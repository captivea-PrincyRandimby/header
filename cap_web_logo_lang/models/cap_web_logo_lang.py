# -*- coding: utf-8 -*-
from odoo import fields, models


class WebsiteLogoLang(models.Model):
    _name = 'website.logo.lang'
    _description = 'Website Logo per Language'
    _order = 'website_id, sequence, id'

    website_id = fields.Many2one(
        'website', string='Website', required=True, ondelete='cascade', index=True)
    lang_id = fields.Many2one(
        'res.lang', string='Language', required=True, ondelete='cascade')
    # Plain Binary (not Image) so SVG files are stored as-is without raster processing.
    logo = fields.Binary(string='Logo', attachment=True, help='SVG, PNG or JPG accepted.')
    logo_filename = fields.Char(string='Logo Filename')
    sequence = fields.Integer(default=10)

    _unique_website_lang = models.Constraint(
        'unique(website_id, lang_id)',
        'A logo is already defined for this language on this website.')
