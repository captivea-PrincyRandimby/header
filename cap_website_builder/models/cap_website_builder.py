import json
import logging
import random
import re

from lxml import etree
from markupsafe import Markup

from odoo import api, fields, models, modules
from odoo.exceptions import AccessError, UserError
from odoo.tools.translate import _

from .ai_provider import AIProviderError, get_provider
from .research_client import ResearchError
from . import page_writer
from . import research_client
from . import snippet_library
from . import theme_snippets
from . import theme_style

_logger = logging.getLogger(__name__)

DEFAULT_MAX_CONTEXT_CHARS = 60000

# Search engines cut the snippet around here, so there is no point writing more.
META_DESCRIPTION_CHARS = 160

# Sub keywords taken from the web search around the main keyword.
SUB_KEYWORD_COUNT = 3

# The design templates a new page may be built to. Matched on the view key
# rather than a list of ids: a theme ships its templates as `website.page`
# records keyed `<theme module>.page_*`, so a template added to the theme
# appears in the field on the next upgrade with nothing to change here. The key
# survives the copy-on-write a website makes when it customises a theme page,
# which an id or a URL does not.
#
# Two prefixes, because two themes carry these pages: `cap_web_captivea_theme`
# is the current one, `theme_captivea` the one it replaced. Matching both means
# a database still on the old theme keeps its templates instead of silently
# offering none.
TEMPLATE_KEY_PREFIXES = (
    theme_snippets.THEME_MODULE + '.page_',
    'cap_web_captivea_theme.page_',
)
TEMPLATE_DOMAIN = ['|'] * (len(TEMPLATE_KEY_PREFIXES) - 1) + [
    ('key', '=like', prefix + '%') for prefix in TEMPLATE_KEY_PREFIXES]

# How much of Surfer's brief reaches the writer. Its lists run long; past these
# the guidance stops being useful and becomes words to shoehorn in.
SURFER_PRIORITY_TERMS = 25   # given with their exact ranges
SURFER_HEADING_TERMS = 12    # asked for in an H2/H3
SURFER_QUESTIONS = 12
SURFER_COMPETITOR_HEADINGS = 15

# How many times the copy may be written, scored and rewritten to reach the
# target. Three is the floor the user asked for and the ceiling a person will
# wait through: each round is an AI call plus a Surfer recalculation.
SURFER_SCORE_ROUNDS = 3

# How much of a page's text goes into one rewrite call. Only the words are sent,
# never the markup, so a 90 KB page is a few thousand characters of text.
REWRITE_BATCH_CHARS = 8000

KEYWORD_PROMPT = """You find the keywords a web page should target.

You are given one main keyword. Search the web for what people actually search
around it, then answer with the %(count)s strongest sub keywords.

A good sub keyword:
- is a phrase people really type, not a paraphrase you invented,
- is more specific than the main keyword and could carry its own section,
- has real search demand, and is not a near duplicate of another one you chose.

From the same search, also report the content ideas: the things people actually
ask and look for around this keyword, in their words. These become the page's
H2 headings, so each one has to be worth a section of its own.

A good content idea:
- comes from what the search results and the questions around them show people
  want, not from what you assume they want,
- is phrased close to how it was searched, so it reads as a heading someone was
  looking for,
- can be answered on this page rather than needing one of its own.

Answer with JSON only, no explanation and no markdown fences:
{"keywords": ["...", "...", "..."], "ideas": ["...", "...", "..."]}
""" % {'count': SUB_KEYWORD_COUNT}

ARTICLE_PROMPT = """You write the copy of a web page, before anyone thinks \
about layout.

Write it as plain text with markdown headings:
- One "# " line: the page's H1.
- "## " lines for sections, "### " for sub sections where a section needs them.
- Ordinary paragraphs under them. "- " for lists.
- No HTML, no markdown tables, no code fences, no images.

Rules:
- The main keyword belongs in the H1 and in the opening paragraph. Give each
  sub keyword a section of its own.
- Write real, specific, useful copy about the subject. Never lorem ipsum, never
  "insert X here", never a sentence that would fit any company.
- Every section says something a reader did not already know from its heading.
- End with a short section that tells the reader what to do next.
- Write for a person. Never repeat a keyword for its own sake.
"""

REWRITE_PROMPT = """You rewrite the wording of a page that already exists.

You are given the new copy for the page, and a numbered list of every piece of
text currently on it. Answer with JSON only: the numbers you are changing, and
what each should say.

    {"3": "new wording", "7": "new wording"}

Rules:
- **Leave out any number you are not changing.** Unchanged is the right answer
  whenever the new copy says nothing about that piece of text. Most pages have
  navigation labels, button labels, form labels, captions and legal lines that
  the new copy does not touch: leave them alone.
- Never invent a fact to fill a slot. If the new copy has nothing to say there,
  omit the number.
- Keep each replacement close to the length of what it replaces. These are slots
  in a finished design: a heading has room for a heading, not a paragraph.
- Match what the slot is. A heading stays a heading, a button label stays two or
  three words, a list item stays one item.
- Plain text only. No HTML, no markdown, no quotes around the whole string.
- Same language as the text you are replacing.

=== THE NEW COPY FOR THE PAGE ===
%(copy)s

=== THE TEXT CURRENTLY ON THE PAGE ===
%(slots)s
"""

FILL_PROMPT = """You write the text of a page that is already designed.

The design is fixed and is none of your business. You are not writing markup and
you will not see any: you get the finished copy of the page, and a numbered list
of the text slots in the design. Each slot shows the text that is in it today -
usually a placeholder in braces saying what belongs there.

Answer with JSON only, no explanation and no markdown fences:

    {"1": "text for slot 1", "2": "text for slot 2"}

Rules:
- Answer every number you are given. A number left out keeps what is there, and
  a placeholder left on a published page is a bug.
- The placeholder is the brief for that slot. "{Context title - e.g. An American
  Odoo partner}" asks for a title of that kind about *this* page's subject. The
  words after "e.g." are an example of the kind of thing, never text to reuse.
- Take the facts from the copy above. Where the copy says nothing about a slot,
  write something that is true of this page from its title, keywords and
  description - never a figure, a client name, a date, an award or a claim you
  invented.
- Keep each answer the length its slot asks for: a heading stays a heading, a
  button label stays two or three words, a paragraph stays a paragraph, a list
  item stays one item.
- Plain text only. No HTML, no markdown, no braces, no quotes around the whole
  string. Same language as the page.

=== THE COPY FOR THIS PAGE ===
%(copy)s

=== THE SLOTS TO FILL ===
%(slots)s
"""

EXTRA_SNIPPETS_PROMPT = """You decide which extra sections a page needs, from a \
fixed catalogue.

A page is being built to a design template. Its sections are listed below, in
order, and they are already decided: you cannot remove one, reorder them or
design a new one. The user's instructions asked for something the template does
not cover, so you may add whole blocks from the theme's catalogue - nothing else.

Answer with JSON only, no explanation and no markdown fences:

    {"add": [{"snippet": "s_cap_faq", "after": 4, "why": "the instructions ask for an FAQ"}]}

Rules:
- "snippet" is a key from the catalogue, spelled exactly as it appears there.
- "after" is the number of the template section the block goes after, or 0 to put
  it at the very top.
- Add a block only if the instructions genuinely ask for what it does. The
  template is the design; adding to it is the exception.
- Never add a block whose job a section of the template already does.
- Answer {"add": []} when nothing should be added. That is the normal answer.

=== THE SECTIONS OF THE TEMPLATE, IN ORDER ===
%(sections)s

=== THE INSTRUCTIONS FROM THE USER ===
%(instructions)s

=== THE CATALOGUE YOU MAY ADD FROM ===
%(catalogue)s
"""

NO_IMAGES_RULE = """=== THIS PAGE HAS NO IMAGES ===
Build it from text alone. Do not write an <img>, a <picture>, a <figure>, a
<video> or a background-image anywhere.

Choose blocks that are made of text. Where the only block that fits is built
around a picture, use it without the image and let the text take the full
width - a column left empty where a picture would have gone is the one thing to
avoid. Never leave a placeholder, and never describe the image you would have
used.

"""

LAYOUT_INTRO = """Here is the finished copy of the page, as plain text with \
markdown headings.

Turn it into the body of an Odoo website page: real snippet sections a website
editor can then edit block by block. Keep the copy - every heading and every
paragraph has to survive into the page - and add nothing to it: your job is the
markup, not the words.

Every top level element is a <section> carrying an s_* snippet class from the
list below, with its data-snippet and data-name attributes. Never put a bare
<h1>, <h2>, <p>, <ul> or <div> at the top level: markup without a snippet class
is unstyled by the theme and cannot be edited as a block, which makes the whole
page useless however good the words are.

=== PAGE COPY ===
%s

"""

# Drawn at random when nobody said how the page should look - no design
# template, no design instruction from the user. The alternative is not "no
# shape" but "the same shape every time": the same copy, the same palette and
# the same prompt produce the same page, so every free-hand page on a site ends
# up a stack of full-width prose blocks in the same order.
#
# The draw happens in Python rather than by telling the model to "be creative".
# A model asked to vary its own output varies the parts that are cheap to vary
# and keeps its habits; handed one concrete shape out of several hundred, it
# builds that shape. It also means the choice is reportable - the chatter says
# which shape was drawn, so a page that came out well can be asked for again.
LAYOUT_OPENINGS = (
    "Open with a hero: the H1 and one line of lead text, and nothing else "
    "above the fold.",
    "Open with a hero carrying the H1, one line of lead text, and the page's "
    "call to action as a button - repeated again at the bottom.",
    "Open with the H1 alone on a coloured band, and put the first real section "
    "immediately under it with no lead paragraph between them.",
)

LAYOUT_RHYTHMS = (
    "Alternate the shapes: a wide prose section, then a multi-column block, "
    "then prose again.",
    "Lead with a block of three short points, then prose, and repeat that pair "
    "down the page.",
    "Keep every section full width and let the colour bands, not the shapes, "
    "separate them.",
    "Work in pairs: a heading-and-intro block, then a columned block that "
    "carries its detail.",
)

LAYOUT_EMPHASIS = (
    "Pull the single strongest fact on the page out into a standalone "
    "highlight band of its own.",
    "Give the middle section a coloured background so the page has a centre.",
    "Set the longest list in two columns rather than one.",
)

LAYOUT_CLOSINGS = (
    "Close on a call-to-action block with one button.",
    "Close with a short stack of question-style headings and their answers, "
    "then the call to action.",
    "Close in two columns: what to do next beside a short summary of the page.",
)

LAYOUT_COLOURS = (
    "Alternate o_cc1 and o_cc2 on consecutive sections.",
    "Keep o_cc1 throughout and use only the spacing classes to separate "
    "sections.",
    "One o_cc3 or o_cc4 band in the middle of the page, o_cc1 everywhere else.",
)

LAYOUT_SPACING = (
    "Default to pt48 pb48, tightening to pt24 pb24 between two sections that "
    "belong together.",
    "Space it evenly and generously: pt64 pb64 on every section.",
)

LAYOUT_VARIATION_INTRO = """=== THE SHAPE TO BUILD, THIS TIME ===
Nobody specified a design for this page, so one has been drawn for you. Build to
it rather than to your usual arrangement - the point is that two pages written
from different copy do not come out as the same stack of blocks.

This is a shape, not a licence: the block list above is still exhaustive, the
markup rules still bind, and a section still only exists if the copy has
something to put in it. Where the shape asks for a block this palette does not
have, use the nearest one it does.
"""


DESCRIPTION_PROMPT = """You write the meta description of a web page.

Given the page's title and markup, reply with the description only: one or two
sentences, at most %s characters, plain text.

- Say what the page offers, in the words someone would search for.
- The main keyword has to appear in it, written out in full as the phrase it
  is. This is one of the placements an SEO tool scores, and it is the line
  someone reads before deciding to click - so work it into a sentence that
  reads, rather than bolting it on.
- No quotes around it, no markdown, no HTML, no label such as "Meta
  description:", no trailing ellipsis.
- Write it for a person deciding whether to click, not for a keyword counter.
""" % META_DESCRIPTION_CHARS

