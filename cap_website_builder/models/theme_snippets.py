"""The Captivea theme's own snippets, read from the database.

``snippet_library`` is a hard coded copy of a few standard Odoo blocks: a last
resort for a database with no design of its own. This module is the opposite -
it reads the real vocabulary of the site, the ``s_cap_*`` templates the theme
registers in the website builder, straight out of ``ir.ui.view``. A snippet
added to the theme is therefore available to the AI on the next upgrade, with
nothing to copy here.

Two things are taken from a snippet:

* its **markup**, inserted verbatim when a section is added to a page. The AI
  never writes it, so a block dropped by the AI is byte for byte the block a
  designer would drop from the builder panel.
* its **placeholders** - the ``{Context title - e.g. ...}`` strings the theme
  writes into its own templates. Each one says what belongs in that slot, which
  makes it the brief for the text that fills it.
"""

import logging
import re

from lxml import etree, html

_logger = logging.getLogger(__name__)

# The theme that owns the snippets. Its views are keyed `<module>.<template id>`
# and every page snippet is `s_cap_*`, which is what separates them from the
# theme's layout and option templates.
THEME_MODULE = 'cap_web_captivea_theme'
SNIPPET_KEY_LIKE = THEME_MODULE + '.s_cap_%'

# The theme writes its own briefs into its templates as `{...}`. Three
# characters minimum so a stray brace in real copy is not read as a slot.
PLACEHOLDER_RE = re.compile(r'\{[^{}]{3,}\}')

# The one placeholder the theme puts in an attribute rather than in text: the
# hidden subject of its contact form, on every template page.
PAGE_TITLE_PLACEHOLDER = '{Short title of the page}'

# How much of a placeholder reaches a catalogue listing. The full string carries
# a whole example sentence; here only the kind of thing is wanted.
HINT_CHARS = 90
HINTS_PER_SNIPPET = 4


def has_placeholder(text):
    """Whether a piece of text is one of the theme's ``{...}`` briefs."""
    return bool(text) and bool(PLACEHOLDER_RE.search(text))


def count_placeholders(markup):
    """How many ``{...}`` briefs a piece of markup still carries.

    JSON is not a brief: the theme stores builder options as
    ``data-custom-template-data='{"references_tags_active": true}'``, and
    counting that as an unfilled slot would report a bug on every page.
    """
    return sum(
        1 for found in PLACEHOLDER_RE.finditer(markup or '')
        # Serialised markup carries it escaped, so both spellings count as JSON.
        if not found.group(0)[1:].lstrip().startswith(('"', '&quot;')))


def _short(text, limit=HINT_CHARS):
    text = ' '.join((text or '').split())
    return text if len(text) <= limit else text[:limit - 1] + '…'


def placeholder_hints(markup, limit=HINTS_PER_SNIPPET):
    """The ``{...}`` briefs inside a block, shortened, in document order."""
    hints = []
    for found in PLACEHOLDER_RE.finditer(markup or ''):
        hint = _short(found.group(0).strip('{}').strip())
        if hint and hint not in hints:
            hints.append(hint)
        if len(hints) >= limit:
            break
    return hints


def _section_of(arch):
    """The one ``<section>`` a snippet template holds, as markup.

    A snippet template is a ``<template>`` wrapping a single section. Only that
    section is wanted: the wrapper is QWeb, not page content.
    """
    if not arch or not arch.strip():
        return ''
    try:
        tree = html.fromstring(arch)
    except (etree.ParserError, etree.XMLSyntaxError):
        return ''
    if tree is None:
        return ''
    sections = tree.xpath('//section')
    element = sections[0] if sections else tree
    return etree.tostring(element, encoding='unicode', method='xml').strip()


def catalogue(env, website=None):
    """Every theme snippet, as ``[{key, name, markup, hints}]``.

    ``key`` is the bare template id (``s_cap_faq``), which is what the AI is
    asked to answer with: the module prefix is noise to it and one more thing to
    get wrong. Read with ``sudo()`` - which blocks the site uses is not
    confidential, and the caller is already a website designer.

    One entry per key, even though a key can have several views: customising a
    snippet on a website copies it on write, leaving the generic view and the
    website's own under the same key. The website's version is the one the site
    renders, so it is the one offered; without a website, the generic one is.
    """
    domain = [('key', '=like', SNIPPET_KEY_LIKE), '|',
              ('website_id', '=', False),
              ('website_id', '=', website.id if website else False)]
    views = env['ir.ui.view'].sudo().search(domain, order='key')
    if views:
        # The website's own copy wins over the generic view of the same key.
        chosen = {}
        for view in views:
            if view.key not in chosen or view.website_id:
                chosen[view.key] = view
        views = env['ir.ui.view'].sudo().browse(
            [view.id for _key, view in sorted(chosen.items())])
    entries = []
    for view in views:
        try:
            arch = view.with_context(lang=None).get_combined_arch()
        except Exception:  # noqa: BLE001 - a broken snippet is skipped, not fatal
            _logger.warning("Could not read theme snippet %s", view.key,
                            exc_info=True)
            continue
        markup = _section_of(arch)
        if not markup:
            continue
        entries.append({
            'key': view.key.split('.', 1)[-1],
            'name': view.name or view.key,
            'markup': markup,
            'hints': placeholder_hints(markup),
        })
    return entries


def by_key(entries):
    return {entry['key']: entry for entry in entries}


def render_listing(entries):
    """The catalogue as names and briefs only, with no markup.

    This is what the AI is shown when it may *choose* a section to add. It never
    needs the markup for that: the module inserts the block itself, so sending
    tags would only invite the model to write its own version of them.
    """
    lines = []
    for entry in entries:
        line = '- %s: %s' % (entry['key'], entry['name'])
        if entry['hints']:
            line += ' — %s' % '; '.join(entry['hints'])
        lines.append(line)
    return '\n'.join(lines)


def render_palette(entries, budget=None):
    """The catalogue as a snippet palette: every name, then full markup.

    Used when a page is built with no design template, where the AI does write
    the markup and needs real blocks to copy. The name list is always complete -
    it is what stops the model inventing a block - and as many full examples as
    the budget allows follow it.
    """
    if not entries:
        return ''
    listing = render_listing(entries)
    header = (
        "=== THE ONLY BLOCK TYPES YOU MAY USE ===\n"
        "These are this site's own snippets, from the Captivea theme. Build the "
        "page from these and no others. Start from a block's markup and change "
        "only the words inside its text nodes: the s_* classes, the data-snippet "
        "and data-name attributes, the o_cc colour classes, the pt/pb spacing "
        "and the container / row / col-* nesting are what make the block "
        "editable in the website builder and styled by the theme.\n\n"
        "Any text in braces - {like this} - is a brief telling you what belongs "
        "in that slot, never text to keep. Replace every one of them, braces "
        "included, with real copy for this page.\n\n%s\n\n"
        "=== FULL MARKUP, ONE EXAMPLE PER BLOCK TYPE ===\n" % listing)
    if budget is None:
        budget = len(''.join(entry['markup'] for entry in entries))
    room = budget - len(header)
    examples, used = [], 0
    for entry in entries:
        block = '<!-- snippet: %s -->\n%s' % (entry['key'], entry['markup'])
        if used + len(block) > room:
            continue
        examples.append(block)
        used += len(block)
    if not examples:
        return ''
    return header + '\n\n'.join(examples) + '\n\n'
