"""Turn a raw LLM answer into safe page content, then write it on the site."""
import logging
import re

from lxml import etree, html

from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

DEFAULT_FORBIDDEN_TAGS = 'script,iframe,object,embed,base,meta,link'

# Tags that carry no structure worth showing in an outline.
INLINE_TAGS = frozenset((
    'a', 'b', 'br', 'em', 'font', 'i', 'label', 'small', 'span', 'strong',
    'sub', 'sup', 'u',
))
# Attributes that define how a block looks and behaves in the website builder.
OUTLINE_ATTRS = ('id', 'class', 'data-snippet', 'data-name', 'data-oe-shape-data')
# A section reaches its headings and buttons around six levels down
# (section > div.container > div.row > div.col > div > h2), so a shallow
# outline shows only the section shells - which is why colours carry over but
# the inner layout does not.
OUTLINE_MAX_DEPTH = 9
IMAGE_SRC_LIMIT = 40

# url(...) inside a style attribute, quoted or not
BACKGROUND_URL_RE = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""")

# ```html ... ``` or ``` ... ``` around the answer
CODE_FENCE_RE = re.compile(r'```[a-zA-Z]*\s*(?P<body>.*?)```', re.DOTALL)


def extract_html(answer):
    """Pull the HTML block out of a model answer.

    Models like to wrap their output in markdown fences and to add a sentence
    before or after it. Returns an empty string when nothing HTML-like is found,
    so the caller can show the raw answer instead of writing garbage.
    """
    if not answer:
        return ''
    fenced = CODE_FENCE_RE.search(answer)
    if fenced:
        answer = fenced.group('body')
    answer = answer.strip()
    start = answer.find('<')
    end = answer.rfind('>')
    if start == -1 or end == -1 or end < start:
        return ''
    return answer[start:end + 1].strip()


def _forbidden_tags(env):
    param = env['ir.config_parameter'].sudo().get_param(
        'cap_website_builder.forbidden_tags', DEFAULT_FORBIDDEN_TAGS)
    return {tag.strip().lower() for tag in param.split(',') if tag.strip()}


def _clean_element(element, forbidden):
    for node in list(element.iter()):
        if not isinstance(node.tag, str):
            continue
        if node.tag.lower() in forbidden:
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
            continue
        for attribute, value in list(node.attrib.items()):
            lowered = attribute.lower()
            if lowered.startswith('on'):
                del node.attrib[attribute]
            elif lowered in ('href', 'src', 'action') and \
                    (value or '').strip().lower().startswith('javascript:'):
                del node.attrib[attribute]


def sanitize_arch(env, content):
    """Strip anything executable from the generated markup.

    QWeb directives (``t-*``) are left untouched, only scripting is removed.
    """
    if not content or not content.strip():
        return ''
    forbidden = _forbidden_tags(env)
    try:
        fragments = html.fragments_fromstring(content)
    except (etree.ParserError, etree.XMLSyntaxError) as error:
        raise UserError(_("The generated content is not valid HTML: %s", error))

    parts = []
    for fragment in fragments:
        if isinstance(fragment, str):
            text = fragment.strip()
            if text:
                parts.append(text)
            continue
        if fragment.tag.lower() in forbidden:
            continue
        _clean_element(fragment, forbidden)
        parts.append(etree.tostring(fragment, encoding='unicode', method='xml'))
    return check_xml('\n'.join(parts))


def check_xml(arch):
    """Return ``arch`` only if it parses as XML, which a view arch must.

    An Odoo view is XML, not HTML: <img> and <br> left open, or a bare & in a
    URL, make the view fail to load. Everything here has already been through
    lxml's HTML parser and been re-serialised as XML, so this is the last gate
    - if it still fails, the markup is wrong in a way we should not write.
    """
    if not arch or not arch.strip():
        return ''
    try:
        # Wrapped: a fragment list has no single root, which XML requires.
        etree.fromstring(
            '<root>%s</root>' % arch,
            parser=etree.XMLParser(resolve_entities=False))
    except etree.XMLSyntaxError as error:
        raise UserError(_(
            "The generated markup is not valid XML, so Odoo would refuse the "
            "view:\n\n%s\n\nRegenerate the page, or fix the draft by hand.",
            error))
    return arch


# Elements whose text is markup or machine-read, never page copy.
NON_TEXT_TAGS = frozenset(('script', 'style', 't'))


def text_slots(root):
    """Every editable piece of text in a tree, in document order.

    Returns ``[(node, which, text)]`` where *which* is ``'text'`` or ``'tail'``.
    Editing a page by rewriting these and putting them back is the only way to
    promise the markup is untouched: a model that never sees a tag cannot drop
    an image, add a button, or collapse a card grid. It can only supply words.
    """
    slots = []
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        if node.tag.lower() in NON_TEXT_TAGS:
            continue
        if node.text and node.text.strip():
            slots.append((node, 'text', node.text))
        # A tail belongs to the node it follows, and is page copy just as often
        # as a node's own text: "<strong>Odoo</strong> handles this" is a tail.
        if node.tail and node.tail.strip():
            parent = node.getparent()
            if parent is not None and parent.tag not in NON_TEXT_TAGS:
                slots.append((node, 'tail', node.tail))
    return slots


def apply_text_slots(slots, replacements):
    """Write new strings into the slots, keeping their surrounding whitespace.

    ``replacements`` maps slot index to new text. Anything missing, empty, or
    carrying markup is skipped and the original text stays: the worst outcome
    of a bad answer is a page that did not change.
    """
    changed = 0
    for index, (node, which, original) in enumerate(slots):
        new = replacements.get(index)
        if not isinstance(new, str):
            continue
        new = new.strip()
        # A '<' here would be text, not markup - lxml escapes it - but it means
        # the model tried to return an element, so the answer is not trusted.
        if not new or '<' in new or new == original.strip():
            continue
        # Indentation lives in these strings; replacing them wholesale would
        # reflow the source even though the rendering is identical.
        leading = original[:len(original) - len(original.lstrip())]
        trailing = original[len(original.rstrip()):]
        setattr(node, which, '%s%s%s' % (leading, new, trailing))
        changed += 1
    return changed


def top_level_blocks(arch):
    """Split a body into its top level blocks, as markup strings.

    Editing a page one block at a time is what makes the page's size stop
    mattering: a 90 KB page is a handful of ordinary calls rather than one that
    does not fit.
    """
    if not arch or not arch.strip():
        return []
    try:
        root = etree.fromstring(
            '<root>%s</root>' % arch,
            parser=etree.XMLParser(resolve_entities=False, recover=True))
    except etree.XMLSyntaxError:
        return []
    if root is None:
        return []
    return [
        etree.tostring(element, encoding='unicode', method='xml')
        for element in root if isinstance(element.tag, str)
    ]


IMAGE_TAGS = frozenset(('img', 'picture', 'source', 'figure', 'svg', 'video'))
# Wrappers worth pruning once their image is gone. A <section> is never pruned:
# it is the block itself, and an empty column is tidier than a missing section.
PRUNABLE_TAGS = frozenset(('div', 'figure', 'span', 'p', 'a'))


def strip_images(arch):
    """Remove every image from a body, and the wrappers left holding nothing.

    Returns ``(arch, removed)``. Dropping the ``<img>`` alone leaves an empty
    column beside a half-width text column, so a wrapper that ends up with no
    text and no children goes too - up to, but never including, the section.
    """
    if not arch or not arch.strip():
        return arch, 0
    try:
        root = etree.fromstring(
            '<root>%s</root>' % arch,
            parser=etree.XMLParser(resolve_entities=False, recover=True))
    except etree.XMLSyntaxError:
        return arch, 0
    if root is None:
        return arch, 0

    removed = 0
    for node in list(root.iter()):
        if not isinstance(node.tag, str):
            continue
        if node.tag.lower() in IMAGE_TAGS:
            parent = node.getparent()
            if parent is None:
                continue
            # Keep any text that trailed the image, it is page copy.
            if node.tail and node.tail.strip():
                previous = node.getprevious()
                if previous is not None:
                    previous.tail = (previous.tail or '') + node.tail
                else:
                    parent.text = (parent.text or '') + node.tail
            parent.remove(node)
            removed += 1

    # A background image is still an image.
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        style = node.get('style')
        if style and BACKGROUND_URL_RE.search(style):
            cleaned = BACKGROUND_URL_RE.sub('none', style)
            node.set('style', cleaned)
            removed += 1

    changed = True
    while changed:
        changed = False
        for node in list(root.iter()):
            if not isinstance(node.tag, str) or node.tag.lower() not in PRUNABLE_TAGS:
                continue
            parent = node.getparent()
            if parent is None or parent is root:
                continue
            if len(node) or (node.text and node.text.strip()):
                continue
            if node.tail and node.tail.strip():
                continue
            parent.remove(node)
            changed = True

    body = ''.join(
        etree.tostring(child, encoding='unicode', method='xml')
        for child in root if isinstance(child.tag, str))
    return body, removed


def deep_signature(arch):
    """The shape of a body at full depth: every element, tag and classes.

    The top level alone is not enough. A rewrite can leave all 12 sections in
    place and still delete half the images and a third of the headings inside
    them, which is exactly what a shallow check waves through.
    """
    if not arch or not arch.strip():
        return []
    try:
        root = etree.fromstring(
            '<root>%s</root>' % arch,
            parser=etree.XMLParser(resolve_entities=False, recover=True))
    except etree.XMLSyntaxError:
        return []
    if root is None:
        return []
    return [
        (node.tag.lower(), tuple(sorted((node.get('class') or '').split())))
        for node in root.iter() if isinstance(node.tag, str)
    ]


def structure_signature(arch):
    """The shape of a body: one entry per top level block.

    Used to prove an edit changed the words and nothing else. Two archs with
    the same signature carry the same sections, in the same order, with the
    same classes - whatever their text says.
    """
    if not arch or not arch.strip():
        return []
    try:
        root = etree.fromstring(
            '<root>%s</root>' % arch,
            parser=etree.XMLParser(resolve_entities=False, recover=True))
    except etree.XMLSyntaxError:
        return []
    if root is None:
        return []
    signature = []
    for element in root:
        if not isinstance(element.tag, str):
            continue
        signature.append((
            element.tag.lower(),
            _block_key(element),
            tuple(sorted((element.get('class') or '').split())),
        ))
    return signature


def as_html(arch):
    """Re-serialise a view arch for a browser to parse directly.

    A view arch is XML, so a childless element may be written ``<i ... />``.
    Odoo renders a stored page through QWeb, which parses that XML and emits
    ``<i ...></i>``, so a real page is fine. Anything that pushes the arch
    straight into a document instead - the draft preview, the Html widget -
    hands it to the browser's HTML parser, which does not honour the closing
    slash on a non-void element: the ``<i>`` stays open and the rest of the
    block becomes its children. With ``.fa {display:inline-block}`` on that
    icon, the whole section collapses to shrink-to-fit and the text wraps one
    word per line.

    Serialising as HTML closes those tags properly and leaves void elements
    alone.
    """
    if not arch or not arch.strip():
        return ''
    try:
        root = etree.fromstring(
            '<root>%s</root>' % arch,
            parser=etree.XMLParser(resolve_entities=False))
    except etree.XMLSyntaxError:
        # Not XML: it has not been through the gate, so pass it on untouched
        # rather than lose the preview entirely.
        return arch
    parts = [root.text or '']
    for child in root:
        parts.append(etree.tostring(child, encoding='unicode', method='html'))
    return ''.join(parts)


def create_page(record, arch):
    """Create a brand new, unpublished website page holding ``arch``."""
    env = record.env
    website = record.website_id or env['website'].get_current_website()
    name = (record.page_url or record.page_title or record.name or '').strip().lstrip('/')
    if not name:
        raise UserError(_("Set a page URL or a page title before applying."))

    # new_page() reads the website from the context for the view, but falls back
    # to the *current* website for the page record itself: force it through
    # page_values so the page really lands on the website picked on the form.
    result = env['website'].with_context(website_id=website.id).new_page(
        name=name,
        add_menu=False,
        template='website.default_page',
        ispage=True,
        page_title=record.page_title or record.name,
        sections_arch=arch,
        page_values={'website_id': website.id},
    )
    page = env['website.page'].browse(result['page_id'])
    page.view_id.website_id = website
    # A generated page never goes live on its own.
    page.is_published = False
    return page


def update_page(record, arch):
    """Replace the body of an existing page with ``arch``.

    Only the content of ``div#wrap`` is swapped: the ``t-call="website.layout"``
    shell, and therefore the header/footer of the site, is preserved.
    """
    page = record.reference_page_id
    if not page:
        raise UserError(_("Select the page to edit first."))
    view = page.view_id.with_context(website_id=page.website_id.id)
    tree = html.fromstring(view.arch)
    wraps = tree.xpath('//div[@id="wrap"]')
    if not wraps:
        raise UserError(_(
            "The page '%s' has no editable body (no div#wrap), it cannot be "
            "rewritten by the AI.", page.name))

    wrap = wraps[0]
    for child in list(wrap):
        wrap.remove(child)
    wrap.text = None
    for fragment in html.fragments_fromstring(arch):
        if isinstance(fragment, str):
            continue
        wrap.append(fragment)

    view.write({'arch': etree.tostring(tree, encoding='unicode', method='xml')})
    return page


def page_arch(page, combined=False):
    """Return the arch of a page, read in its own website's context.

    Without the website in the context the ORM hands back the generic version
    of a COWed view, which is why a page that looks current on the site can
    read as an outdated layout here.

    :param combined: apply the inheriting views on top of the base arch. Use it
        to see what the page actually renders; keep it False when the arch is
        about to be written back, since the inherited content would be baked
        into the base view and then applied a second time.
    """
    if not page or not page.view_id:
        return ''
    view = page.view_id.with_context(website_id=page.website_id.id, lang=None)
    if combined:
        try:
            return view.get_combined_arch()
        except Exception:  # noqa: BLE001 - fall back to the plain arch
            _logger.warning(
                "Could not combine the inherited views of page %s, using its "
                "own arch instead.", page.id, exc_info=True)
    return view.arch or ''


def _page_wrap(page, combined=False):
    """Return the ``div#wrap`` element of a page, or the whole tree."""
    arch = page_arch(page, combined=combined)
    if not arch:
        return None
    try:
        tree = html.fromstring(arch)
    except (etree.ParserError, etree.XMLSyntaxError):
        return None
    wraps = tree.xpath('//div[@id="wrap"]')
    return wraps[0] if wraps else tree