KEYWORD_FIX_PROMPT = """You are given the copy of a web page and the keywords it was written to
target. Each keyword below is missing from a place it is meant to be.

Return the whole copy again, with those gaps closed.

The places, and what each one is in the copy:
- H1: the single "# " line.
- H2: any "## " or "### " heading.
- body copy: the paragraphs and lists under the headings.

Rules:
- Keep everything that is already there: same sections, same order, same facts.
  This is a revision, not a rewrite. Change a heading only where the list below
  asks for a heading.
- Close each gap where it genuinely belongs - the H2 of the section that is
  already about that keyword, a sentence inside that section. If no section
  covers a keyword at all, add one short section that does.
- Write each keyword **exactly** as it is listed: same words, same order, single
  spaces, singular if it is singular, all on one line, nothing inserted between
  the words. It is checked literally, so "Odoo ERP, consulting" and "odoo
  implementation partners" both count as absent.
- Bending a sentence around the phrase is worse than not having it: where the
  exact wording will not sit in a sentence, put it in the heading, where a noun
  phrase reads normally.
- Once per place is enough. Never repeat a keyword to make it count, and never
  put more than one keyword in the H1.
- Same format as the copy you are given: plain text with markdown headings. No
  HTML, no code fences, no note about what you changed.

=== WHAT IS MISSING, AND FROM WHERE ===
%(missing)s

=== THE COPY TO REVISE ===
%(copy)s
"""

FALLBACK_SYSTEM_PROMPT = """You write the body content of Odoo 19 website pages.
Answer with HTML only, no explanation, no markdown fences.
Never output <html>, <head>, <body> or <script> tags: only the sections that go
inside the page. Use Odoo/Bootstrap 5 markup: top level <section> elements with
classes such as "s_text_block pt32 pb32", then container / row / col-lg-* grids.
Write real, specific copy, never lorem ipsum."""

# Closes a prompt that a design template has added its own instructions to.
# Everything the template author wrote is theirs to decide; this is not, because
# it is what `page_writer.extract_html` reads. Kept short so it cannot be
# mistaken for style guidance and argued with, and placed last so it has the
# final word over whatever the template asked for.
OUTPUT_CONTRACT = """Whatever the instructions above ask for, the answer itself is HTML and nothing
else: no explanation, no markdown fences, and no <html>, <head>, <body> or
<script> tag - only the sections that go inside the page."""

# Closes a copy prompt that configured instructions were added to. Same job as
# OUTPUT_CONTRACT one step later: whatever anyone asked for, this is the shape
# the next step can work with. The copy is turned into markup afterwards, so
# copy that arrives as HTML costs the layout step its material.
COPY_CONTRACT = """However the instructions above ask you to write, the answer itself is the page
copy as plain text with markdown headings - one "# " line, "## " sections,
"### " sub sections, paragraphs and "- " lists. No HTML, no tables, no code
fences, no commentary about what you wrote."""

# Headers put in front of a design template's instructions when they are added
# to a prompt. Without one, two prompt bodies run together and the model has no
# way to tell the general rules from the ones about this page.
TEMPLATE_CONTENT_HEADER = """=== WHAT A PAGE OF THIS KIND HAS TO SAY ===
Everything above still applies. These instructions are about this page's
template in particular, and where they are more specific, they win."""

TEMPLATE_DESIGN_HEADER = """=== HOW TO BUILD A PAGE TO THIS DESIGN TEMPLATE ===
Everything above still applies. These instructions are about this page's
template in particular, and where they are more specific, they win."""


# How many times the copy may be sent back for a missing keyword. One round
# fixes the ordinary case; a second covers a model that fixed some and dropped
# others. Past that the copy is kept and the gap is reported, because a third
# rewrite of the same page costs more than the keyword is worth.
KEYWORD_FIX_ROUNDS = 2

# How many content ideas to keep from the keyword search. Enough to head the
# sections of a real page, few enough that the writer still chooses between
# them rather than working through a list.
CONTENT_IDEA_COUNT = 8

# The placements a keyword is worth having, and deliberately the same five that
# Odoo's own Optimize SEO dialog marks: H1, H2, T, D, C. That dialog is where
# anyone will check this page afterwards, so a keyword this module calls placed
# and Odoo marks missing would just be two tools disagreeing. The matching rule
# below is Odoo's too, for the same reason.
#
# Taken from `website/static/src/components/dialog/seo.js`, class `Keyword`:
# usedInH1 reads `#wrap h1`, usedInH2 `#wrap h2`, usedInTitle the title tag,
# usedInDescription the meta description, usedInContent `body.textContent`.
SLOT_TITLE = 'T'
SLOT_DESCRIPTION = 'D'
SLOT_H1 = 'H1'
SLOT_H2 = 'H2'
SLOT_CONTENT = 'C'
SEO_SLOTS = (SLOT_TITLE, SLOT_DESCRIPTION, SLOT_H1, SLOT_H2, SLOT_CONTENT)

SLOT_NAMES = {
    SLOT_TITLE: "title tag",
    SLOT_DESCRIPTION: "meta description",
    SLOT_H1: "H1",
    SLOT_H2: "an H2",
    SLOT_CONTENT: "the body copy",
}

# What each keyword is aimed at. The main keyword carries the page, so it wants
# every slot; a sub keyword earns its section, so it wants the heading of that
# section and the words under it. Anything beyond that is a bonus, never a
# failure - a title tag with four keywords crammed into it ranks for none.
MAIN_KEYWORD_SLOTS = (SLOT_TITLE, SLOT_DESCRIPTION, SLOT_H1, SLOT_CONTENT)
SUB_KEYWORD_SLOTS = (SLOT_H2, SLOT_CONTENT)

HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')

# Character class Odoo uses as a word boundary, copied from
# `WORD_SEPARATORS_REGEX` in `website/static/src/components/dialog/seo.js`. It
# exists there because JavaScript's `\b` is not unicode aware and would break on
# accented words; the class is reproduced rather than replaced by `\b` here so
# that this module and Odoo's SEO dialog agree on every keyword, accents
# included.
SEO_WORD_SEPARATORS = (
    r"[ -⁯⸀-⹿'!\"#$%&()*+,\-./:;<=>?¿¡@\[\]^_`"
    r"{|}~\s]+"
)
SEO_BOUNDARY = '(%s|^|$)' % SEO_WORD_SEPARATORS


def split_copy_slots(copy):
    """The markdown copy split into ``{H1, H2, C}``, the way a page would be.

    ``H1`` is the ``#`` line and ``H2`` the ``##`` lines, matching Odoo's
    dialog, which reads ``#wrap h1`` and ``#wrap h2`` and marks no other
    heading level. A ``###`` is therefore body text here, exactly as it is
    there.

    ``C`` is the **whole** copy, headings included, because Odoo's ``usedInC``
    reads ``body.textContent`` - which contains the headings too. So a keyword
    in the H1 also counts as being in the content, in both tools.
    """
    headings = {SLOT_H1: [], SLOT_H2: []}
    for line in (copy or '').splitlines():
        heading = HEADING_RE.match(line.strip())
        if heading:
            level, text = heading.groups()
            if len(level) == 1:
                headings[SLOT_H1].append(text)
            elif len(level) == 2:
                headings[SLOT_H2].append(text)
    return {
        SLOT_H1: '\n'.join(headings[SLOT_H1]),
        SLOT_H2: '\n'.join(headings[SLOT_H2]),
        SLOT_CONTENT: copy or '',
    }


def contains_keyword(text, keyword):
    """Whether ``keyword`` appears in ``text``, by Odoo's own rule.

    This is ``isKeywordIn`` from Odoo's SEO dialog, in Python: the keyword
    matched **literally**, case-insensitively, with a word separator or the end
    of the string on either side.

    Literally is the part worth knowing. "odoo implementation partners" does
    **not** contain "odoo implementation partner" - the ``s`` is not a separator
    - and "Odoo ERP, consulting" does not contain "odoo erp consulting", because
    the comma is not in the keyword. Both are stricter than they look, and both
    are what Odoo's dialog will show, which is the point: a keyword this module
    called placed and Odoo marks missing would just be two tools disagreeing in
    front of the user.
    """
    if not (keyword or '').strip():
        return False
    pattern = SEO_BOUNDARY + re.escape(keyword.strip()) + SEO_BOUNDARY
    return bool(re.search(pattern, text or '', re.IGNORECASE | re.UNICODE))


def missing_keywords(text, keywords):
    """The keywords that do not appear in ``text`` at all."""
    return [keyword for keyword in keywords
            if (keyword or '').strip() and not contains_keyword(text, keyword)]


def keyword_placement(copy, keywords, title='', description=''):
    """Where each keyword sits, and which of its wanted slots are empty.

    Returns a list of ``{keyword, main, found, wanted, missing}`` in the order
    the keywords were given, so the first entry is always the main keyword.
    """
    parts = split_copy_slots(copy)
    parts[SLOT_TITLE] = title or ''
    parts[SLOT_DESCRIPTION] = description or ''
    report = []
    for index, keyword in enumerate(keywords):
        if not (keyword or '').strip():
            continue
        found = [slot for slot in SEO_SLOTS
                 if contains_keyword(parts.get(slot, ''), keyword)]
        wanted = MAIN_KEYWORD_SLOTS if index == 0 else SUB_KEYWORD_SLOTS
        report.append({
            'keyword': keyword,
            'main': index == 0,
            'found': found,
            'wanted': list(wanted),
            'missing': [slot for slot in wanted if slot not in found],
        })
    return report


def placement_gaps(report):
    """The rows of a placement report that are still short of their slots."""
    return [row for row in report if row['missing']]


def _slots_filled(report):
    """How many aimed-at slots the copy actually fills. The score to beat."""
    return sum(len(set(row['found']) & set(row['wanted'])) for row in report)


def _default_ai_model(self):
    return self.env['cap.ai.model']._get_default_model()


def _extract_json(answer):
    """Pull the JSON object out of an answer that may be wrapped in prose."""
    if not answer:
        return None
    text = answer.strip()
    if '```' in text:
        parts = text.split('```')
        text = max(parts, key=len)
        if text.lstrip().startswith('json'):
            text = text.lstrip()[4:]
    start, end = text.find('{'), text.rfind('}')
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return None


def _render_surfer_brief(brief):
    """Turn Surfer's brief into the instructions the writer works from.

    A term with no range is only a word to sprinkle; with its range it is a
    target that can be met or missed. Same for the structure: Surfer states how
    long the page should be and how many headings it wants, and the writer can
    only hit that if it is told.
    """
    terms = brief.get('terms') or []
    priority, secondary = terms[:SURFER_PRIORITY_TERMS], terms[SURFER_PRIORITY_TERMS:]
    if not (priority or brief.get('structure') or brief.get('questions')):
        return ''

    def term_line(term):
        if term.get('max'):
            return _('- "%(term)s": %(min)s-%(max)s times',
                     term=term['term'], min=term['min'], max=term['max'])
        return _('- "%(term)s": at least %(min)s times',
                 term=term['term'], min=term['min'])

    parts = [_(
        "=== WHAT SURFER SEO SAYS THIS PAGE MUST DO ===\n"
        "Surfer analysed the pages that currently rank for these keywords. "
        "Meet these targets in copy a person would want to read: stay inside "
        "every range, and never pad to reach one.")]

    structure = brief.get('structure') or {}
    if structure:
        lines = []
        for factor, target in structure.items():
            label = research_client.STRUCTURE_FACTORS.get(factor, factor)
            line = '- %s: aim for %s' % (label, target['target'])
            if target['min'] != target['max']:
                line += _(' (accepted %(min)s-%(max)s)',
                          min=target['min'], max=target['max'])
            lines.append(line)
        parts.append(_("TARGET STRUCTURE\n%s") % '\n'.join(lines))

    if priority:
        parts.append(_(
            "PRIORITY TERMS - stay inside the ranges, never go above the "
            "maximum\n%s") % '\n'.join(term_line(term) for term in priority))
    if secondary:
        parts.append(_(
            "SECONDARY TERMS - weave in naturally, do not force them\n%s")
            % ', '.join(term['term'] for term in secondary))

    headings = [term['term'] for term in terms if term.get('heading')]
    if headings:
        parts.append(_("PUT THESE IN H2/H3 HEADINGS\n%s")
                     % ', '.join(headings[:SURFER_HEADING_TERMS]))

    questions = brief.get('questions') or []
    if questions:
        parts.append(_(
            "QUESTIONS TO ANSWER - one section each, answered in the first "
            "sentence\n%s") % '\n'.join(
                '- %s' % question for question in questions[:SURFER_QUESTIONS]))

    covered = brief.get('competitor_headings') or []
    if covered:
        parts.append(_(
            "TOPICS THE COMPETITORS COVER - so you miss nothing, but do not "
            "copy them\n%s") % '\n'.join(
                '- %s' % heading for heading in covered[:SURFER_COMPETITOR_HEADINGS]))

    if brief.get('avg_score'):
        parts.append(_(
            "WHAT THE COMPETITION SCORES - beat it\n- average content score "
            "%(avg)s, best %(best)s",
            avg=brief['avg_score'], best=brief['best_score']))
    return '\n\n'.join(parts)


