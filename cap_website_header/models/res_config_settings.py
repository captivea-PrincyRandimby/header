from odoo import _, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cap_header_enabled = fields.Boolean(
        related='website_id.cap_header_enabled',
        readonly=False,
    )

    def action_cap_provision_header_menus(self):
        self.ensure_one()
        return self._cap_website().action_cap_provision_header_menus()

    def action_cap_reset_mega_menu_panels(self):
        self.ensure_one()
        return self._cap_website().action_cap_reset_mega_menu_panels()

    def _cap_website(self):
        if not self.website_id:
            raise UserError(_("Please select a website first."))
        return self.website_id
