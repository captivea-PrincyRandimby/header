"""Read-only access to Surfer SEO.

Surfer is asynchronous: you create a job, then poll it. It is metered and
consumes plan quota with no sandbox, so every call here is bounded, nothing is
fetched speculatively, and a job already paid for is reused rather than
recreated.

The one caller is the page builder: a request with Use Surfer SEO ticked gets a
content brief before the copy is written, and the copy scored against it
afterwards.
"""
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

SURFER_BASE = 'https://app.surferseo.com'

DEFAULT_TIMEOUT = 60

# How long a Surfer job gets to finish inside the request that created it. A
# SERP analysis usually lands inside two minutes; past that the builder gives
# up on the brief and writes the page without it rather than tying up a worker.
SURFER_WAIT_SECONDS = 120

# Pushing content back makes Surfer recalculate the score. It lands in a few
# seconds; the wait is a ceiling, not a sleep.
SURFER_SCORE_WAIT_SECONDS = 45
SURFER_SCORE_POLL = 3

# Poll fast while the analysis is likely to land, then back off: a completed
# editor is picked up within three seconds instead of waiting out a fixed slot.
SURFER_POLL_FAST = 3
SURFER_POLL_SLOW = 10
SURFER_FAST_WINDOW = 60

# A lost connection must not cost a credit. Content Editors can be listed and
# matched on their keyword, so a job whose id never reached us - the answer to
# the create call was dropped, the transaction rolled back, the worker was
# killed mid-run - is found again rather than started again. On this account
# that alone accounts for most of the editors on record: "erp odoo" was
# analysed four times and "gold odoo partner switzerland" twice, 28 minutes
# apart, all of them the same analysis paid for more than once.
SURFER_REUSE_HOURS = 168        # a week: past that the SERP has moved on
SURFER_ADOPT_MINUTES = 20       # "the create call probably did land" window
SURFER_RECOVER_DELAY = 5        # let Surfer list what it just created
SURFER_LIST_PAGE_SIZE = 50

# Reads are retried through a blip. Writes never are: a retried create is a
# second Content Editor and a second credit, which is the very thing this is
# here to prevent.
SURFER_RETRY_ATTEMPTS = 3
SURFER_RETRY_BACKOFF = 3
SURFER_RETRY_STATUSES = (429, 500, 502, 503, 504)

# The four blocks a Content Editor exposes. Terms alone say which words to use;
# the rest say how long the page should be, what to put in headings, and what
# the pages that already rank cover.
GUIDELINE_BLOCKS = ('terms', 'structure', 'topics_and_questions', 'competitors')

# Surfer states its structural targets as a ratio of a baseline factor.
STRUCTURE_FACTORS = {
    'word_count': 'words',
    'headings_count': 'headings',
    'paragraph_count': 'paragraphs',
    'img_count': 'images',
    'bold_count': 'bold items',
}


class ResearchError(Exception):
    """Anything that stopped us getting data out of Surfer."""


class SurferUnreachable(ResearchError):
    """The call never came back with an answer.

    Different from a refusal on purpose. A 401 or a 422 says the request did
    not happen; a dropped connection, a timeout or a 502 says nothing at all,
    and the job may well have been created on Surfer's side. That distinction
    is what lets a create call be recovered instead of repeated.
    """


