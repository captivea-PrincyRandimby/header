# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class Website(Website):

    def get_seo_data(self, res_id, res_model):
        # Add the JSON-LD field to the payload that pre-fills the SEO dialog.
        res = super().get_seo_data(res_id, res_model)
        record = request.env[res_model].browse(res_id)
        if 'website_meta_json_ld' in record._fields:
            res['website_meta_json_ld'] = record.website_meta_json_ld
        return res
