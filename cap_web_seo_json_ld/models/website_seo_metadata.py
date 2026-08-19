# -*- coding: utf-8 -*-
import json

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WebsiteSeoMetadata(models.AbstractModel):
    _inherit = 'website.seo.metadata'

    # Raw JSON-LD (schema.org) injected verbatim into the page <head>.
    website_meta_json_ld = fields.Text(string="Website JSON-LD (schema.org)")
    # Rendered (raw/unescaped) version for the template. An Html field is output
    # verbatim by QWeb t-out (no &/< escaping), and — unlike a method — it is
    # DELEGATED to website.page via _inherits, so the template never hits a
    # missing attribute whatever the seo_object type (page, product, blog...).
    website_meta_json_ld_markup = fields.Html(
        string="Website JSON-LD (rendered)",
        compute='_compute_website_meta_json_ld_markup',
        sanitize=False)

    @api.depends('website_meta_json_ld')
    def _compute_website_meta_json_ld_markup(self):
        for record in self:
            value = record.website_meta_json_ld or ''
            record.website_meta_json_ld_markup = Markup(value) if value.strip() else False

    @api.constrains('website_meta_json_ld')
    def _check_website_meta_json_ld(self):
        """Reject invalid JSON so we never inject a broken <script> in <head>."""
        for record in self:
            value = (record.website_meta_json_ld or '').strip()
            if not value:
                continue
            try:
                json.loads(value)
            except (ValueError, TypeError) as err:
                raise ValidationError(
                    _("The JSON-LD is not valid JSON:\n%s", err))
