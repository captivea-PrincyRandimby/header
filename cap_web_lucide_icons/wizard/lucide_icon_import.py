# -*- coding: utf-8 -*-
import re

from odoo import fields, models


class LucideIconImport(models.TransientModel):
    _name = 'lucide.icon.import'
    _description = 'Import Lucide Icons'

    names = fields.Text(
        string='Icon names', required=True,
        help='Comma / space / newline separated Lucide names (e.g. rocket, star, '
             'gauge). Browse names on https://lucide.dev/icons/.')

    def action_import(self):
        self.ensure_one()
        names = re.split(r'[\s,;]+', self.names or '')
        created = self.env['lucide.icon'].import_from_catalog(names)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lucide Icons',
            'res_model': 'lucide.icon',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', created.ids)] if created else [],
        }