def _content_children(element, depth=0):
    """Descend through layout wrappers to the real content blocks.

    A page body is usually a single ``div.oe_structure`` holding every section.
    Taking the body's children literally therefore yields one enormous block,
    which then gets cut to fit the budget - so the AI only ever sees the top of
    the first section. Step through those wrappers first.
    """
    children = [child for child in element if isinstance(child.tag, str)]
    if len(children) == 1 and depth < 4:
        only = children[0]
        classes = (only.get('class') or '').split()
        is_snippet = any(css.startswith('s_') for css in classes)
        if only.tag.lower() in ('div', 'main') and not is_snippet and len(only):
            return _content_children(only, depth + 1)
    return children


def text_of(arch):
    """Return the visible text of a markup fragment.

    Sending raw markup to a model that only needs the wording wastes most of
    the budget on classes and attributes.
    """
    if not arch:
        return ''
    try:
        fragments = html.fragments_fromstring(arch)
    except (etree.ParserError, etree.XMLSyntaxError):
        return ''
    parts = []
    for fragment in fragments:
        if isinstance(fragment, str):
            parts.append(fragment)
        else:
            # itertext() rather than text_content(): the latter concatenates
            # adjacent elements with no separator, running a heading straight
            # into the paragraph below it.
            parts.extend(fragment.itertext())
    return ' '.join(' '.join(parts).split())


