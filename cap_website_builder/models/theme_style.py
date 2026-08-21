"""The styles a site adds on top of stock Odoo.

A page generated without them can only ever look like stock Odoo, however good
its copy is. There are two ways a site adds styles, and this reads both:

* a custom module in the addons path, contributing SCSS and JS to
  ``web.assets_frontend`` (that is where a real skin lives);
* whatever was typed in Website > Customize Code, stored as an attachment whose
  URL starts with ``/_custom/``.

The compiled bundle is the honest source for the first: it is what the browser
loads, and its source comments name the file every rule came from, whichever
way the module declared its assets. Skin files run to hundreds of kilobytes, so
what goes to the model is a distilled vocabulary - each class with what it
actually does - rather than the stylesheet itself.
"""
import base64
import logging
import os
import re

from lxml import etree

from odoo.tools.translate import _

from . import page_writer

_logger = logging.getLogger(__name__)

CUSTOM_URL_PREFIX = '/_custom/'
FRONTEND_BUNDLE = 'web.assets_frontend.min.css'

# Budgets in characters, so a big skin cannot crowd out the page copy.
RULES_BUDGET = 26000
JS_BUDGET = 3000
DECLARATION_CHARS = 160

# `/* /module/static/src/scss/file.scss */` markers the asset compiler leaves.
SOURCE_COMMENT_RE = re.compile(r'/\*\s*(/[\w./-]+?\.(?:s?css))\s*\*/')
RULE_RE = re.compile(r'([^{}]+)\{([^{}]*)\}')
CLASS_RE = re.compile(r'\.(-?[_a-zA-Z][\w-]*)')

# What custom JavaScript binds to. Those are the hooks a generated block has to
# carry for the behaviour to apply to it.
JS_HOOK_RE = re.compile(
    r"""(?:querySelector(?:All)?|closest|matches)\(\s*['"]([^'"]+)['"]"""
    r"""|classList\.(?:add|remove|toggle|contains)\(\s*['"]([^'"]+)['"]"""
    r"""|(?:getAttribute|hasAttribute)\(\s*['"](data-[\w-]+)['"]"""
    r"""|selector\s*[:=]\s*['"]([^'"]+)['"]""")


def _stock_roots():
    """The addons directories stock Odoo ships, as a set of absolute paths.

    Anchored on ``base`` and ``web``: both are always installed, always core,
    and they live in *different* addons directories (``odoo/odoo/addons`` and
    ``odoo/addons``), so one alone leaves half of Odoo looking custom.

    Not derived from ``odoo.__file__``, which is None in Odoo 19 - ``odoo`` is
    a namespace package. Reading it raised, and the failure classified every
    module as stock, which silently dropped the site's whole skin from the
    style guide.
    """
    roots = set()
    for module in ('base', 'web'):
        path = _module_path(module)
        if path:
            roots.add(os.path.dirname(os.path.abspath(path)))
    return roots


def _module_path(module):
    try:
        from odoo.modules.module import get_module_path
        return get_module_path(module, display_warning=False) or ''
    except Exception:  # noqa: BLE001
        return ''


def _is_custom_module(module):
    """True when the module is not part of stock Odoo or Enterprise.

    Only those carry a site's own design. Stock classes are already known to
    the model, and listing them would bury the handful that are not.
    """
    roots = _stock_roots()
    if not roots:
        # The real failure: nothing can be classified at all. Say "stock" and
        # send no style guide, because calling every module custom would bury
        # the site's own classes under the whole of Odoo.
        _logger.warning(
            "Cannot locate stock Odoo's addons directories, so no style guide "
            "is sent.")
        return False

    path = _module_path(module)
    if not path:
        # Not a module directory at all. The bundle also carries Customize Code
        # under /_custom/, which is read from its attachment instead, so this
        # is routine rather than a problem.
        return False
    path = os.path.abspath(path)
    if any(path.startswith(root) for root in roots):
        return False
    return '/enterprise/' not in path.replace(os.sep, '/')


def _text_of(attachment):
    if attachment.datas:
        try:
            return base64.b64decode(attachment.datas).decode('utf-8', 'replace')
        except (ValueError, TypeError):
            return ''
    raw = attachment.raw
    if isinstance(raw, bytes):
        return raw.decode('utf-8', 'replace')
    return raw or ''


