# -*- coding: utf-8 -*-
from odoo import fields, models


class QuoteRole(models.Model):
    _name = 'quote.role'
    _description = 'Testimonial Role'
    _order = 'name'

    name = fields.Char(string='Role', required=True, translate=True)

    _name_uniq = models.Constraint('unique(name)', 'This role already exists.')


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
    role_id = fields.Many2one('quote.role', string='Role')
    company_name = fields.Char(string='Company Name')
    partner_id = fields.Many2one(
        'res.partner', string='Customer contact',
        help='Link to the customer contact to relate the online customer '
             'reference page (used when that contact is published).')
    quote = fields.Text(string='Quote', required=True, translate=True)
    tag_ids = fields.Many2many('quote.tag', string='Tags')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    # website_id / is_published / website_published / can_publish come from the mixin.