def _block_key(element):
    """Identify what kind of snippet a block is."""
    snippet = element.get('data-snippet')
    if snippet:
        return snippet
    for css in (element.get('class') or '').split():
        if css.startswith('s_'):
            return css
    return element.tag.lower()


def snippet_inventory(page, combined=False):
    """Return ``[(snippet key, how many times it is used), ...]``.

    This is the palette the AI is allowed to build from. Without it the model
    falls back on plain text sections, because those are what a generic Odoo
    page is made of - and the result reads as a different site.
    """
    wrap = _page_wrap(page, combined=combined)
    if wrap is None:
        return []
    counts, order = {}, []
    for child in _content_children(wrap):
        key = _block_key(child)
        if key not in counts:
            counts[key] = 0
            order.append(key)
        counts[key] += 1
    return [(key, counts[key]) for key in order]


def representative_blocks(page, combined=False):
    """Return one full example of each distinct snippet on the page.

    Sending the first N blocks in page order only ever shows the top of the
    page, so snippet types used further down are never demonstrated. One
    example per type covers the whole design within the same budget.
    """
    wrap = _page_wrap(page, combined=combined)
    if wrap is None:
        return []
    seen, blocks = set(), []
    for child in _content_children(wrap):
        key = _block_key(child)
        if key in seen:
            continue
        seen.add(key)
        blocks.append(
            (key, etree.tostring(child, encoding='unicode', method='xml').strip()))
    return blocks


