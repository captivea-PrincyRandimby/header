from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

CAP_HEADER_VIEW = 'cap_website_header.template_header_captivea'
CAP_DEFAULT_HEADER_VIEW = 'website.template_header_default'

# Language the provisioned menus are stored in.
#
# Every label below is an `_lt` term: Odoo's `.pot` exporter scans the Python
# files for `_` and `_lt` calls, so they end up in
# `i18n/cap_website_header.pot` like any other code string, and the `.po` files
# give their value in each language. `_cap_translate_menu()` then writes those
# values on the records themselves - a `website.menu` is data, not a template,
# so nothing would translate it otherwise.
CAP_SOURCE_LANG = 'en_US'

# Row 1 (grey top bar).
#
# ``children`` entries become second level menus, rendered as a plain dropdown
# where each line is a label plus the grey ``cap_menu_description``
# (Line1Template1 / Line1Template3 mock-ups). They stay regular ``website.menu``
# records: manageable from Website > Menus, translatable, crawlable.
#
# ``template`` turns the menu into a mega menu *inside the top bar* instead: the
# dropdown then shows free, builder editable content (Line1Template2). The row a
# menu belongs to is ``cap_header_row``, not ``is_mega_menu``, precisely so that
# both can live in row 1.
CAP_TOP_MENUS = [
    {
        'name': _lt("Resources"),
        'children': [
            (_lt("Blog"), '/blog', _lt("News, tips & use cases")),
            (_lt("Customer references"), '/customer-references', _lt("Our successful projects")),
            (_lt("White papers"), '/white-papers', _lt("Guides to download")),
            (_lt("Events"), '/events', _lt("Webinars & trade shows")),
            (_lt("Captivea Apps"), '/captivea-apps', _lt("Our Odoo modules")),
        ],
    },
    {'name': _lt("Offers & methodology"), 'url': '/offers-and-methodology'},
    {'name': _lt("Discover Odoo"), 'url': '/discover-odoo'},
    {'name': _lt("Customer references"), 'url': '/customer-references'},
    {
        'name': _lt("About"),
        'template': 'cap_website_header.s_mega_menu_cap_about',
        # No ``children``: ``website.menu._validate_parent_menu()`` forbids a
        # mega menu from having any ("A mega menu cannot have a parent or child
        # menu"). The panel *is* the content of the dropdown, and it covers the
        # same three destinations.
        #
        # ``superseded_children`` are the submenus the panel replaces: the ones
        # this module used to provision, before "About" became a panel. They are
        # what "Reset the mega menu panels" is allowed to delete to satisfy the
        # native constraint - and nothing else.
        'superseded_children': [
            _lt("About Captivea"),
            _lt("Leadership team"),
            _lt("Our Offices"),
        ],
    },
    {
        'name': _lt("Careers"),
        'children': [
            (_lt("Our HR vision"), '/our-hr-vision', _lt("Our culture & commitments")),
            (_lt("Open positions"), '/open-positions', _lt("Join our teams")),
        ],
    },
]

# Row 3 (mega menu bar). ``template`` is the panel design each mega menu starts
# with; it can then be swapped for any other one from the builder
# (Mega Menu > Template), which is why the four designs are plain snippets.
CAP_MEGA_MENUS = [
    {
        'name': _lt("Transform your organization"),
        'subtitle': _lt("Services & Consulting"),
        'template': 'cap_website_header.s_mega_menu_cap_services',
    },
    {
        'name': _lt("Transform your everyday"),
        'subtitle': _lt("User Journey"),
        'template': 'cap_website_header.s_mega_menu_cap_journeys',
    },
    {
        'name': _lt("Transform your business"),
        'subtitle': _lt("By Industry"),
        'template': 'cap_website_header.s_mega_menu_cap_industries',
    },
    {
        'name': _lt("Transform your solutions"),
        'subtitle': _lt("Odoo & Other Solutions"),
        'template': 'cap_website_header.s_mega_menu_cap_solutions',
    },
]