def _bundle_css(env, website):
    """The compiled frontend stylesheet for this website."""
    attachments = env['ir.attachment'].sudo()
    if website:
        attachments = attachments.search(
            [('name', '=', FRONTEND_BUNDLE), ('website_id', '=', website.id)],
            order='id desc', limit=1)
    if not attachments:
        attachments = env['ir.attachment'].sudo().search(
            [('name', '=', FRONTEND_BUNDLE), ('website_id', '=', False)],
            order='id desc', limit=1)
    return _text_of(attachments) if attachments else ''


def _split_bundle(env, website):
    """The bundle split into this site's own CSS and stock Odoo's.

    Both halves matter. The site's half is the vocabulary; stock's half is what
    makes a name *ordinary*, which is how `.cap-eyebrow` is told apart from a
    `.btn` the skin merely restyles.
    """
    css = _bundle_css(env, website)
    blocks, stock_names, keep = [], set(), {}
    if not css:
        return blocks, stock_names
    marks = list(SOURCE_COMMENT_RE.finditer(css))
    for index, mark in enumerate(marks):
        path = mark.group(1)
        end = marks[index + 1].start() if index + 1 < len(marks) else len(css)
        module = path.strip('/').split('/')[0]
        if module not in keep:
            keep[module] = _is_custom_module(module)
        body = css[mark.end():end]
        if keep[module]:
            blocks.append((path, body))
        else:
            for rule in RULE_RE.finditer(body):
                stock_names.update(
                    CLASS_RE.findall(rule.group(1).split('*/')[-1]))
    return blocks, stock_names


def custom_css(env, website):
    """The parts of the compiled stylesheet that belong to this site.

    Returns ``[(source path, css)]``: only the files from custom modules and
    from Customize Code, in the order the browser applies them.
    """
    blocks, _stock = _split_bundle(env, website)

    # Customize Code lives in an attachment, not in a module.
    website_ids = [False] + ([website.id] if website else [])
    for attachment in env['ir.attachment'].sudo().search([
        ('url', '=like', CUSTOM_URL_PREFIX + '%'),
        ('name', '=like', '%.scss'),
        ('website_id', 'in', website_ids),
    ]):
        body = _text_of(attachment).strip()
        if body:
            blocks.append((attachment.name, body))
    return blocks


def class_rules(blocks):
    """``[(class name, what it does)]`` for every class the site defines.

    A class is only usable if the model knows what it draws, so each one keeps
    a trimmed copy of its declarations rather than just its name.
    """
    # The site's design system is the module that writes the most CSS; a small
    # add-on module writes a handful of classes for one page. When the budget
    # cannot hold everything, the design system is what has to survive.
    weight, order, seen, source = {}, {}, {}, {}
    for path, css in blocks:
        module = path.strip('/').split('/')[0]
        weight[module] = weight.get(module, 0) + len(css)

    for index, (path, css) in enumerate(blocks):
        module = path.strip('/').split('/')[0]
        for rule in RULE_RE.finditer(css):
            selector, body = rule.group(1), ' '.join(rule.group(2).split())
            if not body:
                continue
            selector = selector.split('*/')[-1]
            for name in CLASS_RE.findall(selector):
                order.setdefault(name, index)
                # A class is usually written once in full and then tweaked in
                # context (inside a colour block, on hover, on mobile). The
                # fullest rule is the one that says what the class draws, so it
                # wins over whichever happens to come first.
                if len(body) > len(seen.get(name, '')):
                    seen[name] = body
                    source[name] = module

    ranked = sorted(
        seen, key=lambda name: (-weight.get(source[name], 0), order[name]))
    return [(name, seen[name][:DECLARATION_CHARS]) for name in ranked]


def js_hooks(env, website):
    """Selectors and data attributes the site's own JavaScript looks for."""
    modules, hooks = set(), []
    for path, _css in custom_css(env, website):
        module = path.strip('/').split('/')[0]
        if not path.startswith(CUSTOM_URL_PREFIX):
            modules.add(module)

    for module in sorted(modules):
        root = _module_path(module)
        js_root = os.path.join(root, 'static', 'src', 'js') if root else ''
        if not js_root or not os.path.isdir(js_root):
            continue
        for name in sorted(os.listdir(js_root)):
            if not name.endswith('.js'):
                continue
            try:
                with open(os.path.join(js_root, name), encoding='utf-8') as handle:
                    source = handle.read()
            except OSError:
                continue
            found = []
            for match in JS_HOOK_RE.finditer(source):
                hook = next(group for group in match.groups() if group)
                if hook not in found and (
                        hook.startswith(('.', '[data-', 'data-', 'cap'))
                        or hook.startswith('#')):
                    found.append(hook)
            if found:
                hooks.append((name, found[:12]))

    # Attachment JavaScript, from Customize Code.
    website_ids = [False] + ([website.id] if website else [])
    for attachment in env['ir.attachment'].sudo().search([
        ('url', '=like', CUSTOM_URL_PREFIX + '%'),
        ('name', '=like', '%.js'),
        ('website_id', 'in', website_ids),
    ]):
        source = _text_of(attachment)
        found = []
        for match in JS_HOOK_RE.finditer(source):
            hook = next(group for group in match.groups() if group)
            if hook not in found:
                found.append(hook)
        if found:
            hooks.append((attachment.name, found[:12]))
    return hooks