def image_sources(page, combined=False, limit=IMAGE_SRC_LIMIT):
    """Return the image URLs already used on the page.

    An AI cannot invent a working image URL: anything it makes up renders as
    Odoo's broken-image placeholder. These URLs point at real attachments on
    this website, so they are the only ones safe to reuse.
    """
    wrap = _page_wrap(page, combined=combined)
    if wrap is None:
        return []
    sources = []

    def _add(url):
        url = (url or '').strip()
        if url and not url.startswith('data:') and url not in sources:
            sources.append(url)

    for element in wrap.iter():
        if not isinstance(element.tag, str) or len(sources) >= limit:
            continue
        if element.tag.lower() == 'img':
            _add(element.get('src'))
        style = element.get('style') or ''
        if 'url(' in style:
            for match in BACKGROUND_URL_RE.findall(style):
                _add(match)
    return sources[:limit]


def page_blocks(page, combined=False):
    """Return the page body split into its real content blocks.

    Splitting on block boundaries lets the caller send whole sections to the
    AI. A page cut at a fixed character count lands mid-tag, and the model then
    has no complete example of the site's markup to copy.
    """
    wrap = _page_wrap(page, combined=combined)
    if wrap is None:
        return []
    return [
        etree.tostring(child, encoding='unicode', method='xml').strip()
        for child in _content_children(wrap)
    ]