class Website(models.Model):
    _inherit = 'website'

    cap_header_enabled = fields.Boolean(
        string="Captivea Header",
        compute='_compute_cap_header_enabled',
        inverse='_inverse_cap_header_enabled',
        help="Replace the standard header of this website by the three-row "
             "Captivea header. Only this website is impacted.",
    )

    # ------------------------------------------------------------------
    # Header activation (per website)
    # ------------------------------------------------------------------

    def _cap_website_env(self):
        """Environment carrying ``website_id``.

        ``ir.ui.view.write()`` reads that context key to trigger its
        copy-on-write mechanism: the generic view is left untouched and a
        website specific copy is created/updated instead.
        """
        self.ensure_one()
        return self.env(context=dict(self.env.context, website_id=self.id))

    def _cap_viewref(self, xml_id):
        """Most specific ``ir.ui.view`` of ``xml_id`` for this website."""
        self.ensure_one()
        return self._cap_website_env()['website'].viewref(xml_id, raise_if_not_found=False)

    def _compute_cap_header_enabled(self):
        for website in self:
            view = website._cap_viewref(CAP_HEADER_VIEW)
            website.cap_header_enabled = bool(view) and view.active

    def _inverse_cap_header_enabled(self):
        for website in self:
            website._cap_set_header_enabled(website.cap_header_enabled)

    def _cap_set_header_enabled(self, enabled):
        """Toggle the Captivea header template for this website only.

        The views returned by :meth:`_cap_viewref` already carry ``website_id``
        in their context, so writing on them goes through the copy-on-write.
        """
        self.ensure_one()
        view = self._cap_viewref(CAP_HEADER_VIEW)
        if not view:
            raise UserError(_("The Captivea header template is missing, please upgrade the module."))

        if enabled:
            # Only one header template may be active at a time.
            for xml_id in self.env['theme.utils']._header_templates:
                if xml_id == CAP_HEADER_VIEW:
                    continue
                other = self._cap_viewref(xml_id)
                if other and other.active:
                    other.write({'active': False})
            if not view.active:
                view.write({'active': True})
        else:
            if view.active:
                view.write({'active': False})
            # Otherwise the website would be left without any header template.
            default = self._cap_viewref(CAP_DEFAULT_HEADER_VIEW)
            if default and not default.active:
                default.write({'active': True})

    # ------------------------------------------------------------------
    # Labels and their translations
    # ------------------------------------------------------------------

    def _cap_label(self, term, lang=CAP_SOURCE_LANG):
        """Value of one of the labels declared above, in ``lang``.

        ``lang`` has to be an active language: ``Environment.lang`` refuses any
        other one, which is why :meth:`_cap_target_langs` only ever returns
        installed ones.
        """
        return self.env(context={'lang': lang})._(term)

    def _cap_target_langs(self):
        """Languages a provisioned label has to be written in, besides English."""
        return [
            code for code, _name in self.env['res.lang'].get_installed()
            if code != CAP_SOURCE_LANG
        ]

    def _cap_source_menus(self):
        """``website.menu`` read and written in the source language.

        The provisioning matches menus by name, so it has to compare with the
        English value whatever the language of the user running it. On a
        translated field, both ``search()`` and ``read()`` answer for
        ``env.lang``, hence the explicit context.
        """
        return self.env['website.menu'].with_context(lang=CAP_SOURCE_LANG)

    def _cap_translate_menu(self, menu, terms):
        """Fill the per language values of ``menu`` from the ``.po`` files.

        ``terms`` maps a field name to its ``_lt`` label. Writing a field that
        is ``translate=True`` under a language only stores the value of that
        language; the English source, written at creation, stays the reference.

        A value that no longer matches the English source has been translated
        by hand - from Website > Menus or from the website translation editor -
        and is left alone: the catalog is a starting point, not the truth.
        """
        for lang in self._cap_target_langs():
            values = {}
            for field_name, term in terms.items():
                source = self._cap_label(term)
                translation = self._cap_label(term, lang)
                if translation == source:
                    continue  # nothing for that language in the `.po` files
                if menu.with_context(lang=lang)[field_name] != source:
                    continue  # already translated
                values[field_name] = translation
            if values:
                menu.with_context(lang=lang).write(values)

    def _cap_translate_panel(self, menu, template):
        """Translate the ``mega_menu_content`` of ``menu`` in every language.

        ``mega_menu_content`` is translated *term by term*
        (``translate=html_translate``), and that changes how it has to be
        written. Assigning a translated document under a language would not
        translate anything: Odoo pairs the terms of the new value with those it
        already knows, finds nothing in common between two languages, and ends
        up replacing the English source. ``update_field_translations()`` is the
        API that takes the pairing itself, and it is the one the website
        translation editor goes through.

        The pairing is built by rendering the same template twice and zipping
        the two term lists: same document, same terms, same order - only the
        text differs.

        Only called right after the English content has been written, and never
        on a panel left as it is: the keys are the terms Odoo has *stored*, so
        a panel edited in the builder would pair with the reference design.
        """
        field = menu._fields['mega_menu_content']
        source_terms = field.get_trans_terms(menu.with_context(lang=CAP_SOURCE_LANG).mega_menu_content)
        for lang in self._cap_target_langs():
            # Through `field.translate` with a callback that keeps every term:
            # that is the very serialisation Odoo applies when storing the
            # value, so both sides of the zip are normalised the same way.
            rendered = self._cap_render_panel(template, lang)
            terms = field.get_trans_terms(field.translate(lambda term: None, rendered))
            if len(terms) != len(source_terms):
                continue  # not the same document, nothing can be paired
            translations = {
                source: term
                for source, term in zip(source_terms, terms)
                if term != source
            }
            if translations:
                menu.update_field_translations('mega_menu_content', {lang: translations})

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------

    def _cap_get_menu(self, name, parent):
        return self._cap_source_menus().search([
            ('website_id', '=', self.id),
            ('parent_id', '=', parent.id),
            ('name', '=', name),
        ], limit=1)

    def _cap_render_panel(self, template, lang=CAP_SOURCE_LANG):
        """Initial (editable) content of a mega menu panel, in ``lang``."""
        return self.env['ir.ui.view'].with_context(lang=lang)._render_template(template)

    def _cap_panel_menus(self):
        """``(name, template, mega_menu_classes)`` of every provisioned panel.

        ``mega_menu_classes`` is the native field behind the builder's
        "Mega Menu > Size" option. Row 3 panels span the container; the top bar
        one is left empty, i.e. *Default*, so it behaves as a regular dropdown
        anchored under its toggle (Line1Template2).
        """
        panels = [
            (mega['name'], mega['template'], 'o_mega_menu_container_size')
            for mega in CAP_MEGA_MENUS
        ]
        panels += [
            (entry['name'], entry['template'], '')
            for entry in CAP_TOP_MENUS if entry.get('template')
        ]
        return panels

    def action_cap_provision_header_menus(self):
        """Create the Captivea menu structure for the selected websites.

        Idempotent: existing menus are matched by name under the same parent,
        are never renamed, re-targeted nor deleted, so a second call only adds
        what is missing - plus the description of an entry that has none yet,
        and the translations still missing in the languages installed since.
        """
        for website in self:
            website._cap_provision_header_menus()
        return True

    def action_cap_reset_mega_menu_panels(self):
        """Put the reference panels back on the Captivea menus.

        Destructive on purpose, and only for the menus listed in
        ``CAP_MEGA_MENUS`` and ``CAP_TOP_MENUS``: their ``mega_menu_content`` is
        overwritten, so any change made on those panels in the builder is lost.

        This is also the upgrade path for the websites provisioned before a
        design existed - "About" in particular, which used to be a plain
        dropdown: writing the content is what turns it into a mega menu, and
        ``cap_header_row`` being already set to ``top`` keeps it in the top bar.

        Since the English content is rewritten here, this is also the only place
        a panel can be safely translated again, see :meth:`_cap_translate_panel`.
        """
        for website in self:
            root = website.menu_id
            for term, template, classes in website._cap_panel_menus():
                menu = website._cap_get_menu(website._cap_label(term), root)
                if menu:
                    website._cap_clear_superseded_children(menu)
                    menu.with_context(lang=CAP_SOURCE_LANG).write({
                        'mega_menu_content': website._cap_render_panel(template),
                        'mega_menu_classes': classes,
                    })
                    website._cap_translate_panel(menu, template)
        return True

    def _cap_clear_superseded_children(self, menu):
        """Drop the submenus a panel replaces, so the native rule is satisfied.

        ``website.menu._validate_parent_menu()`` forbids a mega menu from having
        children, so a top bar menu that used to be a plain dropdown cannot
        receive a panel while its submenus are still there.

        Only the entries this module provisioned itself are removed - they are
        listed in ``superseded_children`` and the panel leads to the very same
        pages. Anything else is a deliberate addition: rather than deleting it
        silently, the operation stops and says what stands in the way.
        """
        self.ensure_one()
        children = menu.child_id
        if not children:
            return
        menu_name = menu.with_context(lang=CAP_SOURCE_LANG).name
        superseded = next(
            ([self._cap_label(term) for term in entry.get('superseded_children', [])]
             for entry in CAP_TOP_MENUS
             if self._cap_label(entry['name']) == menu_name and entry.get('template')),
            [],
        )
        unexpected = children.with_context(lang=CAP_SOURCE_LANG).filtered(
            lambda child: child.name not in superseded
        )
        if unexpected:
            # Back to the language of the caller: the message names menus the
            # user has to go and find, so it has to name them as the interface
            # does, not as this file does.
            raise UserError(_(
                "The \"%(menu)s\" menu of website %(website)s carries a mega menu "
                "panel, and Odoo does not allow a mega menu to have submenus. "
                "Please move or delete these submenus first: %(children)s.",
                menu=menu.with_env(self.env).name,
                website=self.name,
                children=", ".join(unexpected.with_env(self.env).mapped('name')),
            ))
        children.unlink()

    def _cap_provision_header_menus(self):
        self.ensure_one()
        Menu = self._cap_source_menus()
        root = self.menu_id
        if not root:
            raise UserError(_("Website %s has no root menu.", self.name))

        sequence = 100
        for entry in CAP_TOP_MENUS:
            sequence += 10
            name = self._cap_label(entry['name'])
            menu = self._cap_get_menu(name, root)
            if not menu:
                values = {
                    'name': name,
                    'url': entry.get('url', '#'),
                    'parent_id': root.id,
                    'website_id': self.id,
                    'sequence': sequence,
                    'cap_header_row': 'top',
                }
                if entry.get('template'):
                    # A mega menu that stays in the top bar: free content, but
                    # no `o_mega_menu_*` size class, so the panel keeps the
                    # width and the anchoring of a regular dropdown.
                    #
                    # Only done here, on creation. A menu that already exists as
                    # a plain dropdown is left alone - turning it into a panel
                    # means deleting its submenus, which belongs to the explicit
                    # "Reset the mega menu panels" action.
                    values.update({
                        'mega_menu_content': self._cap_render_panel(entry['template']),
                        'mega_menu_classes': '',
                    })
                menu = Menu.create(values)
                if entry.get('template'):
                    self._cap_translate_panel(menu, entry['template'])
            self._cap_translate_menu(menu, {'name': entry['name']})
            child_sequence = 0
            for child_term, child_url, child_description in entry.get('children', []):
                child_sequence += 10
                child_name = self._cap_label(child_term)
                child = self._cap_get_menu(child_name, menu)
                if child:
                    # Still non destructive: an existing entry keeps its name,
                    # its url and a description that has already been written.
                    # Only an empty one is filled in, so that the websites
                    # provisioned before the descriptions existed get them.
                    if not child.cap_menu_description:
                        child.cap_menu_description = self._cap_label(child_description)
                else:
                    child = Menu.create({
                        'name': child_name,
                        'url': child_url,
                        'cap_menu_description': self._cap_label(child_description),
                        'parent_id': menu.id,
                        'website_id': self.id,
                        'sequence': child_sequence,
                        'cap_header_row': 'top',
                    })
                self._cap_translate_menu(child, {
                    'name': child_term,
                    'cap_menu_description': child_description,
                })

        sequence = 200
        for mega in CAP_MEGA_MENUS:
            sequence += 10
            name = self._cap_label(mega['name'])
            menu = self._cap_get_menu(name, root)
            if not menu:
                menu = Menu.create({
                    'name': name,
                    'cap_mega_subtitle': self._cap_label(mega['subtitle']),
                    'parent_id': root.id,
                    'website_id': self.id,
                    'sequence': sequence,
                    'cap_header_row': 'mega',
                    # Setting the content is what turns the menu into a mega
                    # menu: ``is_mega_menu`` is computed from
                    # ``mega_menu_content``.
                    'mega_menu_content': self._cap_render_panel(mega['template']),
                    'mega_menu_classes': 'o_mega_menu_container_size',
                })
                self._cap_translate_panel(menu, mega['template'])
            self._cap_translate_menu(menu, {
                'name': mega['name'],
                'cap_mega_subtitle': mega['subtitle'],
            })
