# -*- coding: utf-8 -*-
import json

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Website(models.Model):
    _inherit = 'website'

    # Site-wide JSON-LD (schema.org) — e.g. Organization / WebSite markup that
    # should appear on EVERY page. Concatenated with the per-page JSON-LD at
    # render time (each in its own <script type="application/ld+json">).
    website_global_json_ld = fields.Text(string="Global JSON-LD (schema.org)")
    website_global_json_ld_markup = fields.Html(
        string="Global JSON-LD (rendered)",
        compute='_compute_website_global_json_ld_markup',
        sanitize=False)

    @api.depends('website_global_json_ld')
    def _compute_website_global_json_ld_markup(self):
        for website in self:
            value = website.website_global_json_ld or ''
            website.website_global_json_ld_markup = Markup(value) if value.strip() else False

    @api.constrains('website_global_json_ld')
    def _check_website_global_json_ld(self):
        """Reject invalid JSON so we never inject a broken <script> in <head>."""
        for website in self:
            value = (website.website_global_json_ld or '').strip()
            if not value:
                continue
            try:
                json.loads(value)
            except (ValueError, TypeError) as err:
                raise ValidationError(
                    _("The global JSON-LD is not valid JSON:\n%s", err))