# --------------------------------------------------------------------------
# Surfer
# --------------------------------------------------------------------------
class SurferClient:

    def __init__(self, api_key, workspace_id=None, timeout=DEFAULT_TIMEOUT):
        if not api_key:
            raise ResearchError(_(
                "No Surfer API key configured. Add one in Settings > "
                "AI Page Builder."))
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.timeout = timeout or DEFAULT_TIMEOUT

    # -- transport ------------------------------------------------------
    def _request(self, method, path, extra_headers=None, **kwargs):
        """One call, repeated through a blip when repeating it is safe.

        GET is idempotent, so a dropped connection or a 502 is simply tried
        again: an outage of a few seconds in the middle of a two-minute poll
        should not throw away the analysis being waited for. POST and PUT are
        never repeated - a second create is a second credit - so they raise
        :class:`SurferUnreachable` and let the caller work out whether the
        first one landed.
        """
        attempts = SURFER_RETRY_ATTEMPTS if method == 'GET' else 1
        for attempt in range(1, attempts + 1):
            try:
                return self._request_once(method, path, extra_headers, **kwargs)
            except SurferUnreachable as error:
                if attempt == attempts:
                    raise
                time.sleep(SURFER_RETRY_BACKOFF * attempt)

    def _request_once(self, method, path, extra_headers=None, **kwargs):
        headers = {'API-KEY': self.api_key}
        headers.update(extra_headers or {})
        try:
            response = requests.request(
                method, SURFER_BASE + path, headers=headers,
                timeout=self.timeout, **kwargs)
        except requests.exceptions.Timeout:
            raise SurferUnreachable(
                _("Surfer did not answer within %s seconds.", self.timeout))
        except requests.exceptions.RequestException as error:
            raise SurferUnreachable(_("Could not reach Surfer: %s", error))

        if response.status_code == 401:
            raise ResearchError(_(
                "Surfer refused the API key. It must belong to the account "
                "owner, on a plan that includes API access."))
        if response.status_code == 403:
            raise ResearchError(_(
                "Surfer denied this tool (403). The plan or add-on does not "
                "include it."))
        if response.status_code == 422:
            raise ResearchError(_(
                "Surfer quota exceeded, or the request could not be "
                "processed: %s", response.text[:300]))
        # Rate limits and gateway errors say nothing about whether the work was
        # done, so they are treated as an unanswered call rather than a refusal.
        if response.status_code in SURFER_RETRY_STATUSES:
            raise SurferUnreachable(_(
                "Surfer answered HTTP %(code)s: %(body)s",
                code=response.status_code, body=response.text[:200]))
        if response.status_code >= 400:
            raise ResearchError(_(
                "Surfer returned HTTP %(code)s: %(body)s",
                code=response.status_code, body=response.text[:300]))
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            raise ResearchError(_("Surfer returned a non-JSON response."))

    def workspaces(self):
        payload = self._request('GET', '/api/v2/workspaces')
        return payload.get('data', payload)

    def _resolve_workspace(self):
        if self.workspace_id:
            return self.workspace_id
        workspaces = self.workspaces()
        if not workspaces:
            raise ResearchError(_("This Surfer account has no workspace."))
        self.workspace_id = workspaces[0].get('id')
        return self.workspace_id

    def _wait_briefly(self, path, done_states, label, wait_seconds=None):
        """Give a fresh job a chance to finish inside this request.

        Returns the payload when it settles, or None when it is still running.
        A Surfer job can take minutes - far longer than an HTTP request may
        block - so not finishing is a normal outcome here, not an error.

        Polling starts fast and backs off: most analyses land in the first
        minute, and a fixed slow interval would sit on a finished job.

        An unanswered poll is not the end of the wait. The job is running on
        Surfer's side regardless of whether this side can reach it, so a
        network outage keeps the loop going to its deadline instead of
        abandoning an analysis that has already been paid for.
        """
        deadline = time.time() + (wait_seconds or SURFER_WAIT_SECONDS)
        started = time.time()
        while True:
            try:
                payload = self._request('GET', path)
            except SurferUnreachable as error:
                if time.time() >= deadline:
                    raise
                time.sleep(SURFER_POLL_SLOW)
                continue
            state = payload.get('state') or payload.get('status')
            if state in done_states:
                return payload
            if state in ('failed', 'error'):
                raise ResearchError(_("Surfer could not finish the %s.", label))
            if time.time() >= deadline:
                return None
            time.sleep(SURFER_POLL_FAST
                       if time.time() - started < SURFER_FAST_WINDOW
                       else SURFER_POLL_SLOW)

    # -- operations -----------------------------------------------------
    def _editor_path(self, editor_id, workspace_id=None):
        workspace = workspace_id or self._resolve_workspace()
        return '/api/v2/workspaces/%s/content_editors/%s' % (workspace, editor_id)

    def start_content_guidelines(self, main_keyword, secondary_keywords=None,
                                 location='United States', device='mobile',
                                 custom_instructions=None):
        """Create the Content Editor. Returns its id; the analysis runs on."""
        if not main_keyword:
            raise ResearchError(_("Content guidelines need a main keyword."))
        workspace = self._resolve_workspace()
        payload = {
            'main_keyword': main_keyword,
            # Surfer caps the total at 20 keywords including the main one.
            'secondary_keywords': (secondary_keywords or [])[:19],
            'location': location or 'United States',
            'device': device or 'mobile',
            'use_brand_knowledge': False,
        }
        if custom_instructions:
            payload['custom_instructions'] = custom_instructions
        created = self._request(
            'POST', '/api/v2/workspaces/%s/content_editors' % workspace,
            json=payload)
        editor_id = created.get('id')
        if not editor_id:
            raise ResearchError(_("Surfer did not return a Content Editor id."))
        return {'editor_id': editor_id, 'workspace_id': workspace}

    def list_content_editors(self, workspace_id=None,
                             page_size=SURFER_LIST_PAGE_SIZE):
        """The workspace's Content Editors, newest first.

        A free read: listing is not an analysis, so nothing is billed for
        asking what has already been run.
        """
        workspace = workspace_id or self._resolve_workspace()
        payload = self._request(
            'GET', '/api/v2/workspaces/%s/content_editors' % workspace,
            params={'page_size': page_size})
        rows = payload.get('data', payload) if isinstance(payload, dict) else payload
        return rows if isinstance(rows, list) else []

    def find_content_editor(self, main_keyword, secondary_keywords=None,
                            max_age_hours=SURFER_REUSE_HOURS, workspace_id=None):
        """The newest Content Editor that already answers this keyword, or None.

        Matched on the main keyword, which is what anchors Surfer's SERP
        analysis. When several match, one whose secondary keywords are the same
        set wins - the brief is then exactly the one that would have been
        ordered - and otherwise the most recent does.

        Failing to list is not an error here: the worst it costs is the credit
        this was trying to save, so it returns None and lets the caller create.
        """
        wanted = (main_keyword or '').strip().lower()
        if not wanted:
            return None
        try:
            rows = self.list_content_editors(workspace_id=workspace_id)
        except ResearchError:
            # Worst case is the credit this was trying to save; the chatter
            # still reports that an editor was created.
            return None

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        secondary = {word.strip().lower()
                     for word in (secondary_keywords or []) if word}
        exact, loose = [], []
        for row in rows:
            if (row.get('main_keyword') or '').strip().lower() != wanted:
                continue
            if row.get('error') or (row.get('state') or '') in ('failed', 'error'):
                continue
            stamp = _parse_timestamp(row.get('inserted_at'))
            if stamp and stamp < cutoff:
                continue
            found = {word.strip().lower()
                     for word in (row.get('secondary_keywords') or []) if word}
            row = dict(row, _stamp=stamp or datetime.min)
            (exact if secondary and found == secondary else loose).append(row)

        candidates = sorted(exact or loose, key=lambda row: row['_stamp'],
                            reverse=True)
        return candidates[0] if candidates else None

    def ensure_content_editor(self, main_keyword, secondary_keywords=None,
                              location='United States', device='mobile',
                              custom_instructions=None, reuse=True):
        """A Content Editor for this keyword, created only when there is none.

        This is what makes a dropped connection free. Three things can happen:

        - ``reused``   - an analysis for this keyword already exists and is
                         recent enough to still describe the same SERP.
        - ``created``  - there was none, so one was ordered and a credit spent.
        - ``recovered``- the create call never came back. Surfer may well have
                         created the editor before the connection died, so the
                         workspace is checked for one that appeared in the last
                         few minutes and that one is adopted. Without this the
                         credit is spent and thrown away, which is exactly the
                         duplicate pairs sitting in this account's history.

        Returns ``{'editor_id', 'workspace_id', 'origin'}``.
        """
        if not main_keyword:
            raise ResearchError(_("Content guidelines need a main keyword."))

        if reuse:
            row = self.find_content_editor(main_keyword, secondary_keywords)
            if row and row.get('id'):
                return {
                    'editor_id': row['id'],
                    'workspace_id': row.get('workspace_id') or self.workspace_id,
                    'origin': 'reused',
                    'created_at': row.get('inserted_at'),
                }

        try:
            started = self.start_content_guidelines(
                main_keyword, secondary_keywords=secondary_keywords,
                location=location, device=device,
                custom_instructions=custom_instructions)
        except SurferUnreachable as error:
            _logger.warning(
                "The Surfer create call lost its answer (%s); looking for the "
                "editor it may have created.", error)
            time.sleep(SURFER_RECOVER_DELAY)
            row = self.find_content_editor(
                main_keyword, secondary_keywords,
                max_age_hours=SURFER_ADOPT_MINUTES / 60.0)
            if row and row.get('id'):
                return {
                    'editor_id': row['id'],
                    'workspace_id': row.get('workspace_id') or self.workspace_id,
                    'origin': 'recovered',
                    'created_at': row.get('inserted_at'),
                }
            raise
        started['origin'] = 'created'
        return started

    def _settle_editor(self, base, wait, wait_seconds):
        """The editor payload once analysed, or None while it still runs."""
        if wait:
            return self._wait_briefly(
                base, ('completed',), _("content guidelines"),
                wait_seconds=wait_seconds)
        payload = self._request('GET', base)
        state = payload.get('state') or payload.get('status')
        if state in ('failed', 'error'):
            raise ResearchError(
                _("Surfer could not finish the content guidelines."))
        return payload if state == 'completed' else None

    def fetch_content_brief(self, editor_id, workspace_id=None, wait=True,
                            wait_seconds=None):
        """The whole brief, or None while Surfer is still analysing.

        The four guideline blocks are fetched at once rather than one after
        another: they are independent requests and Surfer answers them in
        parallel, so the brief costs one round trip instead of four.
        """
        base = self._editor_path(editor_id, workspace_id)
        if self._settle_editor(base, wait, wait_seconds) is None:
            return None

        def one(block):
            return block, self._request(
                'GET', '%s/seo_guidelines/%s' % (base, block))

        with ThreadPoolExecutor(len(GUIDELINE_BLOCKS)) as pool:
            blocks = dict(pool.map(one, GUIDELINE_BLOCKS))
        return _build_brief(editor_id, blocks)

    def fetch_content_guidelines(self, editor_id, workspace_id=None, wait=True,
                                 wait_seconds=None):
        """The term rows alone, for the research chat's table."""
        brief = self.fetch_content_brief(
            editor_id, workspace_id=workspace_id, wait=wait,
            wait_seconds=wait_seconds)
        if brief is None:
            return None
        return [{
            'term': term['term'],
            'suggested_uses': ('%s-%s' % (term['min'], term['max'])
                               if term['max'] else term['min']),
            'in_heading': 'yes' if term['heading'] else '',
        } for term in brief['terms']]

    def score_content(self, markdown, editor_id, workspace_id=None,
                      wait_seconds=None):
        """Push the article into the Content Editor and read its score back.

        Surfer recalculates asynchronously, so the result is polled rather than
        slept for: the score is trusted once ``updated_at`` has moved and the
        same value has been read twice, which is what tells a finished
        recalculation apart from a stale reading of the previous one.

        Returns ``{'total', 'seo', 'ai_search'}``; the values are None when the
        recalculation did not settle in time.
        """
        if not markdown or not markdown.strip():
            raise ResearchError(_("There is no content to score."))
        base = self._editor_path(editor_id, workspace_id)
        before = self._request('GET', base).get('updated_at')

        self._request(
            'PUT', base + '/content',
            extra_headers={'Content-Type': 'text/markdown'},
            data=markdown.encode('utf-8'))

        deadline = time.time() + (wait_seconds or SURFER_SCORE_WAIT_SECONDS)
        previous = object()
        while time.time() < deadline:
            time.sleep(SURFER_SCORE_POLL)
            payload = self._request('GET', base)
            score = (payload.get('content_score') or {}).get('total')
            if (payload.get('updated_at') != before
                    and score is not None and score == previous):
                return _score_of(payload)
            previous = score
        return _score_of(self._request('GET', base))


