# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ContractAmendmentWizard(models.TransientModel):
    _name = 'contract.amendment.wizard'
    _description = 'Contract Amendment Wizard'

    contract_id = fields.Many2one(
        'contract.management',
        string='Contract',
        required=True
    )
    
    amendment_reason = fields.Text(
        string='Amendment Reason',
        required=True,
        help='Reason for this amendment'
    )
    
    # Contract Fields - Same as contract.management
    name = fields.Char(
        string='Contract Title',
        required=True
    )
    
    contract_number = fields.Char(
        string='Contract ID',
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contractor/Vendor',
        required=True
    )
    
    contract_type_id = fields.Many2one(
        'contract.management.type',
        string='Type of Contract',
        required=True,
        default=lambda self: self.env.ref('contract_management.contract_type_contract', raise_if_not_found=False)
    )
    
    classification_ids = fields.Many2many(
        'contract.management.classification',
        'contract_amendment_wizard_classification_rel',
        'wizard_id',
        'classification_id',
        string='Classifications'
    )
    
    category_ids = fields.Many2many(
        'contract.management.category',
        'contract_amendment_wizard_category_rel',
        'wizard_id',
        'category_id',
        string='Categories'
    )
    
    department_ids = fields.Many2many(
        'contract.management.department',
        'contract_amendment_wizard_department_rel',
        'wizard_id',
        'department_id',
        string='Departments'
    )
    
    facility_project = fields.Char(
        string='Facility/Project'
    )

    contract_manager_id = fields.Many2one(
        'res.users',
        string='Contract Manager'
    )
    
    effective_date = fields.Date(
        string='Effective Date',
        required=True
    )
    
    expiry_date = fields.Date(
        string='Expiry Date',
        required=True
    )
    
    notice_period_days = fields.Integer(
        string='Expiration notice (Days)',
        default=30
    )
    
    contract_value = fields.Monetary(
        string='Contract Value',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency'
    )

    
    version_number = fields.Char(
        string='Version Number',
        default='1.0'
    )
    
    contract_documents = fields.Binary(
        string='Contract Document',
        help='Upload the main contract document'
    )
    
    contract_document_name = fields.Char(
        string='Contract Document Name'
    )
    
    additional_documents = fields.Binary(
        string='Additional Documents',
        help='Upload additional supporting documents'
    )
    
    additional_document_name = fields.Char(
        string='Additional Document Name'
    )
    
    compliance_notes = fields.Text(
        string='Compliance Notes'
    )
    
    description = fields.Text(
        string='Description'
    )
    
    notes = fields.Text(
        string='Notes'
    )

    @api.model
    def default_get(self, fields_list):
        """Load current contract data into wizard"""
        res = super().default_get(fields_list)
        
        if self.env.context.get('active_model') == 'contract.management' and self.env.context.get('active_id'):
            contract = self.env['contract.management'].browse(self.env.context['active_id'])
            
            # Load all contract fields into wizard
            contract_data = contract.read()[0]
            
            for field_name, value in contract_data.items():
                if field_name in fields_list and field_name not in ['id', 'create_date', 'write_date', '__last_update']:
                    field = self._fields.get(field_name)
                    if field and field.type == 'many2many' and isinstance(value, list):
                        res[field_name] = [(6, 0, value)]
                    else:
                        res[field_name] = value
            
            res['contract_id'] = contract.id
        
        return res

    def action_create_amendment(self):
        """Create amendment and update contract"""
        self.ensure_one()
        
        if not self.amendment_reason:
            raise UserError(_('Please provide a reason for this amendment.'))
        
        # Prepare update data - only copy fields that exist in contract model
        contract_fields = set(self.contract_id._fields.keys())
        
        update_data = {}
        for field_name, value in self.read()[0].items():
            if (field_name in contract_fields and 
                field_name not in ['id', 'contract_id', 'amendment_reason', 'create_date', 'write_date', '__last_update']):
                # Handle Many2one fields - extract ID from tuple
                field = self._fields.get(field_name)
                if isinstance(value, tuple) and len(value) == 2 and field.type == 'many2one':
                    update_data[field_name] = value[0]  # Extract ID from (id, name)
                elif isinstance(value, list) and field and field.type == 'many2many':
                    update_data[field_name] = [(6, 0, value)]
                else:
                    update_data[field_name] = value
        
        # Update contract with new data, pass context to trigger amendment creation
        self.contract_id.with_context(
            create_amendment=True,
            amendment_type='amendment',
            amendment_reason=self.amendment_reason
        ).write(update_data)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Amendment Created'),
                'message': _('Contract has been successfully amended. Previous version saved as amendment.'),
                'type': 'success',
            }
        }

    def action_cancel(self):
        """Cancel amendment creation"""
        return {'type': 'ir.actions.act_window_close'}
