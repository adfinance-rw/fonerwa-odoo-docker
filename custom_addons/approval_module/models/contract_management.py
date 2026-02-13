# -*- coding: utf-8 -*-

from odoo import api, models


class ContractManagement(models.Model):
    _inherit = 'contract.management'

    def name_get(self):
        """Show partner (contractor/vendor) name so dropdown and selection show who the contract is with."""
        return [(r.id, r.partner_id.name or r.name or '') for r in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Dropdown: return partner name as display; search still matches contract name and partner name."""
        res = super().name_search(name, args or [], operator, limit)
        if not res:
            return res
        ids = [r[0] for r in res]
        records = self.browse(ids)
        return [(r.id, r.partner_id.name or r.name or '') for r in records]