def _parse_timestamp(value):
    """Surfer's ``2026-08-13T14:55:11Z`` as a naive UTC datetime, or None.

    Naive on purpose: it is only ever compared against ``utcnow()``, and an
    unparseable stamp must not decide anything, so it returns None and the
    caller treats the age as unknown rather than as old.
    """
    text = (value or '').strip()
    if not text:
        return None
    try:
        stamp = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None
    if stamp.tzinfo:
        stamp = stamp.astimezone(timezone.utc).replace(tzinfo=None)
    return stamp


def _rows(block):
    """Every guideline block wraps its list in ``data``."""
    return block.get('data') or [] if isinstance(block, dict) else []


def _parse_terms(block):
    """Terms Surfer scored, headings first then by how often they are wanted."""
    terms = []
    for entry in _rows(block):
        target = entry.get('target_range') or {}
        if not (entry.get('included') and entry.get('item')):
            continue
        if target.get('min') is None:
            continue
        terms.append({
            'term': entry['item'],
            'min': target['min'],
            'max': target.get('max'),
            'heading': bool(entry.get('heading')),
        })
    terms.sort(key=lambda term: (-term['heading'], -term['min']))
    return terms


def _parse_structure(block):
    """Turn Surfer's ratios into real numbers.

    Every structural target is expressed as a multiple of a baseline factor,
    so a ratio on its own means nothing: min/max/avg have to be multiplied by
    the baseline value to become a word or heading count.
    """
    if not isinstance(block, dict):
        return {}
    baseline = block.get('guidelines_baseline') or 'word_count'
    base = block.get(baseline)
    if not base:
        return {}
    # The baseline is an exact target; allow +/-10% so it is not missed by one.
    structure = {baseline: {
        'min': round(base * 0.9), 'max': round(base * 1.1), 'target': round(base),
    }}
    for guideline in block.get('structural_guidelines') or []:
        target = guideline.get('target') or {}
        factor = guideline.get('factor')
        if factor not in STRUCTURE_FACTORS or target.get('avg') is None:
            continue
        structure[factor] = {
            'min': round(target['min'] * base),
            'max': round(target['max'] * base),
            'target': round(target.get('value_override') or target['avg'] * base),
        }
    return structure


