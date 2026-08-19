# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models
from odoo.tools import file_open


class LucideIcon(models.Model):
    _name = 'lucide.icon'
    _description = 'Lucide Icon'
    _order = 'sequence, name'

    name = fields.Char(required=True, help='Lucide icon slug, e.g. "rocket".')
    svg = fields.Text(required=True, help='Inner SVG markup (paths) of the icon.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint('unique(name)', 'This Lucide icon already exists.')

    @api.model
    def _load_catalog(self):
        """Full Lucide catalog {name: inner_svg} bundled with the module."""
        try:
            with file_open('cap_web_lucide_icons/data/lucide_catalog.json', 'r') as fh:
                return json.load(fh)
        except Exception:
            return {}

    @api.model
    def get_catalog_names(self):
        """All Lucide names available for import (for autocomplete/reference)."""
        return sorted(self._load_catalog().keys())

    @api.model
    def import_from_catalog(self, names):
        """Create lucide.icon records for the given catalog names (skips unknown
        and already-existing ones). Returns the created recordset."""
        catalog = self._load_catalog()
        created = self.browse()
        existing = set(self.with_context(active_test=False).search([]).mapped('name'))
        for raw in names:
            key = (raw or '').strip().lower()
            if not key or key not in catalog or key in existing:
                continue
            created |= self.create({'name': key, 'svg': catalog[key]})
            existing.add(key)
        return created
