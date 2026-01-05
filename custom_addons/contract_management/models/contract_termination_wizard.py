# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ContractTerminationWizard(models.TransientModel):
    _name = 'contract.termination.wizard'
    _description = 'Contract Termination Wizard'

    contract_id = fields.Many2one(
        'contract.management',
        string='Contract',
        required=True
    )
    
    termination_date = fields.Date(
        string='Termination Date',
        default=fields.Date.today,
        required=True
    )
    
    termination_reason = fields.Text(
        string='Termination Reason',
        required=True,
        help='Reason for terminating this contract'
    )
    
    termination_document = fields.Binary(
        string='Termination Document',
        help='Upload termination document if available'
    )
    
    termination_document_name = fields.Char(
        string='Termination Document Name'
    )
    
    terminated_by = fields.Many2one(
        'res.users',
        string='Terminated By',
        default=lambda self: self.env.user,
        required=True
    )

    @api.model
    def default_get(self, fields_list):
        """Load contract data into wizard"""
        res = super().default_get(fields_list)
        
        if (self.env.context.get('active_model') == 'contract.management' and
                self.env.context.get('active_id')):
            contract = self.env['contract.management'].browse(
                self.env.context['active_id'])
            res['contract_id'] = contract.id
            
            # Pre-fill termination date with today
            if 'termination_date' in fields_list:
                res['termination_date'] = fields.Date.today()
        
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically terminate contract on save"""
        records = super().create(vals_list)
        
        for record in records:
            # Validate required fields
            if not record.termination_reason:
                raise UserError(
                    _('Please provide a reason for terminating this '
                      'contract.'))
            
            # Terminate the contract
            record.contract_id.write({
                'state': 'terminated',
                'termination_date': record.termination_date,
                'termination_reason': record.termination_reason,
                'termination_document': record.termination_document,
                'termination_document_name': record.termination_document_name,
                'terminated_by': record.terminated_by.id,
            })
        
        return records

    def write(self, vals):
        """Override write to handle updates and auto-terminate if needed"""
        result = super().write(vals)
        
        # If this is an update to an existing wizard record,
        # terminate the contract
        for record in self:
            if (record.contract_id and
                    record.contract_id.state != 'terminated'):
                if not record.termination_reason:
                    raise UserError(
                        _('Please provide a reason for terminating this '
                          'contract.'))
                
                record.contract_id.write({
                    'state': 'terminated',
                    'termination_date': record.termination_date,
                    'termination_reason': record.termination_reason,
                    'termination_document': record.termination_document,
                    'termination_document_name': (
                        record.termination_document_name),
                    'terminated_by': record.terminated_by.id,
                })
        
        return result