def _parse_topics(block):
    """The questions readers ask, and the headings competitors use."""
    questions, competitor_headings = [], []
    for entry in _rows(block):
        if not entry.get('item'):
            continue
        if entry.get('type') == 'people_also_ask' and entry.get('included'):
            questions.append(entry['item'])
        elif entry.get('type') == 'competitors':
            competitor_headings.append(entry['item'])
    return questions, competitor_headings


def _build_brief(editor_id, blocks):
    """One dict holding everything Surfer says about this keyword."""
    questions, competitor_headings = _parse_topics(
        blocks.get('topics_and_questions'))
    competitors = [{
        'url': row.get('url'),
        'title': row.get('title'),
        'score': row.get('score'),
        'position': row.get('position'),
        'used': bool(row.get('included')),
    } for row in _rows(blocks.get('competitors'))]

    used = [row for row in competitors if row['used']] or competitors
    scores = [row['score'] for row in used
              if isinstance(row['score'], (int, float))]
    return {
        'editor_id': editor_id,
        'terms': _parse_terms(blocks.get('terms')),
        'structure': _parse_structure(blocks.get('structure')),
        'questions': questions,
        'competitor_headings': competitor_headings,
        'competitors': competitors,
        'avg_score': round(sum(scores) / len(scores), 1) if scores else None,
        'best_score': max(scores) if scores else None,
    }