def page_body(page, combined=False):
    """Return the inner markup of a page body, for use as AI context."""
    wrap = _page_wrap(page, combined=combined)
    if wrap is None:
        return page_arch(page, combined=combined)
    parts = [wrap.text or '']
    parts += [
        etree.tostring(child, encoding='unicode', method='xml')
        for child in wrap if isinstance(child.tag, str)
    ]
    return ''.join(parts).strip()


def _outline_element(element, depth, lines, max_depth):
    if not isinstance(element.tag, str):
        return
    tag = element.tag.lower()
    # Inline tags matter only when they carry a class: <span class="o_..."> and
    # <i class="fa fa-..."> are part of the design, bare ones are just text.
    if tag in INLINE_TAGS and not element.get('class'):
        return
    attributes = []
    for name in OUTLINE_ATTRS:
        value = element.get(name)
        if value:
            attributes.append('%s="%s"' % (name, ' '.join(value.split())))
    lines.append('%s<%s%s>' % (
        '  ' * depth, tag, (' ' + ' '.join(attributes)) if attributes else ''))
    if depth >= max_depth:
        return
    for child in element:
        _outline_element(child, depth + 1, lines, max_depth)


def structure_outline(page, combined=False, max_depth=OUTLINE_MAX_DEPTH):
    """Return a text skeleton of the page: every block, its classes and its
    builder attributes, with all the copy stripped out.

    This is what lets the AI match a long page. The outline stays small enough
    to send in full even for pages far past the character budget, so the model
    sees the site's complete structural vocabulary rather than the first few
    sections of it.
    """
    wrap = _page_wrap(page, combined=combined)
    if wrap is None:
        return ''
    lines = []
    for child in _content_children(wrap):
        _outline_element(child, 0, lines, max_depth)
    return '\n'.join(lines)