def _batch_slots(slots, budget):
    """Group text slots into runs small enough for one call.

    Yields ``[(index, text)]`` keeping each slot's position in the whole page,
    because that number is what the answer refers back to.
    """
    batch, size = [], 0
    for index, (_node, _which, text) in enumerate(slots):
        text = ' '.join(text.split())
        if not text:
            continue
        if batch and size + len(text) > budget:
            yield batch
            batch, size = [], 0
        batch.append((index, text))
        size += len(text)
    if batch:
        yield batch


def _clean_description(answer):
    """Strip the wrappers models like to add, and cut to snippet length."""
    text = ' '.join((answer or '').split())
    if not text:
        return ''
    # "Meta description: ..." / "Description: ..."
    for label in ('meta description:', 'description:'):
        if text.lower().startswith(label):
            text = text[len(label):].strip()
    text = text.strip('"“”\'`')
    if len(text) <= META_DESCRIPTION_CHARS:
        return text
    # Cut on a word boundary rather than mid-word.
    cut = text[:META_DESCRIPTION_CHARS]
    if ' ' in cut:
        cut = cut[:cut.rfind(' ')]
    return cut.rstrip(' ,;:-') + '…'


class CapWebsiteBuilder(models.Model):
    _name = 'cap.website.builder'
    _description = 'AI Website Page Request'
    _inherit = ['mail.thread']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Title', required=True, default=lambda self: _('New page request'))
    mode = fields.Selection(
        [('create', 'Create a new page'), ('edit', 'Edit an existing page')],
        string='Mode', default='create', required=True)
    ai_model_id = fields.Many2one(
        'cap.ai.model', string='AI Model', required=True,
        default=_default_ai_model, ondelete='restrict')
    reference_page_id = fields.Many2one(
        'website.page', string='Content Reference Page',
        help="Reference for what the page says, never for how it looks. Its "
             "text is read; its markup never is.\n"
             "In create mode: source material for the writer - the products, "
             "the figures, the names, the way this company describes what it "
             "does.\n"
             "In edit mode: the page being rewritten, and its current text is "
             "the base the new copy starts from.")
    template_page_id = fields.Many2one(
        'website.page', string='Design Template',
        domain=TEMPLATE_DOMAIN,
        help="Which of the theme's page templates the page is built to look "
             "like - Industry, Sector hub, Case study, and so on.\n"
             "Reference for how the page looks, never for what it says: its "
             "snippets, classes and structure are copied; its words are "
             "ignored.\n"
             "In edit mode this decides what happens to the page: pick a "
             "template and the page is rebuilt to it, replacing its current "
             "design. Leave it empty and only the words change - the existing "
             "layout, images and blocks are kept exactly as they are.\n"
             "In create mode, left empty, the design is taken from the site's "
             "own pages or from the standard Odoo snippets.")
    allow_extra_snippets = fields.Boolean(
        string='May Add Theme Sections',
        help="Off, a page built to a design template gets exactly the template's "
             "sections: the AI only writes the text that goes in them.\n"
             "On, and only if your instructions ask for something the template "
             "does not cover, the AI may also add whole blocks from the Captivea "
             "theme's snippet catalogue. It chooses which block and where; the "
             "markup is inserted by the module, unchanged, exactly as the "
             "website builder would drop it.")
    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].get_current_website())
    prompt = fields.Text(
        string='Instructions',
        help="Describe the page you want, or the change to apply.")
    draft_arch = fields.Html(
        string='Draft', sanitize=False,
        help="What the AI produced. You can edit it before applying it.")
    page_url = fields.Char(string='Page URL', help="For example /our-services")
    page_title = fields.Char(string='Page Title')
    main_keyword = fields.Char(
        string='Main Keyword',
        help="The phrase this page should rank for.")
    use_surfer = fields.Boolean(
        string='Use Surfer SEO', default=lambda self: self._default_use_surfer(),
        help="Ask Surfer SEO what a page on these keywords has to cover, and "
             "give its answer to the AI as the brief for the copy. Unticked, "
             "the AI works the coverage out itself.")
    sub_keywords = fields.Text(
        string='Sub Keywords', readonly=True, copy=False,
        help="The strongest phrases found around the main keyword, one per "
             "line. Written when you press Generate.")
    surfer_score_target = fields.Float(
        string='Target Surfer Score', default=70,
        help="The Surfer content score the copy has to reach. After each "
             "attempt the article is pushed back to Surfer and scored; if it "
             "falls short the AI rewrites it and it is scored again, up to "
             "3 rounds. Set 0 to write the copy once and never score it.")
    surfer_score = fields.Float(
        string='Surfer Score', readonly=True, copy=False,
        help="The best score the copy reached, out of 100.")
    surfer_score_rounds = fields.Integer(
        string='Scoring Rounds', readonly=True, copy=False)
    surfer_editor_id = fields.Char(
        string='Surfer Content Editor', readonly=True, copy=False,
        help="The editor the brief came from. The article is pushed back into "
             "it to be scored, so both refer to the same SERP analysis.")
    surfer_workspace_id = fields.Char(
        string='Surfer Workspace', readonly=True, copy=False)
    surfer_keyword = fields.Char(
        string='Analysed Keywords', readonly=True, copy=False,
        help="The main keyword the Content Editor was created for. While it is "
             "unchanged the same editor is reused, so a retry costs no credit. "
             "Change the main keyword and a fresh analysis is run.")
    content_ideas = fields.Text(
        string='Content Ideas', readonly=True, copy=False,
        help="What people ask around these keywords, from the same web search "
             "that found the sub keywords. Used as the page's H2 headings, so "
             "the sections answer questions that were really searched for.")
    surfer_terms = fields.Text(
        string='Surfer Terms', readonly=True, copy=False,
        help="What Surfer says a page on these keywords has to cover. Empty "
             "when no Surfer key is configured, or when Surfer was still "
             "analysing.")
    article_body = fields.Text(
        string='Page Copy', readonly=True, copy=False,
        help="The copy of the page as plain text, before it was turned into "
             "website snippets.")
    content_source = fields.Selection(
        [('ai', 'AI only'), ('surfer', 'Surfer brief + AI')],
        string='Copy Written With', readonly=True, copy=False)
    description = fields.Text(
        string='Page Description',
        help="A brief description of what this page is about. It is given to "
             "the AI as the brief for the page, and written to the page's "
             "meta description when you apply it, which is what search "
             "engines show under the title.")
    state = fields.Selection(
        [('draft', 'Draft'), ('generated', 'Generated'), ('applied', 'Applied')],
        string='Status', default='draft', required=True, tracking=True)
    page_id = fields.Many2one(
        'website.page', string='Resulting Page', readonly=True, copy=False)
    conversation_json = fields.Text(
        string='Conversation', default='[]', copy=False,
        help="Machine readable history sent back to the model on each turn. "
             "The human readable version lives in the chatter below.")

    @api.model
    def _default_use_surfer(self):
        """Ticked when there is a key to use, so the default is the useful one
        without ever promising a service that is not configured."""
        return bool(research_client.available_sources(self.env).get('surfer'))

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------
    def _check_builder_group(self):
        """Writing on the website is a designer action, check it in code as
        well so RPC callers cannot bypass the UI."""
        if not self.env.user.has_group('website.group_website_designer'):
            raise AccessError(_(
                "You need Website Designer access rights to generate or apply "
                "AI page content."))

    # ------------------------------------------------------------------
    # Conversation helpers
    # ------------------------------------------------------------------
    def _get_history(self):
        try:
            history = json.loads(self.conversation_json or '[]')
        except ValueError:
            history = []
        return history if isinstance(history, list) else []

    def _append_history(self, role, content):
        history = self._get_history()
        history.append({'role': role, 'content': content})
        self.conversation_json = json.dumps(history)

    def _stack_prompt(self, base, extra, header, contract):
        """Global prompt, then this template's, then the module's contract.

        The global prompt is the base and is always sent. A design template's
        instructions are **added after** it, never in place of it: what a case
        study needs is knowledge about that template, but it sits on top of the
        general rules rather than replacing them - a template author writing
        "open with the client and the headline result" should not also have to
        restate that an ``<img>`` closes itself for their page to load.

        The contract goes last, and only when a template contributed something.
        It is not style guidance but the shape the next step can work with, so
        it takes the final word over whatever the template asked for.
        """
        base = (base or '').strip()
        extra = (extra or '').strip()
        if not extra:
            return base
        return '%s\n\n%s\n%s\n\n%s' % (base, header, extra, contract)

    def _get_content_prompt(self):
        """The system prompt for the step that writes the copy.

        Content and SEO only. At this point the page has no layout and the
        answer is plain text, so nothing about markup belongs here - that is
        what ``_get_system_prompt`` is for, one step later.
        """
        template = self.template_page_id.sudo()
        return self._stack_prompt(
            '%s\n\n%s' % (
                ARTICLE_PROMPT,
                (self.ai_model_id.sudo().content_prompt or '').strip()),
            template.cap_content_prompt if template else '',
            TEMPLATE_CONTENT_HEADER, COPY_CONTRACT)

    def _get_system_prompt(self):
        """The system prompt for the steps that build the page.

        Style and layout. The model's page prompt carries the output rules and
        the XML rules an Odoo view arch has to satisfy, which hold for every
        page whatever it looks like.
        """
        template = self.template_page_id.sudo()
        return self._stack_prompt(
            (self.ai_model_id.sudo().system_prompt or '').strip()
            or FALLBACK_SYSTEM_PROMPT,
            template.cap_builder_prompt if template else '',
            TEMPLATE_DESIGN_HEADER, OUTPUT_CONTRACT)

    def _get_max_context_chars(self):
        return self.ai_model_id.sudo().max_context_chars or DEFAULT_MAX_CONTEXT_CHARS

    def _get_page_context(self):
        """Build the reference-page block prepended to the first user message.

        The reference is sent in two parts, because neither alone is enough to
        reproduce a site's style: a structural outline of the *whole* page, so
        no section is invisible to the AI however long the page is, and then as
        many complete blocks of real markup as the budget allows, as verbatim
        examples to copy from.
        """
        # Only the design template supplies design, in both modes. Falling back
        # to the content reference would quietly make it one, which is the
        # confusion these two fields exist to remove - and in edit mode falling
        # back to the page being edited would rebuild it to its own old design,
        # which is the thing choosing a template is meant to change.
        page = self.template_page_id
        if not page:
            return ''
        # Always what the page actually renders, with its inheriting views
        # applied: read without them, a COWed view comes back in its generic
        # form, which is how a page that looks current on the site arrives here
        # as an outdated layout.
        combined = True
        blocks = page_writer.page_blocks(page, combined=combined)
        if not blocks:
            return ''

        limit = self._get_max_context_chars()
        outline = page_writer.structure_outline(page, combined=combined)
        # The outline is the part that must never be cut: it is the only view
        # of the page that is guaranteed to be complete.
        outline_limit = max(int(limit * 0.4), 1)
        if len(outline) > outline_limit:
            outline = outline[:outline_limit]

        inventory = page_writer.snippet_inventory(page, combined=combined)
        palette = '\n'.join(
            '- %s (used %s time(s))' % (key, count) for key, count in inventory)
        # Offering URLs and then forbidding images is a contradiction the model
        # resolves the wrong way round, so none are offered.
        image_list = _(
            "This page is text only. Do not use any image: not one of this "
            "page's, not one of your own.")

        # One full example per snippet type, so every kind of block on the page
        # is demonstrated rather than just the ones at the top.
        examples = page_writer.representative_blocks(page, combined=combined)
        budget = limit - len(outline) - len(palette) - len(image_list)
        sample, used = [], 0
        for key, block in examples:
            block = page_writer.strip_images(block)[0]
            if used + len(block) > budget:
                break
            sample.append('<!-- snippet: %s -->\n%s' % (key, block))
            used += len(block)
        if not sample and examples:
            sample = [examples[0][1][:max(budget, 1)]]
        if len(sample) < len(examples):
            self.message_post(body=Markup('<p>%s</p>') % _(
                "The reference page uses %(total)s kinds of block; %(sent)s of "
                "them were sent to the AI as full markup examples, plus the "
                "outline of the whole page. Raise the reference page limit on "
                "the AI model to send more.",
                total=len(examples), sent=len(sample)))

        if self.mode == 'edit':
            header = _(
                "Here is the page to rewrite. Return the complete new content "
                "of its body, built from the same snippets it already uses "
                "unless the instructions ask for something different.")
        else:
            header = _(
                "Here is the design reference: an existing page whose look the "
                "new page must reuse. Build the new page by copying whole "
                "blocks from the examples below and swapping their text: same "
                "snippet types, same classes, same builder attributes, same "
                "structure. Do not design new sections.\n\n"
                "Its words are not yours. Every sentence in these examples is "
                "placeholder as far as you are concerned - the copy for this "
                "page has already been written and is given above. Take the "
                "markup and leave the subject matter behind, however relevant "
                "it looks.")
        return (
            '%s\n\n'
            '=== THE ONLY BLOCK TYPES YOU MAY USE ===\n%s\n\n'
            '=== THE ONLY IMAGE URLS YOU MAY USE ===\n'
            'Reuse these exactly as written, or leave the image out. Any other '
            'URL renders as a broken-image placeholder.\n%s\n\n'
            '=== STRUCTURE OF THE WHOLE REFERENCE PAGE ===\n%s\n\n'
            '=== FULL MARKUP, ONE EXAMPLE PER BLOCK TYPE ===\n%s\n\n'
            % (header, palette, image_list, outline, '\n\n'.join(sample))
        )

    def _get_brief(self):
        """The page description, given to the AI as the brief for the page."""
        if not self.description:
            return ''
        return _(
            "=== WHAT THIS PAGE IS ABOUT ===\n%s\n\n"
            "Write the page to deliver exactly this. Do not drift onto "
            "adjacent subjects.\n\n"
        ) % self.description.strip()

    def _write_description(self, provider, arch):
        """Ask the AI for a meta description of the page it just wrote."""
        text = page_writer.text_of(arch)
        if not text:
            return ''
        limit = self._get_max_context_chars()
        answer = provider.chat(DESCRIPTION_PROMPT, [{
            'role': 'user',
            'content': 'Page title: %s\n\nPage content:\n%s' % (
                self.page_title or self.name or '', text[:limit // 2]),
        }])
        return _clean_description(answer)

    def _build_messages(self):
        messages = self._get_history()
        context = (self._get_brief() + self._get_page_context()) if not messages else ''
        messages.append({'role': 'user', 'content': context + (self.prompt or '')})
        return messages

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------
    def _step_description(self, provider):
        """Step one: a description, written only when the user left it empty."""
        if self.description:
            return self.description.strip()
        answer = provider.chat(DESCRIPTION_PROMPT, [{
            'role': 'user',
            'content': _(
                "Page title: %(title)s\nMain keyword: %(keyword)s\n\n"
                "The page does not exist yet: describe what it will be about."
                "%(source)s",
                title=self.page_title or self.name or '',
                keyword=self.main_keyword or '',
                source=self._get_content_reference()),
        }])
        description = _clean_description(answer)
        if description:
            self.description = description
            self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
                _("Description written for you:"), description))
        return description

    def _step_sub_keywords(self, provider):
        """Step two: search the web for the strongest phrases around the main
        keyword, and keep the top ones.

        Returns the main keyword followed by the sub keywords.
        """
        main = (self.main_keyword or '').strip()
        question = _(
            "Main keyword: %(keyword)s\nPage title: %(title)s\n"
            "What the page is about: %(description)s",
            keyword=main, title=self.page_title or self.name or '',
            description=self.description or _("(not given)"))

        answer = provider.chat(
            KEYWORD_PROMPT, [{'role': 'user', 'content': question}],
            web_search=True)
        payload = _extract_json(answer) or {}
        found, seen = [], {main.lower()}
        for keyword in payload.get('keywords') or []:
            if not isinstance(keyword, str):
                continue
            keyword = keyword.strip()
            if not keyword or keyword.lower() in seen:
                continue
            seen.add(keyword.lower())
            found.append(keyword)
            if len(found) >= SUB_KEYWORD_COUNT:
                break

        # The content ideas ride along on the search already being paid for.
        # They are the H2 material: headings taken from what people searched
        # beat headings a model invented, and this is the one call in the
        # pipeline that has actually looked.
        ideas, seen_ideas = [], set()
        for idea in payload.get('ideas') or []:
            if not isinstance(idea, str):
                continue
            idea = idea.strip()
            if not idea or idea.casefold() in seen_ideas:
                continue
            seen_ideas.add(idea.casefold())
            ideas.append(idea)
            if len(ideas) >= CONTENT_IDEA_COUNT:
                break
        self.content_ideas = '\n'.join(ideas)
        if ideas:
            self.message_post(body=Markup('<p><b>%s</b></p><p>%s</p>') % (
                _("Content ideas from the search"),
                Markup('<br/>').join(ideas)))

        self.sub_keywords = '\n'.join(found)
        if found:
            note = Markup('<br/>').join(found)
            if not provider.supports_web_search:
                # Say so rather than let the user believe a search happened:
                # only Anthropic runs one, the others answer from memory.
                note += Markup('<br/><i>%s</i>') % _(
                    "This provider cannot search the web, so these come from "
                    "the model's own knowledge.")
            self.message_post(body=Markup('<p><b>%s</b></p><p>%s</p>') % (
                _("Sub keywords for \"%s\"", main), note))
        else:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "No sub keywords were found for \"%s\"; the page is written "
                "on the main keyword alone.", main))
        return [main] + found

    def _remember_surfer_editor(self, started, signature):
        """Write down which Content Editor this request is working with, and
        commit it before anything else can go wrong.

        A credit has been spent by the time this runs. Everything after it - the
        copy, the scoring rounds, the layout - can fail, and an exception rolls
        the transaction back and takes the editor id with it, so the next
        Generate orders the same analysis again. Committing here is what makes
        pressing Generate after a failure free.

        Losing it is no longer fatal either: ``ensure_content_editor`` finds the
        editor by keyword next time. This just saves the round trip, and keeps
        the id visible on the request while the run is still going.
        """
        self.ensure_one()
        self.write({
            'surfer_editor_id': str(started['editor_id']),
            'surfer_workspace_id': str(started['workspace_id']),
            'surfer_keyword': signature,
        })
        origin = started.get('origin')
        if origin == 'reused':
            self.message_post(body=Markup('<p>%s</p>') % _(
                "Surfer had already analysed \"%(keyword)s\" (editor "
                "%(editor)s, run %(when)s), so that analysis is used and no "
                "credit is spent.",
                keyword=signature, editor=started['editor_id'],
                when=started.get('created_at') or _("earlier")))
        elif origin == 'recovered':
            self.message_post(body=Markup('<p>%s</p>') % _(
                "The connection to Surfer dropped while the analysis was being "
                "ordered. The job it had already started was found and picked "
                "up (editor %s), so nothing is ordered twice.",
                started['editor_id']))
        # Never inside a test run, where committing escapes the rollback that
        # keeps one test from leaking into the next. Keyed on `current_test`,
        # which is set only while a test is actually running, and not on
        # `config['test_enable']`: this server carries test_enable=True in its
        # odoo.conf for the whole process, so that flag would switch the commit
        # off in ordinary use - exactly when it is needed.
        if not modules.module.current_test:
            self.env.cr.commit()

    def _step_surfer_terms(self, keywords):
        """Step three, when the request asks for Surfer: ask it what a page on
        these keywords has to contain.

        Whether Surfer runs is the user's choice, not a side effect of a key
        being present somewhere in the settings.

        Returns ``(brief as text, brief as data)``. Both are empty when Surfer
        was not asked for, could not answer, or is still analysing: the brief
        feeds step four and its data feeds the scoring, and neither is ever a
        blocker.
        """
        if not self.use_surfer:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "Surfer SEO is off on this request, so the AI works out what "
                "the page has to cover from the %s keywords itself.",
                len(keywords)))
            return '', None
        if not research_client.available_sources(self.env).get('surfer'):
            # Normally unreachable: _run_pipeline refuses to start without the
            # key. Kept for a refinement turn or an RPC caller.
            self.message_post(body=Markup('<p>%s</p>') % _(
                "No Surfer API key is configured, so the AI works out what the "
                "page has to cover from the %s keywords itself.",
                len(keywords)))
            return '', None
        # Keyed on the main keyword alone. The sub keywords come from a fresh
        # web search each run and drift between them, so keying on all four
        # would mean a new editor - and a new credit - on every retry, which is
        # the opposite of what reuse is for. The main keyword is what anchors
        # Surfer's SERP analysis anyway.
        signature = keywords[0]
        try:
            client = research_client.get_surfer(self.env)
            # A Content Editor costs a credit and takes minutes. While the
            # keywords are unchanged the analysis is still the right one, so a
            # retry after a failure reuses it instead of paying again.
            if self.surfer_editor_id and self.surfer_keyword == signature:
                self.message_post(body=Markup('<p>%s</p>') % _(
                    "Reusing the Surfer analysis already run for these "
                    "keywords (editor %s). No new credit is spent.",
                    self.surfer_editor_id))
            else:
                # Asks Surfer what it already has before ordering anything, and
                # if the order is placed but the answer is lost, finds the job
                # it started rather than starting a second one.
                started = client.ensure_content_editor(
                    keywords[0], secondary_keywords=keywords[1:],
                    custom_instructions=self.description or None)
                self._remember_surfer_editor(started, signature)
            brief = client.fetch_content_brief(
                self.surfer_editor_id, workspace_id=self.surfer_workspace_id)
        except ResearchError as error:
            self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
                _("Surfer could not be used, the AI writes the copy alone:"),
                str(error)))
            return '', None

        if brief is None:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "Surfer was still analysing after %s seconds, so the copy is "
                "written without its brief. The editor keeps running on "
                "Surfer's side; generate again to pick it up.",
                research_client.SURFER_WAIT_SECONDS))
            return '', None

        text = _render_surfer_brief(brief)
        self.surfer_terms = text
        if text:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "Surfer analysed the pages that rank for these keywords: "
                "%(terms)s scored terms, %(questions)s questions, "
                "%(competitors)s competitors. The AI now writes the page copy "
                "to that brief.",
                terms=len(brief['terms']), questions=len(brief['questions']),
                competitors=len(brief['competitors'])))
        return text, brief

    def _get_content_reference(self):
        """The content reference page as source material for the writer.

        Its text is sent, never its markup. What is wanted here is the subject
        matter - the products, the figures, the names - not the layout, which
        is the design template's job.

        Used in both modes, and the framing differs. In create mode the page is
        a *source* to draw on for a page that does not exist yet. In edit mode
        it is the page being rewritten, so its text is the *base* the new copy
        starts from: what is already true about this page stays true unless the
        brief says otherwise, rather than being paraphrased away.
        """
        self.ensure_one()
        page = self.reference_page_id
        if not page:
            return ''
        text = page_writer.text_of(page_writer.page_body(page, combined=True))
        if not text:
            return ''
        limit = max(self._get_max_context_chars() // 3, 2000)
        if self.mode == 'edit':
            return _(
                "\n=== THE CURRENT TEXT OF THE PAGE YOU ARE REWRITING ===\n"
                "This is what %(url)s says today. It is the base for the new "
                "copy, not a page to summarise: keep the facts that are still "
                "true - the products, the figures, the names, the claims this "
                "company makes - and rewrite around them to the brief above. "
                "Drop only what the brief supersedes or what is no longer "
                "accurate, and add what the brief asks for that is missing.\n\n"
                "How it is laid out is not your concern here: the new page is "
                "built to the design template, not to this page's markup.\n"
                "%(text)s\n",
                url=page.url or page.name, text=text[:limit])
        return _(
            "\n=== SOURCE MATERIAL FROM AN EXISTING PAGE ===\n"
            "This is the text of %(url)s, the content reference for this "
            "page: subject matter, not a model to imitate. Take from it what is "
            "true and relevant - the products, the figures, the names, the way "
            "this company describes what it does - and write fresh copy. Do "
            "not copy its sentences, and leave out anything that belongs only "
            "to that page.\n\n"
            "It says nothing about how the new page is laid out. That comes "
            "from the design template, separately, and is none of your "
            "concern here.\n%(text)s\n",
            url=page.url or page.name, text=text[:limit])

    def _get_template_brief(self):
        """The design template's sections, as the shape the copy has to fit.

        Written into the *copy* prompt, not the layout one, and that is the
        point: the page's design is decided before a word of it exists, so the
        copy is commissioned section by section against the slots that are
        actually there. Without this the writer produces a well argued page of
        its own shape, and half of it then has nowhere to go.
        """
        self.ensure_one()
        if not self.template_page_id:
            return ''
        root = self._parse_body(self._template_body())
        if root is None or not len(root):
            return ''
        lines = []
        blocks = [child for child in root if isinstance(child.tag, str)]
        for number, block in enumerate(blocks, start=1):
            markup = etree.tostring(block, encoding='unicode', method='xml')
            hints = theme_snippets.placeholder_hints(markup, limit=6)
            line = '%s. %s' % (number, self._block_label(block))
            if hints:
                line += ': %s' % '; '.join(hints)
            lines.append(line)
        return _(
            "\n=== THE SECTIONS THIS PAGE WILL HAVE, IN ORDER ===\n"
            "The page is built to the \"%(template)s\" template, whose design is "
            "already decided. These are its sections, each with what it asks "
            "for. Write the copy to fit them: one \"## \" section per numbered "
            "block, in this order, saying what that block asks for and no more. "
            "Do not propose sections of your own and do not leave one of these "
            "with nothing to say - a block with no copy stays on the page "
            "showing its placeholder.\n%(sections)s\n",
            template=self.template_page_id.name, sections='\n'.join(lines))

    def _step_copy(self, provider, keywords, terms, feedback=None):
        """Step four: write the page copy.

        Two routes, same output. With a Surfer brief the coverage is Surfer's;
        without one the model plans its own coverage from the keywords first,
        so a database with no Surfer key still gets a page built on all four of
        them rather than free prose around the title.
        """
        brief = _(
            "Page title: %(title)s\n"
            "What the page is about: %(description)s\n"
            "Main keyword: %(main)s\n"
            "Sub keywords: %(subs)s\n",
            title=self.page_title or self.name or '',
            description=self.description or _("(not given)"),
            main=keywords[0],
            subs=', '.join(keywords[1:]) or _("(none)"))
        # Listed again as a requirement rather than left as two header lines.
        # This block is the same whichever route runs below, so the rule does
        # not depend on whether Surfer answered - and the copy is checked
        # against exactly this list before it is turned into a page.
        brief += _(
            "\n=== WHERE EACH OF THESE %(count)s KEYWORDS HAS TO APPEAR ===\n"
            "%(list)s\n"
            "These are the placements an SEO tool scores, so cover as many as "
            "each keyword can carry:\n"
            "- The MAIN keyword: in the H1, in the opening paragraph, and in "
            "the body where it belongs. It is also wanted in the page's title "
            "tag and meta description, which are set elsewhere - write the H1 "
            "so it can be reused as the title.\n"
            "- Each SUB keyword: in the \"## \" heading of the section that is "
            "about it, and in the words under that heading.\n"
            "Each one written **exactly** as given, because this is checked "
            "literally, the way Odoo's own SEO panel checks it:\n"
            "- Same words in the same order, single spaces, nothing inserted "
            "between them - \"odoo erp consulting\" is not matched by \"Odoo "
            "ERP, consulting\".\n"
            "- Singular stays singular. \"odoo implementation partners\" does "
            "not count as \"odoo implementation partner\", so write the phrase "
            "as given and let the rest of the sentence carry the plural.\n"
            "- On one line. A keyword broken across a line break does not "
            "count.\n"
            "Once per placement is enough - repeating a keyword to make it "
            "count reads as padding and helps nothing, and two keywords "
            "crammed into one H1 rank for neither.\n",
            count=len(keywords),
            list='\n'.join('- %s' % keyword for keyword in keywords))
        ideas = [line.strip() for line in (self.content_ideas or '').splitlines()
                 if line.strip()]
        if ideas:
            # From the keyword step's web search, so these are what people
            # actually looked for rather than sections a model imagined. Offered
            # as material, not as a running order: a page that answers six of
            # them well beats one that lists all eight.
            brief += _(
                "\n=== CONTENT IDEAS FROM GOOGLE SEARCHES ===\n"
                "%(ideas)s\n"
                "These came from searching what people ask around these "
                "keywords. Use them as the H2 headings wherever one fits the "
                "page, phrased close to how it was searched. Skip any that "
                "this page has no business answering, and never keep one as a "
                "heading with nothing under it.\n",
                ideas='\n'.join('- %s' % idea for idea in ideas))
        if terms:
            brief += '\n' + terms + '\n'
        else:
            brief += _(
                "\n=== NO KEYWORD TOOL IS AVAILABLE, PLAN THE COVERAGE "
                "YOURSELF ===\n"
                "Nothing analysed the pages that currently rank for these "
                "keywords, so do that job before you write:\n"
                "1. Decide what someone searching each of the keywords above "
                "expects to find on the page. Give every keyword a section of "
                "its own, in the order a reader needs them.\n"
                "2. For each section, decide the specific terms, questions and "
                "figures a page on that keyword has to contain to be worth "
                "reading, and cover them.\n"
                "3. Then write the page. Do not show your plan: the answer is "
                "the finished copy.\n")
        template = self._get_template_brief()
        if template:
            brief += template
        source = self._get_content_reference()
        if source:
            brief += source
        if self.prompt:
            brief += _("\n=== EXTRA INSTRUCTIONS FROM THE USER ===\n%s\n") % self.prompt
        if feedback:
            brief += _("\n=== WHY THE LAST ATTEMPT WAS NOT GOOD ENOUGH ===\n%s\n") % feedback

        # Which prompt wrote the words is worth having on the record: two runs
        # from the same brief can read differently because one template carries
        # content instructions and another does not.
        if self.template_page_id \
                and self.template_page_id.sudo().cap_content_prompt:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "Written to the content instructions on the \"%s\" template, "
                "added to the AI model's Content & SEO prompt.",
                self.template_page_id.name))
        copy = provider.chat(
            self._get_content_prompt(), [{'role': 'user', 'content': brief}])
        copy = (copy or '').strip()
        if not copy:
            raise AIProviderError(_("The AI returned no copy for the page."))
        self.article_body = copy
        self.content_source = 'surfer' if terms else 'ai'
        return copy

    def _get_style_guide(self, website):
        """The site's own CSS and JS, reported once so a silent miss is visible."""
        self.ensure_one()
        guide = theme_style.style_guide(self.env, website)
        if guide:
            blocks = theme_style.custom_css(self.env, website)
            rules = theme_style.class_rules(blocks)
            # Name the modules: a style guide built from the wrong ones looks
            # exactly like a page that ignored the design, and only this line
            # tells the two apart.
            self.message_post(body=Markup('<p><b>%s</b><br/>%s</p>') % (
                _("Building with the styles of %(site)s: %(count)s classes "
                  "from", site=website.name if website else '',
                  count=len(rules)),
                ', '.join('%s (%s KB)' % (module, round(size / 1024))
                          for module, size in theme_style.sources(blocks))))
        else:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "%s has no custom CSS of its own, so the page is built from "
                "the theme's standard snippets only.",
                website.name if website else _("This website")))
        return guide

    def _score_feedback(self, brief, copy, score):
        """What is wrong with this draft, in terms the writer can act on.

        Surfer's number says the copy fell short; only the local checks say
        where. They are free and instant, so they run on every round.
        """
        lines = []
        terms = research_client.term_report(copy, brief.get('terms') or [])
        low = [row for row in terms if row['state'] == 'low']
        high = [row for row in terms if row['state'] == 'high']
        missing = [row['term'] for row in terms if not row['in_heading']]

        if low:
            lines.append(_("Under their minimum - use each of these more:\n%s")
                         % '\n'.join(
                             '- "%s": %s now, needs %s' % (
                                 row['term'], row['count'], row['min'])
                             for row in low[:20]))
        if high:
            lines.append(_("Over their maximum - cut these back:\n%s")
                         % '\n'.join(
                             '- "%s": %s now, at most %s' % (
                                 row['term'], row['count'], row['max'])
                             for row in high[:10]))
        if missing:
            lines.append(_("Expected in an H2 or H3 heading, and not there: %s")
                         % ', '.join(missing[:8]))

        gaps = [row for row in research_client.structure_report(
            copy, brief.get('structure') or {}) if row['state'] != 'ok']
        if gaps:
            lines.append(_("Structure off target:\n%s") % '\n'.join(
                '- %s: %s now, aim for %s' % (
                    row['label'], row['value'], row['target'])
                for row in gaps))

        if not lines:
            # Everything countable is on target, so what is left is quality:
            # depth, specificity, answering the questions properly.
            lines.append(_(
                "Every term and every structural target is already met, so the "
                "score is being held back by the writing itself: answer each "
                "question more directly, go deeper where the copy is thin, and "
                "cut anything that says nothing."))
        return _(
            "The draft scored %(score)s out of 100 on Surfer; it has to reach "
            "%(target)s.\n\n%(gaps)s\n\nRewrite the whole article to fix "
            "this. Keep what already works, keep the same subject and "
            "structure, and return the finished markdown only.",
            score=round(score), target=round(self.surfer_score_target),
            gaps='\n\n'.join(lines))

    def _step_score(self, provider, keywords, terms, brief, copy):
        """Push the copy to Surfer, and rewrite it until it reaches the target.

        Returns the best-scoring version written, which is not always the last:
        a rewrite aimed at one gap can open another, and shipping a worse page
        than one already written would be perverse.
        """
        target = self.surfer_score_target
        if not (target and brief and self.surfer_editor_id):
            return copy

        client = research_client.get_surfer(self.env)
        best, best_score, rounds = copy, None, 0
        for attempt in range(1, SURFER_SCORE_ROUNDS + 1):
            try:
                score = client.score_content(
                    copy, self.surfer_editor_id,
                    workspace_id=self.surfer_workspace_id)['total']
            except ResearchError as error:
                self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
                    _("Surfer could not score the copy:"), str(error)))
                break
            rounds = attempt
            if score is None:
                self.message_post(body=Markup('<p>%s</p>') % _(
                    "Surfer did not return a score in time, so the copy is "
                    "kept as written."))
                break
            if best_score is None or score > best_score:
                best, best_score = copy, score

            if score >= target:
                self.message_post(body=Markup('<p>%s</p>') % _(
                    "Surfer scored the copy %(score)s out of 100, at or above "
                    "the %(target)s asked for, after %(rounds)s round(s).",
                    score=round(score), target=round(target), rounds=attempt))
                break
            if attempt == SURFER_SCORE_ROUNDS:
                self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
                    _("Surfer score not reached."),
                    _("After %(rounds)s rounds the best the copy scored is "
                      "%(score)s out of 100, short of the %(target)s asked "
                      "for. The best of the %(rounds)s versions is the one "
                      "kept. Lower the target, or add instructions telling the "
                      "AI what the page is missing, and generate again.",
                      rounds=SURFER_SCORE_ROUNDS, score=round(best_score),
                      target=round(target))))
                break

            self.message_post(body=Markup('<p>%s</p>') % _(
                "Round %(round)s: scored %(score)s out of 100, below the "
                "%(target)s asked for. Rewriting.",
                round=attempt, score=round(score), target=round(target)))
            try:
                copy = self._step_copy(
                    provider, keywords, terms,
                    feedback=self._score_feedback(brief, copy, score))
            except AIProviderError as error:
                self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
                    _("The rewrite failed, keeping the best draft so far:"),
                    str(error)))
                break

        self.write({
            'surfer_score': best_score or 0,
            'surfer_score_rounds': rounds,
        })
        self.article_body = best
        return best

    def _step_keyword_check(self, provider, keywords, copy):
        """Last gate before the copy becomes a page: are all the keywords in it?

        The check itself is local and free, so it runs on every request. Only a
        copy that is actually missing something costs an AI call, and a page
        that already covers its keywords - the normal outcome - costs nothing
        and adds no latency.

        Fixing the copy rather than the finished page is deliberate. Every route
        from here builds the page out of this text, so a keyword put in now ends
        up in the markup whichever route runs; a keyword injected into the markup
        afterwards would have to be threaded past a design template's slots and
        could not be done without touching the design.
        """
        report = self._keyword_placement(copy)
        gaps = placement_gaps(report)
        # Silent when it passes, which is the normal outcome. Only a gap this
        # step could not close is worth a line in the chatter.
        if not gaps:
            return copy

        for attempt in range(1, KEYWORD_FIX_ROUNDS + 1):
            # The title tag and the meta description are not the copy, and the
            # revision below cannot reach them: T is what the user typed, and D
            # is written by its own step. Only the copy slots are asked for.
            fixable = [row for row in gaps
                       if set(row['missing']) - {SLOT_TITLE, SLOT_DESCRIPTION}]
            if not fixable:
                self._report_head_gaps(gaps)
                return copy
            try:
                answer = provider.chat(self._get_content_prompt(), [{
                    'role': 'user',
                    'content': KEYWORD_FIX_PROMPT % {
                        'missing': self._placement_brief(fixable),
                        'copy': copy,
                    },
                }])
            except AIProviderError as error:
                # The copy is good enough to build a page from, so a failure
                # here is reported and stepped over rather than raised.
                self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
                    _("The keyword revision failed, keeping the copy as it is:"),
                    str(error)))
                return copy

            revised = (answer or '').strip()
            if not revised:
                self.message_post(body=Markup('<p>%s</p>') % _(
                    "The AI returned nothing, so the copy is kept as it is."))
                return copy

            # Only keep a revision that filled more slots than it emptied. A
            # model that moves a keyword out of a heading to put it in a
            # sentence has not helped, and taking that would be worse than
            # doing nothing.
            new_report = self._keyword_placement(revised)
            if _slots_filled(new_report) <= _slots_filled(report):
                self.message_post(body=Markup('<p>%s</p>') % _(
                    "Round %(round)s did not improve the placement, so the "
                    "previous copy is kept.", round=attempt))
                self._report_head_gaps(gaps)
                return copy

            copy, report = revised, new_report
            gaps = placement_gaps(report)
            self.article_body = copy
            if not gaps:
                return copy

        self._report_head_gaps(gaps, rounds=KEYWORD_FIX_ROUNDS)
        return copy

    def _keyword_placement(self, copy):
        """Where the request's keywords sit across the five SEO slots."""
        self.ensure_one()
        return keyword_placement(
            copy, self._all_keywords(),
            title=self.page_title or self.name or '',
            description=self.description or '')

    def _all_keywords(self):
        """The main keyword first, then the sub keywords, as one list."""
        self.ensure_one()
        main = (self.main_keyword or '').strip()
        subs = [line.strip() for line in (self.sub_keywords or '').splitlines()
                if line.strip()]
        return ([main] if main else []) + subs

    @staticmethod
    def _placement_brief(rows):
        """The gaps, as the list ``KEYWORD_FIX_PROMPT`` asks for."""
        return '\n'.join(
            '- "%s": missing from %s' % (
                row['keyword'],
                ', '.join(SLOT_NAMES[slot] for slot in row['missing']
                          if slot not in (SLOT_TITLE, SLOT_DESCRIPTION)))
            for row in rows)

    def _report_head_gaps(self, gaps, rounds=None):
        """Say what is still short, and whose job the remainder is.

        T and D are reported rather than repaired: the title tag is what the
        user typed on the request, and rewriting someone's page title to fit a
        keyword is not a trade this step is allowed to make.
        """
        head = [row for row in gaps
                if {SLOT_TITLE, SLOT_DESCRIPTION} & set(row['missing'])]
        body = [row for row in gaps
                if set(row['missing']) - {SLOT_TITLE, SLOT_DESCRIPTION}]
        if body:
            self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
                _("Still short after %s round(s):") % (rounds or 1),
                _("%(gaps)s. The page is built from the copy as it stands - "
                  "add the wording yourself, or rephrase the keyword into "
                  "something a heading can carry.",
                  gaps=self._placement_brief(body).replace('\n', '; '))))
        if head:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "Not in the title tag or meta description: %(list)s. Those two "
                "are yours - edit the Page Title and Page Description on this "
                "request. They are not rewritten automatically, because a "
                "title bent around a keyword is worse than one that reads.",
                list=', '.join('"%s"' % row['keyword'] for row in head)))

    def _step_rewrite(self, provider, copy):
        """Edit mode: put the new copy into the page that is already there.

        The markup is never sent and never returned. The page's text is pulled
        out of the tree, the model supplies replacement wording for the pieces
        the new copy actually covers, and those strings are written back into
        the same nodes.

        That is a promise rather than an instruction: a model that never sees a
        tag cannot drop an image, add a button or a form, or collapse a card
        grid into a paragraph. Asking for markup back always could, however
        firmly the prompt says otherwise - which is what kept happening.

        Returns '' only when the page has no readable body.
        """
        page = self.reference_page_id
        # The base arch, not the combined one: this markup is written straight
        # back, and folding the inherited views in would bake them into the
        # base view and then apply them a second time.
        body = page_writer.page_body(page, combined=False)
        if not body or not body.strip():
            self.message_post(body=Markup('<p>%s</p>') % _(
                "The page has no body that can be read, so it is rebuilt from "
                "the copy instead of edited in place."))
            return ''

        try:
            root = etree.fromstring(
                '<root>%s</root>' % body,
                parser=etree.XMLParser(resolve_entities=False, recover=True))
        except etree.XMLSyntaxError:
            root = None
        if root is None:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "The page markup could not be parsed, so it is rebuilt from "
                "the copy instead of edited in place."))
            return ''

        slots = page_writer.text_slots(root)
        if not slots:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "The page has no text to replace, so it is left as it is."))
            return body

        limit = self._get_max_context_chars()
        brief = copy[:max(limit // 2, 4000)]
        replacements = {}
        for batch in _batch_slots(slots, REWRITE_BATCH_CHARS):
            listing = '\n'.join(
                '%s. [%s] %s' % (index, slots[index][0].tag, text)
                for index, text in batch)
            try:
                answer = provider.chat(self._get_system_prompt(), [{
                    'role': 'user',
                    'content': REWRITE_PROMPT % {'copy': brief, 'slots': listing},
                }])
            except AIProviderError as error:
                # One failed batch costs its own wording, not the whole page.
                _logger.warning("Rewrite batch failed: %s", error)
                continue
            payload = _extract_json(answer) or {}
            for key, value in payload.items():
                try:
                    replacements[int(key)] = value
                except (TypeError, ValueError):
                    continue

        changed = page_writer.apply_text_slots(slots, replacements)
        arch = ''.join(
            etree.tostring(child, encoding='unicode', method='xml')
            for child in root if isinstance(child.tag, str))

        self.message_post(body=Markup('<p>%s</p>') % _(
            "Rewrote the page in place: %(changed)s of %(total)s pieces of text "
            "took the new copy, the rest were left as they were. No markup was "
            "sent to the AI and none came back, so every block, image, button "
            "and form is exactly where it was.",
            changed=changed, total=len(slots)))
        self._report_structure_change(body, arch)
        self._append_history('user', _("Rewrite this page with new copy."))
        self._append_history('assistant', arch)
        return arch

    # ------------------------------------------------------------------
    # Design template: fill it, never redesign it
    # ------------------------------------------------------------------
    def _template_body(self):
        """The design template's markup, to be used as the new page's skeleton.

        Combined, not base: what the template renders today is the design that
        was asked for. Baking the inheriting views in is right here, unlike in
        an in-place edit - they are keyed to the template's view and will never
        apply to the page this becomes.
        """
        page = self.template_page_id
        if not page:
            return ''
        return page_writer.page_body(page, combined=True)

    @staticmethod
    def _parse_body(body):
        """A body's markup as a tree of top level blocks, or None."""
        if not body or not body.strip():
            return None
        try:
            return etree.fromstring(
                '<root>%s</root>' % body,
                parser=etree.XMLParser(resolve_entities=False, recover=True))
        except etree.XMLSyntaxError:
            return None

    @staticmethod
    def _serialise_body(root):
        return ''.join(
            etree.tostring(child, encoding='unicode', method='xml')
            for child in root if isinstance(child.tag, str))

    @staticmethod
    def _block_label(element):
        """What a top level block is called, for a listing the AI reads."""
        return (element.get('data-name')
                or element.get('data-snippet')
                or (element.get('class') or '').split(' ')[0]
                or element.tag)

    def _section_listing(self, root):
        blocks = [child for child in root if isinstance(child.tag, str)]
        return '\n'.join(
            '%s. %s' % (number, self._block_label(block))
            for number, block in enumerate(blocks, start=1))

    def _step_extra_snippets(self, provider, root):
        """Let the AI add whole theme blocks to the skeleton, if asked to.

        The AI picks from the theme's catalogue by name and says where it goes.
        It never sends markup and none is accepted from it: the block inserted
        is the theme's own template, unchanged, exactly what the website builder
        would drop. So "add an FAQ" can add an FAQ, and nothing else can happen -
        no section is redesigned, reordered or lost on the way.
        """
        if not (self.allow_extra_snippets and self.prompt):
            return 0
        entries = theme_snippets.catalogue(self.env, website=self.website_id)
        if not entries:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "No snippet of the Captivea theme could be read, so nothing was "
                "added to the template. Install or upgrade the theme."))
            return 0

        answer = provider.chat(FALLBACK_SYSTEM_PROMPT, [{
            'role': 'user',
            'content': EXTRA_SNIPPETS_PROMPT % {
                'sections': self._section_listing(root),
                'instructions': self.prompt,
                'catalogue': theme_snippets.render_listing(entries),
            },
        }])
        payload = _extract_json(answer) or {}
        wanted = payload.get('add') or []
        if not isinstance(wanted, list):
            return 0

        known = theme_snippets.by_key(entries)
        blocks = [child for child in root if isinstance(child.tag, str)]
        added, unknown = [], []
        # Inserted from the bottom up, so the numbers the AI answered with keep
        # pointing at the same section while the tree grows underneath them.
        for item in sorted(
                (item for item in wanted if isinstance(item, dict)),
                key=lambda item: -(int(item.get('after') or 0)
                                   if str(item.get('after') or 0).lstrip('-').isdigit()
                                   else 0)):
            entry = known.get((item.get('snippet') or '').strip())
            if not entry:
                unknown.append(str(item.get('snippet')))
                continue
            element = self._parse_body(entry['markup'])
            element = element[0] if element is not None and len(element) else None
            if element is None:
                continue
            after = item.get('after') or 0
            after = int(after) if str(after).lstrip('-').isdigit() else 0
            after = max(0, min(after, len(blocks)))
            if after == 0:
                root.insert(0, element)
            else:
                blocks[after - 1].addnext(element)
            added.append((entry['name'], item.get('why') or ''))

        if added:
            self.message_post(body=Markup('<p><b>%s</b><br/>%s</p>') % (
                _("Sections added from the theme catalogue, because the "
                  "instructions asked for them:"),
                Markup('<br/>').join(
                    Markup('%s — %s') % (name, why) for name, why in added)))
        if unknown:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "The AI asked for %s, which is not in the theme catalogue, so it "
                "was ignored.", ', '.join(unknown)))
        return len(added)

    def _fill_attribute_placeholders(self, root):
        """Fill the placeholders that live in attributes, not in text.

        The theme writes one: the hidden subject of its contact form, ``Form -
        {Short title of the page}``. ``text_slots`` cannot reach it - an
        attribute is not a text node - and left as it is, every enquiry from the
        page arrives with the placeholder in its subject line. The page's own
        title is the answer, so no AI call is needed for it.

        Returns the number of attribute placeholders still unfilled, ignoring
        values that are JSON rather than a brief (``data-custom-template-data``
        holds ``{"key": true}``, which is not a slot).
        """
        title = (self.page_title or self.name or '').strip()
        left = 0
        for node in root.iter():
            if not isinstance(node.tag, str):
                continue
            for name, value in list(node.attrib.items()):
                if not theme_snippets.has_placeholder(value):
                    continue
                if value.lstrip().startswith('{"'):
                    continue
                if title:
                    value = value.replace(
                        theme_snippets.PAGE_TITLE_PLACEHOLDER, title)
                    node.set(name, value)
                if theme_snippets.has_placeholder(value):
                    left += 1
        return left

    def _fill_slots(self, provider, slots, targets, copy, prompt):
        """Ask the AI for the wording of the given slots, and write it back.

        Only strings travel, in both directions. The tree the slots belong to is
        never serialised into a prompt and never rebuilt from an answer, which is
        what makes "the design is untouched" a fact rather than an instruction.
        """
        limit = self._get_max_context_chars()
        brief = (copy or '')[:max(limit // 2, 4000)]
        pairs = [(index, ' '.join(slots[index][2].split())) for index in targets]
        pairs = [(index, text) for index, text in pairs if text]
        replacements = {}
        batch, size = [], 0
        batches = []
        for index, text in pairs:
            if batch and size + len(text) > REWRITE_BATCH_CHARS:
                batches.append(batch)
                batch, size = [], 0
            batch.append((index, text))
            size += len(text)
        if batch:
            batches.append(batch)

        for batch in batches:
            listing = '\n'.join(
                '%s. [%s] %s' % (index, slots[index][0].tag, text)
                for index, text in batch)
            try:
                answer = provider.chat(self._get_system_prompt(), [{
                    'role': 'user',
                    'content': prompt % {'copy': brief, 'slots': listing},
                }])
            except AIProviderError as error:
                # One failed batch costs its own wording, not the whole page.
                _logger.warning("Fill batch failed: %s", error)
                continue
            payload = _extract_json(answer) or {}
            for key, value in payload.items():
                try:
                    replacements[int(key)] = value
                except (TypeError, ValueError):
                    continue
        return page_writer.apply_text_slots(slots, replacements)

    def _step_template_fill(self, provider, copy):
        """Build the page by filling the design template, never by drawing it.

        The template's markup is the page. Every section it has survives, in its
        order, with its classes, its images and its forms; the AI's only job is
        the words that go in the slots the template left for them - the theme
        writes those as ``{...}`` placeholders, so which text is the design's own
        and which is waiting to be written is not a judgement call.

        Returns '' when the template cannot be read, so the caller can fall back
        to building the page from a palette.
        """
        body = self._template_body()
        root = self._parse_body(body)
        if root is None or not len(root):
            self.message_post(body=Markup('<p>%s</p>') % _(
                "The design template \"%s\" has no markup that can be read, so "
                "the page is built from the snippet palette instead.",
                self.template_page_id.name))
            return ''

        added = self._step_extra_snippets(provider, root)
        skeleton = self._serialise_body(root)

        slots = page_writer.text_slots(root)
        targets = [index for index, (_node, _which, text) in enumerate(slots)
                   if theme_snippets.has_placeholder(text)]
        prompt = FILL_PROMPT
        if not targets:
            # A page with no `{...}` placeholders is not one of the theme's
            # templates - someone picked an ordinary page. Then every piece of
            # text is a candidate, and the rewrite rules apply instead: change
            # what the new copy covers and leave the rest alone. Still text
            # only, so the design is as safe as before.
            targets = list(range(len(slots)))
            prompt = REWRITE_PROMPT
            self.message_post(body=Markup('<p>%s</p>') % _(
                "This template carries no {placeholder} slots, so its own "
                "wording is what the AI works from: the text the new copy covers "
                "is replaced and the rest is left as it is."))
        if not slots:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "The design template has no text to fill, so it is copied as it "
                "is."))
            return skeleton

        changed = self._fill_slots(provider, slots, targets, copy, prompt)
        left_attrs = self._fill_attribute_placeholders(root)
        arch = self._serialise_body(root)

        left = sum(
            1 for _node, _which, text in page_writer.text_slots(root)
            if theme_snippets.has_placeholder(text)) + left_attrs
        message = _(
            "Built to the \"%(template)s\" template: %(changed)s of "
            "%(total)s text slots filled with the new copy. No markup was sent "
            "to the AI and none came back, so every section of the template is "
            "there, in its order, with its own classes, images and forms.",
            template=self.template_page_id.name, changed=changed,
            total=len(targets))
        if added:
            message += ' ' + _("%s section(s) were added from the theme "
                              "catalogue on top of it.", added)
        if left:
            message += ' ' + _(
                "%s placeholder(s) are still unfilled - the AI answered nothing "
                "for them. Fill them in the preview, or generate again.", left)
        self.message_post(body=Markup('<p>%s</p>') % message)
        self._report_structure_change(skeleton, arch)
        self._append_history(
            'user', _("Fill the \"%s\" design template with this page's copy.",
                      self.template_page_id.name))
        self._append_history('assistant', arch)
        return arch

    def _refine_template_fill(self, provider):
        """A refinement turn on a page built to a template.

        The instructions may change the words. They may not redesign the page:
        a template was chosen, so the design is settled. Same slot route as the
        first pass, with the instructions as the brief.
        """
        root = self._parse_body(self.draft_arch or '')
        if root is None or not len(root):
            return ''
        before = self._serialise_body(root)
        slots = page_writer.text_slots(root)
        if not slots:
            return before
        targets = list(range(len(slots)))
        brief = _("The page's copy:\n%(copy)s\n\nWhat to change now:\n%(prompt)s",
                  copy=self.article_body or '', prompt=self.prompt or '')
        changed = self._fill_slots(provider, slots, targets, brief, REWRITE_PROMPT)
        arch = self._serialise_body(root)
        self.message_post(body=Markup('<p>%s</p>') % _(
            "Refined in place: %(changed)s of %(total)s pieces of text changed. "
            "The design template's markup is untouched - to change the design, "
            "clear the Design Template field and generate again.",
            changed=changed, total=len(slots)))
        self._report_structure_change(before, arch)
        return arch

    def _report_structure_change(self, before, after):
        """Say in the chatter whether the edit kept the page's shape.

        The instruction is to change words only, and a model can quietly ignore
        it. Comparing the two bodies block by block is cheap and turns a silent
        redesign into a line the user can read before pressing Apply.
        """
        old = page_writer.deep_signature(before)
        new = page_writer.deep_signature(after)
        if old == new:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "Markup verified identical: all %s elements, their nesting and "
                "their classes are unchanged. Only the words are different.",
                len(old)))
            return
        from collections import Counter
        before, after = Counter(tag for tag, _cls in old), Counter(
            tag for tag, _cls in new)
        lost = sorted(
            ('%s %s -> %s' % (tag, before[tag], after.get(tag, 0))
             for tag in before if before[tag] != after.get(tag, 0)))
        self.message_post(body=Markup('<p><b>%s</b><br/>%s</p>') % (
            _("The edit changed the page's markup, not only its words."),
            _("%(before)s elements before, %(after)s after: %(lost)s. Check "
              "the preview before applying.",
              before=len(old), after=len(new),
              lost=', '.join(lost) or _("classes changed"))))

    def _is_free_hand_design(self):
        """True when nobody has said how this page should look.

        Two ways to say it, and either one turns the draw off: a **design
        template**, whose markup is the design outright, or **instructions** on
        the request, which are handed to the layout step as the design brief.

        A user who wrote instructions about the words rather than the design
        also turns it off, which is the right way round to be wrong: a drawn
        shape that quietly overrode what someone typed would be worse than one
        that did not fire.
        """
        self.ensure_one()
        return not self.template_page_id and not (self.prompt or '').strip()

    def _layout_recipe(self):
        """One shape, drawn from the vocabularies above.

        Unseeded on purpose: pressing Generate again is how a user asks for a
        different design, so two runs of the same request should not agree.
        """
        draw = random.Random()
        return [
            draw.choice(LAYOUT_OPENINGS),
            draw.choice(LAYOUT_RHYTHMS),
            draw.choice(LAYOUT_EMPHASIS),
            draw.choice(LAYOUT_CLOSINGS),
            draw.choice(LAYOUT_COLOURS),
            draw.choice(LAYOUT_SPACING),
        ]

    def _step_layout(self, provider, copy):
        """Step five: turn the copy into Odoo snippets the editor can edit."""
        limit = self._get_max_context_chars()
        # The reference page is the palette when there is one. With no
        # reference the model has no snippet vocabulary at all, and writes bare
        # headings and paragraphs: correct copy in a page the editor cannot
        # edit block by block. The standard snippets stand in for it.
        website = self.website_id or self.env['website'].get_current_website()
        palette = self._get_page_context()
        if not palette:
            # The Captivea theme's own snippets are the site's design system, so
            # they come before anything mined off the pages: a block from here is
            # the same block the website builder drops, placeholders and all.
            entries = theme_snippets.catalogue(self.env, website=website)
            palette = theme_snippets.render_palette(entries, budget=limit)
            if palette:
                self.message_post(body=Markup('<p>%s</p>') % _(
                    "No design template, so the page is built from the Captivea "
                    "theme's own %s snippets.", len(entries)))
        if not palette:
            # No reference page named, so the site's own pages stand in for
            # one: real blocks beat a class list, because they show how this
            # site actually assembles a section out of its classes. Mined once
            # and reused, since reading them means combining every page's views.
            blocks = theme_style.house_blocks(self.env, website)
            palette = theme_style.render_house_palette(blocks)
            if palette:
                self.message_post(body=Markup('<p>%s</p>') % _(
                    "Palette taken from %(count)s real sections of this site: "
                    "%(pages)s.", count=len(blocks),
                    pages=', '.join(sorted({block['url'] for block in blocks}))))
        if not palette:
            palette = snippet_library.fallback_palette()
            self.message_post(body=Markup('<p>%s</p>') % _(
                "No reference page and no page of this site uses its own "
                "classes, so the standard Odoo snippets are used."))
        # The site's own CSS and JS: without them the best the model can do is
        # stock Odoo, however good the copy is.
        message = (LAYOUT_INTRO % copy[:limit] + NO_IMAGES_RULE + palette
                   + self._get_style_guide(website))
        asked = (self.prompt or '').strip()
        if self._is_free_hand_design():
            recipe = self._layout_recipe()
            message += '%s%s\n' % (
                LAYOUT_VARIATION_INTRO,
                '\n'.join('- %s' % line for line in recipe))
            self.message_post(body=Markup('<p><b>%s</b></p><p>%s</p>') % (
                _("No design was specified, so this shape was drawn for the "
                  "page. Generate again to draw another."),
                Markup('<br/>').join(recipe)))
        elif asked:
            # The user's own words about the design. They used to reach the copy
            # step and stop there, so on a first run the only way to say
            # anything about the design was to pick a template.
            message += _(
                "=== WHAT THE USER ASKED FOR ===\n"
                "This is what was asked for on the request. Where it says "
                "anything about how the page should look, it decides - over any "
                "arrangement you would otherwise have reached for. Where it "
                "only talks about the words, they are already written above and "
                "there is nothing here for you to do about it.\n%s\n"
            ) % asked
        # Which prompt built the page is worth having on the record: two drafts
        # from the same copy can differ entirely because one template carries
        # its own instructions and another does not.
        if self.template_page_id and self.template_page_id.sudo().cap_builder_prompt:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "Built to the build instructions on the \"%s\" template, added "
                "to the AI model's Page Generation prompt.",
                self.template_page_id.name))
        answer = provider.chat(
            self._get_system_prompt(), [{'role': 'user', 'content': message}])
        arch = page_writer.extract_html(answer)
        if not arch:
            self.message_post(body=Markup('<p><b>%s</b></p><p>%s</p>') % (
                _("The AI did not return any HTML:"), answer or ''))
            return ''
        # Asking is not enough: a model handed a palette full of pictures
        # writes pictures. The markup is cleaned instead.
        arch, removed = page_writer.strip_images(arch)
        if removed:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "%s image(s) the AI added were removed - generated pages are "
                "text only - along with the wrappers left empty.", removed))
        # The theme writes its briefs into its own snippets as {...}. A block
        # copied from the palette with one left in it publishes the brief, so it
        # is worth a line before Apply rather than a bug report afterwards.
        left = theme_snippets.count_placeholders(arch)
        if left:
            self.message_post(body=Markup('<p>%s</p>') % _(
                "%s snippet placeholder(s) in braces were left in the draft. "
                "Replace them in the preview, or generate again.", left))
        # Seed the conversation so the next Generate is a refinement turn on
        # this page rather than a second run of the whole pipeline.
        self._append_history('user', message)
        self._append_history('assistant', arch)
        return arch

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_generate(self):
        """Run the pipeline, or refine the page that came out of it.

        Once a draft exists the conversation continues on it, so a second
        Generate applies the new instructions to that page instead of
        researching and rewriting it from nothing.
        """
        self.ensure_one()
        self._check_builder_group()
        if self.mode == 'edit' and not self.reference_page_id:
            raise UserError(_("Select the page you want the AI to edit."))
        if self._get_history():
            return self._refine()
        return self._run_pipeline()

    def _run_pipeline(self):
        self.ensure_one()
        if not self.main_keyword:
            raise UserError(_("Enter the main keyword before generating."))
        if self.mode == 'create' and not self.page_title:
            raise UserError(_("Enter the page title before generating."))
        # Checked before any AI call: asking for Surfer and finding out it
        # cannot run only at step three would mean two calls already paid for
        # and a page written the way the user did not ask for.
        if self.use_surfer and not research_client.available_sources(
                self.env).get('surfer'):
            raise UserError(_(
                "This request asks for Surfer SEO, but no Surfer API key is "
                "configured. Add one in Settings > AI Page Builder, or untick "
                "Use Surfer SEO to let the AI work out the coverage itself."))

        # Posted before anything runs, because the field it comes from is
        # cleared once a draft exists. Without this the instructions that shaped
        # a page are gone the moment it is built, and a run that came out wrong
        # cannot be told from one that was asked for something different.
        # `_refine` does the same for every later turn.
        if self.prompt:
            self.message_post(body=Markup('<p><b>%s</b></p><p>%s</p>') % (
                _("Instructions"), self.prompt))

        try:
            provider = get_provider(self.ai_model_id)
            self._step_description(provider)
            keywords = self._step_sub_keywords(provider)
            terms, brief = self._step_surfer_terms(keywords)
            copy = self._step_copy(provider, keywords, terms)
            copy = self._step_score(provider, keywords, terms, brief, copy)
            # After scoring, not before: a Surfer rescore rewrites the copy and
            # can drop a keyword the first draft had, so checking earlier would
            # be checking a version that never reaches the page.
            copy = self._step_keyword_check(provider, keywords, copy)
            # Three routes to a page, and which one runs is decided here.
            #
            # A design template is the strongest statement the user can make
            # about the design, so it wins in both modes: the template's markup
            # becomes the page and the AI only fills its text slots. It cannot
            # drop a section, reorder one or invent one, because it is never
            # handed any markup to change.
            #
            # In edit mode with no template, editing is a rewrite in place - the
            # words change and the structure does not. That is the safe default
            # for "fix the wording on this page", where rebuilding would
            # silently redesign a page nobody asked to redesign.
            #
            # With neither, the page has to be laid out from a palette, and only
            # then does the AI write markup at all.
            arch = ''
            if self.template_page_id:
                arch = self._step_template_fill(provider, copy)
            elif self.mode == 'edit' and self.reference_page_id:
                arch = self._step_rewrite(provider, copy)
            if not arch:
                arch = self._step_layout(provider, copy)
        except AIProviderError as error:
            self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
                _("AI error:"), str(error)))
            return False
        if not arch:
            return False

        self.draft_arch = arch
        self.state = 'generated'
        self.prompt = False
        self.message_post(body=Markup('<p>%s</p>') % _(
            "Draft built (%s characters). Review it, then press Apply.",
            len(arch)))
        self._report_page_keywords(keywords, arch)
        return True

    def _report_page_keywords(self, keywords, arch):
        """Say whether the keywords survived into the finished page.

        Reported, never repaired. The copy was already checked and fixed before
        the page was built, so a keyword missing here was lost by the route that
        built it - a template slot too short for the phrase, or a rewrite that
        left that text alone. Putting it back would mean editing markup the user
        chose the design of, which is not a trade this step is allowed to make.
        """
        lost = missing_keywords(page_writer.text_of(arch), keywords)
        if not lost:
            return
        self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
            _("In the copy but not in the finished page:"),
            _("%(lost)s. The design decided how much of the copy has room - "
              "edit the page, or generate again with a template whose sections "
              "fit the wording.",
              lost=', '.join('"%s"' % word for word in lost))))

    def _refine(self):
        """A further turn on the page already drafted."""
        self.ensure_one()
        if not self.prompt:
            raise UserError(_(
                "Write what you want changed, then press Generate again."))

        prompt = self.prompt
        self.message_post(body=Markup('<p><b>%s</b></p><p>%s</p>') % (
            _("Instructions"), prompt))

        try:
            provider = get_provider(self.ai_model_id)
            # A page built to a template stays built to it on every later turn.
            # Sending the draft back as markup to be rewritten is exactly how a
            # settled design gets quietly redrawn, so refinement takes the same
            # text-only route as the first pass.
            if self.template_page_id:
                arch = (self._refine_template_fill(provider)
                        if self.draft_arch else '')
                if not arch:
                    # The draft could not be read back. Filling the template
                    # again is still the template's design; asking the model for
                    # markup would not be.
                    arch = self._step_template_fill(
                        provider, self.article_body or self.prompt or '')
                if arch:
                    self._append_history('user', prompt)
                    self._append_history('assistant', arch)
                    self.draft_arch = arch
                    self.state = 'generated'
                    self.prompt = False
                    return True
            answer = provider.chat(
                self._get_system_prompt(), self._build_messages())
        except AIProviderError as error:
            self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
                _("AI error:"), str(error)))
            return False

        arch = page_writer.extract_html(answer)
        if not arch:
            self.message_post(body=Markup('<p><b>%s</b></p><p>%s</p>') % (
                _("The AI did not return any HTML:"), answer or ''))
            return False

        self._append_history('user', prompt)
        self._append_history('assistant', arch)
        self.draft_arch = arch
        self.state = 'generated'
        self.prompt = False
        self.message_post(body=Markup('<p>%s</p>') % _(
            "Draft updated (%s characters). Review it, then press Apply.",
            len(arch)))
        return True

    def action_suggest_description(self):
        """Rewrite the description from the current draft."""
        self.ensure_one()
        self._check_builder_group()
        if not self.draft_arch:
            raise UserError(_("Generate a page first, then I can describe it."))
        try:
            provider = get_provider(self.ai_model_id)
            description = self._write_description(provider, self.draft_arch)
        except AIProviderError as error:
            raise UserError(str(error))
        if not description:
            raise UserError(_("The AI returned nothing usable."))
        self.description = description
        self.message_post(body=Markup('<p><b>%s</b> %s</p>') % (
            _("Suggested description:"), description))
        return True

    def action_apply(self):
        self.ensure_one()
        self._check_builder_group()
        if not self.draft_arch:
            raise UserError(_("There is nothing to apply yet."))

        arch = page_writer.sanitize_arch(self.env, self.draft_arch)
        if not arch:
            raise UserError(_("The draft is empty once cleaned up, nothing to apply."))

        if self.mode == 'edit':
            if not self.reference_page_id:
                raise UserError(_("Select the page you want to edit."))
            # Keep the previous content in the chatter so a human can revert.
            previous = page_writer.page_body(self.reference_page_id)
            self.message_post(
                body=Markup('<p>%s</p>') % _("Content replaced. Previous version attached."),
                attachments=[('previous_page_%s.html' % self.reference_page_id.id,
                              previous or '')],
            )
            page = page_writer.update_page(self, arch)
        else:
            page = page_writer.create_page(self, arch)
            self.message_post(body=Markup('<p>%s</p>') % _(
                "Page created at %s. It is not published yet.", page.url))

        # Carry the brief onto the page itself: this is the text search engines
        # show under the title, and nothing else on the page supplies it.
        if self.description:
            page.website_meta_description = self.description.strip()
        # And the keywords, into the field Odoo's own Optimize SEO dialog reads
        # and writes. The page was written to these four; without this the
        # dialog opens empty and offers to guess them back out of the markup,
        # which is a worse answer than the one already on the request.
        keywords = self._all_keywords()
        if keywords:
            page.website_meta_keywords = ', '.join(keywords)

        self.page_id = page
        self.page_url = page.url
        self.state = 'applied'
        return True

    def action_preview_draft(self):
        """Open the draft on the frontend, with the website's theme applied."""
        self.ensure_one()
        if not self.draft_arch:
            raise UserError(_("Generate something before previewing it."))
        website = self.website_id or self.env['website'].get_current_website()
        return {
            'type': 'ir.actions.act_url',
            'url': '%s/cap_website_builder/preview/%s' % (
                website.domain.rstrip('/') if website.domain else '', self.id),
            'target': 'new',
        }

    def action_reset_to_draft(self):
        self.ensure_one()
        self.state = 'draft'
        return True

    def action_open_page(self):
        self.ensure_one()
        if not self.page_id:
            raise UserError(_("No page has been created or edited yet."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.page_id.url,
            'target': 'new',
        }

    # ------------------------------------------------------------------
    # Onchanges
    # ------------------------------------------------------------------
    @api.onchange('mode')
    def _onchange_mode(self):
        if self.mode == 'create':
            self.page_id = False
        elif self.reference_page_id:
            self.page_url = self.reference_page_id.url
            self.page_title = self.reference_page_id.name

    # No onchange follows the design template's website, unlike the content
    # reference below. The theme's templates are global records with no website
    # of their own, so there is nothing to follow: which site the page is
    # published to stays the user's choice, or the content reference's.

    @api.onchange('reference_page_id')
    def _onchange_reference_page_id(self):
        if not self.reference_page_id:
            return
        # Follow the reference page's website so the style we copy and the site
        # we publish to are the same one.
        if self.reference_page_id.website_id:
            self.website_id = self.reference_page_id.website_id
        if self.mode == 'edit':
            self.page_url = self.reference_page_id.url
            self.page_title = self.reference_page_id.name