def _score_of(payload):
    score = payload.get('content_score') or {}
    return {
        'total': score.get('total'),
        'seo': score.get('seo'),
        'ai_search': score.get('ai_search'),
    }


# --------------------------------------------------------------------------
# Local checks
# --------------------------------------------------------------------------
# Free and instant: they say *why* a score is low, which a number cannot. A
# rewrite told "these six terms are under their minimum and the page is 300
# words short" fixes the gap; one told "score 61, do better" guesses.
HEADING_RE = re.compile(r'^#{1,6}\s*(.+)$', re.M)
HEADING_COUNT_RE = re.compile(r'^#{1,6}\s', re.M)
IMAGE_RE = re.compile(r'!\[[^\]]*\]\(')
BOLD_RE = re.compile(r'\*\*[^*]+\*\*')


def _plain_text(markdown):
    text = (markdown or '').lower().replace('\u2019', "'")
    text = re.sub(r'```.*?```', ' ', text, flags=re.S)
    text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r"[^\w'\s]", ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def term_report(markdown, terms):
    """Every scored term, how often it appears, and whether that is on target."""
    text = _plain_text(markdown)
    # An apostrophe is punctuation in most terms and part of the word in a few,
    # so each term is counted against the text that matches how it is written.
    no_apostrophe = text.replace("'", ' ')
    headings = ' '.join(HEADING_RE.findall(markdown or '')).lower()

    report = []
    for term in terms:
        word = term['term'].lower()
        source = text if "'" in term['term'] else no_apostrophe
        count = len(re.findall(
            r'(?<!\w)' + re.escape(word) + r'(?!\w)', source))
        maximum = term.get('max')
        if count < term['min']:
            state = 'low'
        elif maximum and count > maximum:
            state = 'high'
        else:
            state = 'ok'
        report.append(dict(
            term, count=count, state=state,
            in_heading=not term.get('heading') or word in headings))
    return report


