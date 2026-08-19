# -*- coding: utf-8 -*-
from odoo import models

# (name, url, sequence) of the Templates submenu items.
TEMPLATE_MENU_ITEMS = [
    ('Home', '/template-home', 910),
    ('Sub-sector (Industry)', '/template-subsector', 930),
    ('Sector hub', '/template-sector', 940),
    ('Team (Business function)', '/template-team', 950),
    ('About', '/template-about', 960),
    ('Country', '/template-country', 970),
    ('Office', '/template-office', 980),
    ('Odoo Partner (country)', '/template-partner', 990),
    ('Product pillar (Odoo)', '/template-product', 1000),
    ('Odoo app', '/template-app-odoo', 1010),
    ('Captivea add-on', '/template-app-captivea', 1020),
    ('ISV partner', '/template-isv', 1030),
    ('Comparison (ERP)', '/template-comparison', 1040),
    ('Comparison (CMS)', '/template-comparison-cms', 1045),
    ('Offer', '/template-offer', 1050),
    ('Customer benefit', '/template-benefit', 1060),
    ('Case study', '/template-case-study', 1070),
]


class Website(models.Model):
    _inherit = 'website'

    def _captivea_generate_template_menu(self):
        """Build the "Templates" top menu and its children imperatively:
        create (or reuse) the parent, then create/re-parent every child under
        it via the parent's real id. This avoids the theme.website.menu
        materialization issues where children lose their parent link."""
        Menu = self.env['website.menu'].sudo()
        # Only ever touch NON-theme menus: menus materialized from theme.website.menu
        # (theme_template_id set) are garbage-collected at the end of the module
        # load, so reusing them would delete our work too.
        not_theme = [('theme_template_id', '=', False)]
        websites = self.env['website'].sudo().search([])
        for website in websites:
            root = website.menu_id
            if not root:
                continue
            # Parent: reuse our own "Templates" menu if it exists, else create it.
            parents = Menu.search(not_theme + [
                ('website_id', '=', website.id),
                ('parent_id', '=', root.id),
                ('name', '=', 'Templates'),
            ])
            parent = parents[:1]
            if not parent:
                parent = Menu.create({
                    'name': 'Templates',
                    'parent_id': root.id,
                    'website_id': website.id,
                    'sequence': 900,
                })
            # Children: reuse our own by url (re-parent) else create a fresh one.
            for name, url, seq in TEMPLATE_MENU_ITEMS:
                child = Menu.search(not_theme + [
                    ('website_id', '=', website.id),
                    ('url', '=', url),
                ], limit=1)
                vals = {
                    'name': name,
                    'url': url,
                    'parent_id': parent.id,
                    'website_id': website.id,
                    'sequence': seq,
                }
                if child:
                    child.write(vals)
                else:
                    Menu.create(vals)
            # Clean up our own duplicate (now childless) "Templates" menus.
            (parents - parent).filtered(lambda m: not m.child_id).unlink()
        return True
