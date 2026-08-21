# -*- coding: utf-8 -*-
from odoo import fields, models


class QuoteTag(models.Model):
    _name = 'quote.tag'
    _description = 'Testimonial Tag'
    _order = 'name'

    name = fields.Char(string='Name', required=True, translate=True)
    color = fields.Integer(string='Color')

    _name_uniq = models.Constraint('unique(name)', 'This tag already exists.')


class QuoteTestimonial(models.Model):
    _name = 'quote.testimonial'
    _description = 'Quote / Testimonial'
    _inherit = ['website.published.multi.mixin']
    _order = 'sequence, id desc'

    name = fields.Char(string='Name', required=True,
                       help='Internal label, only used in the backend.')
    sequence = fields.Integer(default=10)
    author = fields.Char(string='Author')
    role = fields.Char(
        string='Role', translate=True,
        help="Free text, as it should read under the author's name: "
             "CFO, Operations Director, Head of IT…")
    company_name = fields.Char(string='Company Name')
    partner_id = fields.Many2one(
        'res.partner', string='Customer contact',
        help='Link to the customer contact to relate the online customer '
             'reference page (used when that contact is published).')
    quote = fields.Text(string='Quote', required=True, translate=True)
    # Testimonials keep their own tag list (quote.tag): expertise, industry,
    # country and role. Customer references use the partner website tags and the
    # blog uses blog.tag - three lists, because the three objects are not tagged
    # by the same people nor with the same granularity.
    tag_ids = fields.Many2many('quote.tag', string='Tags')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    # website_id / is_published / website_published / can_publish come from the mixin.