def structure_report(markdown, structure):
    """What the article actually is, against what Surfer asked for."""
    plain = _plain_text(markdown)
    actual = {
        'word_count': len(plain.split()),
        'headings_count': len(HEADING_COUNT_RE.findall(markdown or '')),
        'paragraph_count': len([
            block for block in re.split(r'\n\s*\n', markdown or '')
            if block.strip() and not block.strip().startswith('#')]),
        'img_count': len(IMAGE_RE.findall(markdown or '')),
        'bold_count': len(BOLD_RE.findall(markdown or '')),
    }
    report = []
    for factor, target in (structure or {}).items():
        value = actual.get(factor)
        if value is None:
            continue
        if value < target['min']:
            state = 'low'
        elif value > target['max']:
            state = 'high'
        else:
            state = 'ok'
        report.append({
            'factor': factor,
            'label': STRUCTURE_FACTORS.get(factor, factor),
            'value': value,
            'state': state,
            **target,
        })
    return report


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
# Surfer is configured from Settings > AI Page Builder and stored as system
# parameters, read in sudo so any user allowed to build a page can have it
# analysed without being able to read the key.
PARAM_SURFER_KEY = 'cap_website_builder.surfer_api_key'
PARAM_SURFER_WORKSPACE = 'cap_website_builder.surfer_workspace_id'


def research_config(env):
    params = env['ir.config_parameter'].sudo()
    return {
        'surfer_api_key': params.get_param(PARAM_SURFER_KEY) or '',
        'surfer_workspace_id': params.get_param(PARAM_SURFER_WORKSPACE) or '',
    }


def available_sources(env):
    # Still a dict of one, and read as `.get('surfer')` by the page builder: a
    # bare boolean would have to be unpicked at every call site the day a
    # second analysis service is added.
    config = research_config(env)
    return {'surfer': bool(config['surfer_api_key'])}


def get_surfer(env):
    config = research_config(env)
    return SurferClient(config['surfer_api_key'], config['surfer_workspace_id'])
