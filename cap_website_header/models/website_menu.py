from odoo import api, fields, models


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    cap_mega_subtitle = fields.Char(
        string="Header Subtitle",
        translate=True,
        help="Small uppercase line displayed under the menu label in the "
             "Captivea header mega menu bar (e.g. \"Services & Consulting\").",
    )

    cap_menu_description = fields.Char(
        string="Header Description",
        translate=True,
        help="Grey line displayed under the label inside the top bar dropdowns "
             "of the Captivea header (e.g. \"News, tips & use cases\").",
    )

    cap_header_row = fields.Selection(
        selection=[
            ('top', "Top bar"),
            ('mega', "Mega menu bar"),
        ],
        string="Captivea Header Row",
        compute='_compute_cap_header_row',
        store=True,
        readonly=False,
        help="Row of the Captivea header this menu is displayed in. Kept apart "
             "from \"Mega Menu\" on purpose: a top bar menu may carry a mega "
             "menu panel - that is how the \"About\" dropdown gets its free "
             "content while staying in the top bar.",
    )

    @api.depends('is_mega_menu')
    def _compute_cap_header_row(self):
        """Default value only, an explicit choice is never overwritten.

        ``store=True`` + ``readonly=False`` is the standard Odoo idiom for a
        computed field the user may override: the compute runs again whenever
        ``is_mega_menu`` changes, and keeps whatever value is already set. A
        menu therefore lands in the mega menu bar when it is *created* as a mega
        menu, and turning an existing top bar menu into a mega menu leaves it
        where it is - which is exactly what "About" needs.
        """
        for menu in self:
            if not menu.cap_header_row:
                menu.cap_header_row = 'mega' if menu.is_mega_menu else 'top'
