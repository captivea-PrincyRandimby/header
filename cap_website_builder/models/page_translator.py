"""Translate the terms of a page, without a browser.

The website editor's "translate this page" button is a builder action: it walks
the DOM inside the editor's iframe, chunks the text nodes, and writes the answer
back into the live document for the user to save. None of that exists in a cron
- no browser, no editable, no unsaved document - so the same job is done against
Odoo's own translation storage instead.

A view's ``arch_db`` is translated term by term. ``get_field_translations``
hands back ``{lang, source, value}`` for every term, and a term whose value
still equals its source has never been translated. Those are the ones worth
paying for.
"""
import hashlib
import html
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor



class TranslationServiceError(Exception):
    """Odoo's translation service refused or failed.

    A plain exception on purpose: it is raised inside worker threads, where
    ``_()`` has no environment to read a language from and logs a warning with
    a full stack trace for every call. Callers translate the message.
    """

_logger = logging.getLogger(__name__)

# Roughly the chunk size the editor's own button uses. Small chunks cost more
# calls; large ones make a model likelier to drop or merge an entry.
CHUNK_CHARS = 2000

# Terms that are not prose. Ported from the editor's button so a scheduled run
# and a manual one skip the same things.
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PHONE_RE = re.compile(r'^[+\d][\d\s\-().]{6,}$')
URL_RE = re.compile(
    r'^(https?://)?([\w-]+\.)+[\w-]+(:\d+)?(/[\w\-./?%&=]*)?(#\S*)?$', re.I)
# The editor's button accepts a term with a letter *or* a number. This wants a
# letter: "2024", "99%" and "+34 91 000" are dates, prices and numbers, and
# paying a model to hand them back unchanged is the one waste a scheduled run
# repeats on every page.
LETTER_RE = re.compile(r'[^\W\d_]', re.UNICODE)
ZERO_WIDTH_RE = re.compile('[\u200b-\u200d\ufeff]')

# A term is judged on the words a reader sees, not on its markup. Without this,
# `<small class="text-muted"><span class="h2-fs"><strong>3</strong></span></small>`
# passes the letter test on its class names, is sent on every run, and comes back
# unchanged every time because there is nothing in it to translate.
TAG_RE = re.compile(r'<[^>]*>')

# Entities are unescaped repeatedly, not once. A page carries `&amp;nbsp;` -
# the escaped form of `&nbsp;` - and one pass turns it into the *word* `nbsp`,
# which then reads as a letter and keeps a term of pure punctuation alive. Seen
# on this database: the term `:&amp;nbsp;` was sent and learned as
# untranslatable, which it should never have been asked about.
UNESCAPE_PASSES = 3

# Slugs and identifiers: `erp-netsuite`, `sap-business-one`,
# `microsoft-dynamics-365`. Lower case, no spaces, joined by - _ or . - the shape
# of a URL fragment or a code name, never of a sentence. Deliberately narrow: a
# capital letter or a space and it is treated as prose again.
SLUG_RE = re.compile(r'^[a-z0-9]+(?:[-_.][a-z0-9]+)+$')

# Odoo's own translation service, the one behind the editor's button. It is an
# IAP call rather than a model method, so it is made here the way the
# html_editor controller makes it: same endpoint, same parameters, same
# database id.
DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'
OLG_TIMEOUT = 30

# The editor's button sends three chunks at a time, with this comment against
# it: more than that and the service starts answering "our AI is unreachable".
# Kept identical, and it also cuts the wall time of a page by about two thirds.
OLG_CONCURRENCY = 3


def language_name(code):
    """A language name a translator will understand, from the code.

    Not ``res.lang.name``: on a real database that field holds "Luxembourg" for
    fr_LU and "Singapore" for en_SG - country names, not languages - and
    "French (CA) / Français (CA)" for fr_CA. Asking a model to translate a page
    "into Luxembourg" is how a whole batch comes back unusable.
    """
    try:
        from babel import Locale
        return Locale.parse(code).get_display_name('en')
    except Exception:  # noqa: BLE001 - an odd code is not worth failing over
        return code


def olg_settings(env):
    """Endpoint and database id, read once so the calls need no cursor."""
    parameters = env['ir.config_parameter'].sudo()
    return (parameters.get_param('html_editor.olg_api_endpoint',
                                 DEFAULT_OLG_ENDPOINT),
            parameters.get_param('database.uuid'))


