# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, date


class HrFiscalYear(models.Model):
    _name = 'hr.fiscal.year'
    _description = 'HR Fiscal Year'
    _order = 'date_from desc'

    name = fields.Char(string='Fiscal Year Name', required=True)
    # code = fields.Char(string='Code', required=True)
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from >= record.date_to:
                raise ValidationError("Start date must be before end date.")
            
            # Check for overlapping fiscal years
            # Overlap if existing.start <= new.end AND existing.end >= new.start
            overlapping = self.search([
                ('id', '!=', record.id),
                '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from)
            ])
            if overlapping:
                raise ValidationError("Fiscal years cannot overlap.")
    
    @api.model
    def get_current_fiscal_year(self):
        """Get the current fiscal year"""
        current = self.search([('date_from', '<=', date.today()), ('date_to', '>=', date.today())], limit=1)
        if not current:
            # Try to find based on current date
            today = date.today()
            current = self.search([
                ('date_from', '<=', today),
                ('date_to', '>=', today)
            ], limit=1)
        return current
    
    @api.model
    def get_previous_fiscal_year(self):
        """Get the previous fiscal year"""
        current = self.get_current_fiscal_year()
        if current:
            previous = self.search([
                ('date_to', '<', current.date_from)
            ], order='date_to desc', limit=1)
            return previous
        return self.env['hr.fiscal.year']
    
    
    def action_view_appraisals(self):
        """View appraisals for this fiscal year"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Appraisals - {self.name}',
            'res_model': 'hr.appraisal',
            'view_mode': 'list,form',
            'domain': [('fiscal_year_id', '=', self.id)],
            'context': {'default_fiscal_year_id': self.id},
        }
    
    def action_view_objectives(self):
        """View objectives for this fiscal year"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Objectives - {self.name}',
            'res_model': 'hr.appraisal.goal',
            'view_mode': 'list,form',
            'domain': [('create_date', '>=', self.date_from), ('create_date', '<=', self.date_to)],
            'context': {},
        }
