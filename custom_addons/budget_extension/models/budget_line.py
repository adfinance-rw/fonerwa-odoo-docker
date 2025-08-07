# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class BudgetLine(models.Model):
    """Extend Budget Line with Budgetary Activity and IFMIS Mapping"""
    _inherit = 'budget.line'

    # NEW FIELDS - Main requirement
    budget_activity_id = fields.Many2one(
        'budget.activity',
        string='Budgetary Activity',
        help="Classification of this budget line by activity type"
    )
    ifmis_mapping_id = fields.Many2one(
        'ifmis.mapping',
        string='IFMIS Mapping',
        help="Mapping to IFMIS (Integrated Financial Management Information System)"
    )
    
    # Related fields for easier access and reporting
    budget_activity_code = fields.Char(related='budget_activity_id.code', string='Activity Code', readonly=True, store=True)
    budget_activity_name = fields.Char(related='budget_activity_id.name', string='Activity Name', readonly=True, store=True)
    ifmis_code = fields.Char(related='ifmis_mapping_id.ifmis_code', string='IFMIS Code', readonly=True, store=True)
    ifmis_category = fields.Selection(related='ifmis_mapping_id.ifmis_category', string='IFMIS Category', readonly=True, store=True)

    @api.onchange('budget_activity_id')
    def _onchange_budget_activity_id(self):
        if self.budget_activity_id and not self.budget_activity_id.active:
            return {
                'warning': {
                    'title': 'Inactive Activity',
                    'message': f'The selected budgetary activity "{self.budget_activity_id.name}" is inactive.'
                }
            }

    @api.onchange('ifmis_mapping_id')
    def _onchange_ifmis_mapping_id(self):
        if self.ifmis_mapping_id and not self.ifmis_mapping_id.active:
            return {
                'warning': {
                    'title': 'Inactive IFMIS Mapping',
                    'message': f'The selected IFMIS mapping "{self.ifmis_mapping_id.name}" is inactive.'
                }
            }

    def action_view_activity(self):
        """Action to view the related budget activity"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Budget Activity',
            'view_mode': 'form',
            'res_model': 'budget.activity',
            'res_id': self.budget_activity_id.id,
            'target': 'current',
        }

    def action_view_ifmis_mapping(self):
        """Action to view the related IFMIS mapping"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'IFMIS Mapping',
            'view_mode': 'form',
            'res_model': 'ifmis.mapping',
            'res_id': self.ifmis_mapping_id.id,
            'target': 'current',
        } 