def olg_chat(endpoint, database_id, prompt, conversation):
    """One call to Odoo's translation service, as the controller makes it.

    Takes plain values rather than an env: it runs in a worker thread, where a
    cursor would not be safe, and it needs nothing from the ORM anyway.
    """
    from odoo.addons.iap.tools import iap_tools

    response = iap_tools.iap_jsonrpc(
        endpoint + "/api/olg/1/chat",
        params={
            'prompt': prompt,
            'conversation_history': conversation or [],
            'database_id': database_id,
        },
        timeout=OLG_TIMEOUT)

    status = (response or {}).get('status')
    if status == 'success':
        return response.get('content') or ''
    if status == 'error_prompt_too_long':
        raise TranslationServiceError(
            "the batch was refused as too long")
    if status == 'limit_call_reached':
        raise TranslationServiceError(
            "this database has reached its limit on the service")
    raise TranslationServiceError(
        "the service returned no answer (%s)" % (status or '?'))


SYSTEM_PROMPT = """You are a translation assistant. You translate the text of a \
web page, one block at a time.

- The input is a JSON array of objects: [{"id": "...", "text": "..."}, ...]
- Translate only the "text" field, and keep its meaning.
- Preserve leading and trailing spaces exactly: " Hello " becomes " Hola ".
- Translate each block on its own. Two blocks that read as one sentence in the
  page are still separate strings here, and each must stand on its own.
- A block may contain HTML tags. Copy every tag, attribute and entity exactly as
  it is and translate only the words between them.
- Leave alone anything that should not be translated: brand and product names,
  code, URLs, email addresses, phone numbers.
- Answer with the same JSON array, with "text" replaced by the translation.
  Nothing else: no explanation, no markdown fences, no extra fields.
"""


def is_translatable(term):
    """False for a term that is not prose: a URL, an email, a number, a slug.

    Ported from the editor's own button so a scheduled run and a manual one
    skip the same things, with the deliberate differences noted on
    ``LETTER_RE``, ``TAG_RE`` and ``SLUG_RE``.

    These rules matter more here than in the button. The button runs once, when
    someone clicks it; this runs every hour forever, so a term with nothing to
    translate in it is not a one-off waste but a line on every bill, and it also
    never stops being pending - the service hands it back unchanged, nothing is
    written, and it is due again next run.
    """
    text = ZERO_WIDTH_RE.sub('', term or '').strip()
    if not text:
        return False
    # Judge the visible words, not the markup around them.
    visible = TAG_RE.sub(' ', text)
    for _pass in range(UNESCAPE_PASSES):
        plain = html.unescape(visible)
        if plain == visible:
            break
        visible = plain
    visible = visible.strip()
    if not visible or not LETTER_RE.search(visible):
        return False
    if SLUG_RE.match(visible):
        return False
    return not (EMAIL_RE.match(visible) or PHONE_RE.match(visible)
                or URL_RE.match(visible))


def term_key(term):
    """A stable key for a term, used to remember the ones that never translate.

    Hashed rather than kept whole: some of these terms are several hundred
    characters of markup, and the key is only ever compared for equality. Lives
    here, next to the code that decides what is worth sending, so the model that
    stores the keys and the code that filters on them cannot drift apart.
    """
    return hashlib.sha256((term or '').encode('utf-8')).hexdigest()[:32]


def pending_terms(record, field_name, lang, known_unchanged=None):
    """The terms of ``record.field_name`` still worth paying to translate.

    A term Odoo has no translation for reads back as its own source, so
    ``value == source`` is what "untranslated" looks like. Terms already
    translated are left alone, which is what makes a scheduled run idempotent
    and cheap to repeat.

    ``known_unchanged`` is a set of term hashes the service has already answered
    "this does not translate" for. Those terms look exactly like untranslated
    ones in storage - there is no way to tell "no translation exists" from
    "translated to itself" - so without this they are due again on every run,
    for ever. It is passed in rather than queried here so this stays a function
    of its arguments, and so one query serves a whole page.
    """
    try:
        translations, _context = record.get_field_translations(field_name, [lang])
    except Exception:  # noqa: BLE001 - a broken view must not stop the run
        _logger.warning(
            "Could not read translations of %s#%s", record._name, record.id,
            exc_info=True)
        return []

    known_unchanged = known_unchanged or frozenset()
    terms, seen = [], set()
    for row in translations:
        source = row.get('source') or ''
        if row.get('value') and row['value'] != source:
            continue
        if source in seen or not is_translatable(source):
            continue
        if known_unchanged and term_key(source) in known_unchanged:
            continue
        seen.add(source)
        terms.append(source)
    return terms