def sources(blocks):
    """The modules a style guide was built from, biggest contributor first."""
    weight = {}
    for path, css in blocks:
        module = path.strip('/').split('/')[0]
        weight[module] = weight.get(module, 0) + len(css)
    return sorted(weight.items(), key=lambda item: -item[1])


def style_guide(env, website):
    """The block describing this site's own styles, or '' when it has none."""
    blocks = custom_css(env, website)
    rules = class_rules(blocks)
    if not rules:
        return ''

    lines, used = [], 0
    for name, body in rules:
        line = '.%s { %s }' % (name, body)
        if used + len(line) > RULES_BUDGET:
            lines.append('... %s more classes, not listed' % (len(rules) - len(lines)))
            break
        lines.append(line)
        used += len(line)

    source_names = ', '.join(module for module, _size in sources(blocks))
    guide = (
        "=== THIS SITE'S OWN STYLES ===\n"
        "On top of the theme, this website loads its own CSS (from %(sources)s).\n"
        "These classes are what make its pages look like its pages, so build\n"
        "with them: when a block you are writing matches something styled here,\n"
        "put that class on it. Rules are listed as the class and what it draws.\n"
        "\n"
        "Two things to respect:\n"
        "- A class works with the markup its rule expects around it. Where a\n"
        "  rule reads like a child or descendant selector, reproduce that\n"
        "  nesting, not just the outer class name.\n"
        "- Use these and the snippet classes only. Never invent a class that is\n"
        "  defined nowhere, and never write an inline style to imitate one:\n"
        "  the site's own class already exists for it.\n\n"
        "%(rules)s\n"
    ) % {'sources': source_names or 'this website', 'rules': '\n'.join(lines)}

    hooks = js_hooks(env, website)
    if hooks:
        hook_lines, used = [], 0
        for name, found in hooks:
            line = '- %s: %s' % (name, ', '.join(found))
            if used + len(line) > JS_BUDGET:
                break
            hook_lines.append(line)
            used += len(line)
        guide += (
            "\nThe site's JavaScript runs on every page and looks for these.\n"
            "Markup that carries them gets the behaviour; markup that does not\n"
            "is inert. Use them when the block is meant to behave that way.\n%s\n"
            % '\n'.join(hook_lines))
    return guide + '\n'


# --------------------------------------------------------------------------
# The site's own pages, as worked examples
# --------------------------------------------------------------------------
# A vocabulary list says what a class draws; it does not show a model how the
# site actually builds a section out of those classes. The pages already on the
# site do, so they are mined for one real block per kind and sent as the
# palette, exactly as a chosen reference page would be.
HOUSE_PAGES_SCANNED = 25
HOUSE_EXAMPLES = 8
HOUSE_BUDGET = 30000
HOUSE_BLOCK_MAX = 9000   # a rich card grid or process-steps block is ~9k


# In a stylesheet a class is written `.name`; in markup it is a token inside a
# class attribute. Matching CSS syntax against HTML finds nothing at all.
MARKUP_CLASS_RE = re.compile(r'class="([^"]*)"')


def _custom_classes_in(markup, vocabulary):
    """Which of the site's own classes appear in a piece of markup."""
    found = set()
    for attribute in MARKUP_CLASS_RE.findall(markup or ''):
        for name in attribute.split():
            if name in vocabulary:
                found.add(name)
    return found


def distinctive_classes(env, website):
    """The classes this site invented, not the ones it restyles.

    A skin redefines `h1`, `lead`, `btn` and `o_cc1` as well as adding
    `cap-eyebrow`. Counting the redefinitions makes every block look rich in
    house style, so a set cover over them is satisfied without ever reaching
    for a class the model would not have guessed by itself.
    """
    blocks, stock_names = _split_bundle(env, website)
    return {name for name, _body in class_rules(blocks)
            if name not in stock_names}


