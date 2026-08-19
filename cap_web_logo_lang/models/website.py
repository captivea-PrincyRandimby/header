# -*- coding: utf-8 -*-
import base64

from odoo import fields, models
from odoo.tools import file_open

# Default brand logo shipped with the module (used to prefill the table).
DEFAULT_LOGO_PATH = 'cap_web_logo_lang/static/src/img/default_logo.svg'


class Website(models.Model):
    _inherit = 'website'

    logo_lang_ids = fields.One2many(
        'website.logo.lang', 'website_id', string='Logos per language')

    def get_lang_logo_record(self, lang_code=None):
        """Return the website.logo.lang record (0..1) holding a logo for the
        given language code (defaults to the current context language).
        Falls back to any configured logo row so the header shows the brand
        logo even if the current language has no dedicated row. Public (no
        leading underscore) so it can be called from QWeb; sudo for public render."""
        self.ensure_one()
        lang_code = lang_code or self.env.context.get('lang')
        rows = self.sudo().logo_lang_ids.filtered(lambda r: r.logo)
        if not rows:
            return self.env['website.logo.lang']
        match = rows.filtered(lambda r: r.lang_id.code == lang_code)
        return match[:1] or rows[:1]

    def _default_lang_logo(self):
        """Base64 of the module's bundled default logo (falls back to the
        website's own logo if the file is missing)."""
        try:
            with file_open(DEFAULT_LOGO_PATH, 'rb') as fh:
                return base64.b64encode(fh.read())
        except Exception:
            return False

    def action_generate_lang_logos(self):
        """Create a row for every active language missing on each website and
        prefill it (and any existing row without a logo) with the bundled
        default brand logo."""
        LogoLang = self.env['website.logo.lang'].sudo()
        default_logo = self._default_lang_logo()
        for website in self:
            logo = default_logo or website.logo or False
            by_lang = {r.lang_id: r for r in website.logo_lang_ids}
            for lang in website.language_ids:
                row = by_lang.get(lang)
                if not row:
                    LogoLang.create({
                        'website_id': website.id,
                        'lang_id': lang.id,
                        'logo': logo,
                        'logo_filename': 'default_logo.svg',
                    })
                elif not row.logo and logo:
                    row.write({'logo': logo, 'logo_filename': 'default_logo.svg'})
        return True

    def action_reset_lang_logos(self):
        """Force every active-language row back to the bundled default logo
        (overwrites custom logos)."""
        LogoLang = self.env['website.logo.lang'].sudo()
        default_logo = self._default_lang_logo()
        for website in self:
            logo = default_logo or website.logo or False
            by_lang = {r.lang_id: r for r in website.logo_lang_ids}
            for lang in website.language_ids:
                row = by_lang.get(lang)
                if row:
                    row.write({'logo': logo, 'logo_filename': 'default_logo.svg'})
                else:
                    LogoLang.create({
                        'website_id': website.id, 'lang_id': lang.id,
                        'logo': logo, 'logo_filename': 'default_logo.svg',
                    })
        return True