def chunk_terms(terms, limit=CHUNK_CHARS):
    """Group terms into batches small enough for one call."""
    batch, size = [], 0
    for term in terms:
        cost = len(term) + 16  # the JSON wrapper around each entry
        if batch and size + cost > limit:
            yield batch
            batch, size = [], 0
        batch.append(term)
        size += cost
    if batch:
        yield batch


def _parse(answer, batch):
    """Read the model's array back.

    Returns ``(translations, unchanged)``: ``{source: translation}`` for the
    terms that came back different, and the list of terms that came back
    **identical**.

    The second list used to be thrown away, and that was the expensive mistake.
    A term returned unchanged has no translation - a brand name, a slug, a
    number in markup - and writing it would be a no-op, but forgetting it means
    sending it again on every single run for ever. The caller records them so
    they are asked about once.
    """
    text = (answer or '').strip()
    if '```' in text:
        parts = text.split('```')
        text = max(parts, key=len)
        if text.lstrip().startswith('json'):
            text = text.lstrip()[4:]
    start, end = text.find('['), text.rfind(']')
    if start == -1 or end == -1 or end < start:
        return {}, []
    try:
        rows = json.loads(text[start:end + 1])
    except ValueError:
        return {}, []
    if not isinstance(rows, list):
        return {}, []

    result, unchanged = {}, []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            index = int(row.get('id'))
        except (TypeError, ValueError):
            continue
        value = row.get('text')
        if not isinstance(value, str) or not value.strip():
            continue
        if not 0 <= index < len(batch):
            continue
        if value == batch[index]:
            unchanged.append(batch[index])
        else:
            result[batch[index]] = value
    return result, unchanged


def translate_terms(env, terms, language):
    """Translate ``terms`` into ``language`` with Odoo's own service.

    Follows the editor button's process rather than inventing one: chunks of
    the same size, three calls in flight at once, and - the part that matters -
    **a failed chunk is skipped, never fatal**. The button's own comment on it
    is "ignore failed request to save successfull ones", and it is right: one
    transient IAP error should not throw away eighteen chunks already paid for.

    Returns ``(translations, skipped, unchanged)``: ``{source: translation}`` for
    what came back usable, how many terms were not translated (which the caller
    reports the way the button does), and the terms the service handed back
    **identical**, which the caller records so they are never sent again.

    ``skipped`` and ``unchanged`` are different failures and must not be
    conflated. A skipped term is work still to do - its chunk errored, and the
    next run should retry it. An unchanged term is work that will never happen -
    there is nothing to translate - and retrying it is the loop this whole
    registry exists to break.
    """
    endpoint, database_id = olg_settings(env)
    batches = list(chunk_terms(terms))
    if not batches:
        return {}, 0, []

    # Built here, in the calling thread. `_()` reads the language from the
    # calling frame's environment, and a worker thread has none: called there it
    # logs "no translation language detected" with a full stack trace on every
    # chunk. This string is sent to an API, not shown to anyone, so it needs no
    # translating either.
    payloads = [
        json.dumps([{'id': index, 'text': term}
                    for index, term in enumerate(batch)], ensure_ascii=False)
        for batch in batches
    ]

    def run(job):
        batch, payload = job
        try:
            answer = olg_chat(endpoint, database_id, payload, [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content':
                    "Translate the following into %s:\n\n%s" % (language, payload)},
            ])
        except Exception as error:  # noqa: BLE001 - one chunk, not the page
            _logger.warning("Translation chunk failed: %s", error)
            return {}, []
        parsed, unchanged = _parse(answer, batch)
        if not parsed and not unchanged:
            # A chunk that answers but yields nothing at all is the failure
            # worth seeing: the answer's shape is the only clue to why. A chunk
            # that answers with everything unchanged is not a failure - it is a
            # batch of brand names, and it is now recorded rather than retried.
            _logger.warning(
                "Translation chunk returned nothing usable for %s. "
                "Answer began: %s", language, (answer or '')[:200])
        return parsed, unchanged

    with ThreadPoolExecutor(OLG_CONCURRENCY) as pool:
        results = list(pool.map(run, zip(batches, payloads)))

    translations, unchanged = {}, []
    for result, untouched in results:
        translations.update(result)
        unchanged.extend(untouched)
    # Terms the service returned unchanged are not counted as skipped: they are
    # answered, the answer is "this does not translate", and the caller stops
    # asking. Counting them here would report permanent work every run.
    settled = set(translations) | set(unchanged)
    skipped = len([term for term in terms if term not in settled])
    return translations, skipped, unchanged