def _page_candidates(env, website, vocabulary):
    """This site's pages, richest in its own classes first."""
    domain = [('website_id', 'in', [website.id, False])] if website else []
    pages = env['website.page'].sudo().search(
        domain, order='is_published desc, id desc', limit=200)
    scored = []
    for page in pages:
        arch = page.arch or ''
        if not arch:
            continue
        found = _custom_classes_in(arch, vocabulary)
        if found:
            scored.append((len(found), page.id, page, found))
    scored.sort(key=lambda row: -row[0])
    return [row[2] for row in scored[:HOUSE_PAGES_SCANNED]]


def house_blocks(env, website):
    """Real sections from this site's pages, chosen to show the most classes.

    Greedy set cover over the site's own vocabulary: each block picked is the
    one adding the most classes not yet demonstrated. Eight blocks chosen that
    way teach far more of a design system than the eight biggest, or the first
    eight on the busiest page.
    """
    vocabulary = distinctive_classes(env, website)
    if not vocabulary:
        return []

    seen_markup, blocks = set(), []
    for page in _page_candidates(env, website, vocabulary):
        # _page_wrap does the work: it reads the arch in the page's own website
        # context, applies the inheriting views, and returns the div#wrap that
        # holds the sections. Parsing page.arch directly would yield the QWeb
        # template - a single <t t-call="website.layout"> - and no blocks.
        try:
            wrap = page_writer._page_wrap(page, combined=True)
        except Exception:  # noqa: BLE001 - one bad page must not stop the rest
            continue
        if wrap is None:
            continue
        for element in page_writer._content_children(wrap):
            markup = etree.tostring(element, encoding='unicode', method='html')
            if len(markup) > HOUSE_BLOCK_MAX:
                continue
            found = _custom_classes_in(markup, vocabulary)
            if not found:
                continue
            fingerprint = (page_writer._block_key(element), frozenset(found))
            if fingerprint in seen_markup:
                continue
            seen_markup.add(fingerprint)
            blocks.append({
                'key': page_writer._block_key(element),
                'url': page.url,
                'classes': found,
                'markup': markup,
            })

    # Greedy set cover: the block that teaches the most that is still unknown.
    chosen, covered, used = [], set(), 0
    while blocks and len(chosen) < HOUSE_EXAMPLES:
        blocks.sort(key=lambda block: -len(block['classes'] - covered))
        best = blocks.pop(0)
        gain = best['classes'] - covered
        if not gain:
            break
        if used + len(best['markup']) > HOUSE_BUDGET:
            break
        chosen.append(best)
        covered |= best['classes']
        used += len(best['markup'])
    return chosen


def house_palette(env, website):
    """The palette prompt built from this site's own pages, or ''."""
    return render_house_palette(house_blocks(env, website))


IMAGE_SRC_RE = re.compile(r'src="(/[^"]+)"')
HOUSE_IMAGE_LIMIT = 25


def house_images(blocks):
    """The image URLs the example blocks use, in the order they appear."""
    images = []
    for block in blocks:
        for src in IMAGE_SRC_RE.findall(block['markup']):
            if src not in images:
                images.append(src)
    return images[:HOUSE_IMAGE_LIMIT]


def render_house_palette(blocks):
    """The palette prompt for blocks already mined, so nothing is read twice.

    The examples are stripped of their images: generated pages are text only,
    and a palette full of pictures is an instruction to use pictures whatever
    the prompt says.
    """
    if not blocks:
        return ''
    blocks = [dict(block, markup=page_writer.strip_images(block['markup'])[0])
              for block in blocks]
    examples = '\n\n'.join(
        '<!-- from %s -->\n%s' % (block['url'], block['markup'])
        for block in blocks)
    return _(
        "=== HOW THIS SITE BUILDS ITS SECTIONS ===\n"
        "These are real sections from pages already on this website. They are\n"
        "the palette: build the new page out of blocks like these, and no\n"
        "others.\n\n"
        "For each section you need, take the closest block below and change\n"
        "only the words inside the text nodes and the image URLs. Keep\n"
        "everything else exactly: the s_* snippet class and the site's own\n"
        "classes, the data-snippet and data-name attributes, the colour and\n"
        "spacing classes, and the container / row / col nesting. Those classes\n"
        "are what make the page look like this site rather than like stock\n"
        "Odoo, and they only work with the markup their rules expect.\n\n"
        "Vary the blocks as the copy needs: never three of the same kind in a\n"
        "row, and finish with the call-to-action block if one is shown.\n\n"
        "%(images)s\n\n"
        "%(examples)s\n", examples=examples,
        images=_(
            "These examples have had their images removed: the page you are "
            "building is text only. Do not add an image back."))
