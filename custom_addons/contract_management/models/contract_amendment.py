# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
from datetime import datetime


class ContractAmendment(models.Model):
    _name = 'contract.management.amendment'
    _description = 'Contract Amendment'
    _order = 'amendment_date desc, version desc'
    _rec_name = 'display_name'

    # Amendment Information
    contract_id = fields.Many2one(
        'contract.management',
        string='Contract',
        required=True,
        ondelete='cascade'
    )
    
    version = fields.Char(
        string='Version',
        required=True,
        help='Version number (v1, v2, v3, etc.)'
    )
    
    amendment_date = fields.Datetime(
        string='Amendment Date',
        default=fields.Datetime.now,
        required=True
    )
    
    amended_by = fields.Many2one(
        'res.users',
        string='Amended By',
        default=lambda self: self.env.user,
        required=True
    )
    
    amendment_reason = fields.Text(
        string='Amendment Reason',
        help='Reason for this amendment'
    )
    
    amendment_type = fields.Selection([
        ('original', 'Original Contract'),
        ('amendment', 'Amendment'),
        ('correction', 'Correction')
    ], string='Amendment Type', default='amendment', required=True)
    
    # Display Name
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Amendment Status
    is_current = fields.Boolean(
        string='Current Version',
        default=False,
        help='True if this is the current active version'
    )
    
    # COMPLETE CONTRACT STRUCTURE - Same as contract.management
    # Basic Information
    name = fields.Char(
        string='Contract Title',
        required=True
    )
    
    contract_number = fields.Char(
        string='Contract ID',
        required=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contractor/Vendor',
        required=True
    )
    
    # Contract Classification
    contract_type_id = fields.Many2one(
        'contract.management.type',
        string='Type of Contract',
        required=True,
        default=lambda self: self.env.ref('contract_management.contract_type_contract', raise_if_not_found=False)
    )
    
    classification_ids = fields.Many2many(
        'contract.management.classification',
        'contract_amendment_classification_rel',
        'amendment_id',
        'classification_id',
        string='Classifications'
    )
    
    category_ids = fields.Many2many(
        'contract.management.category',
        'contract_amendment_category_rel',
        'amendment_id',
        'category_id',
        string='Categories'
    )
    
    department_ids = fields.Many2many(
        'contract.management.department',
        'contract_amendment_department_rel',
        'amendment_id',
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
    
    # Dates and Value
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
    
    # Status and Lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('renewed', 'Renewed'),
        ('terminated', 'Terminated'),
        ('archived', 'Archived')
    ], string='Status', default='draft')
    
    # Version Control
    version_number = fields.Char(
        string='Version Number',
        default='1.0'
    )
    
    # Document Management
    contract_documents = fields.Binary(
        string='Contract Document',
        help='Upload the main contract document'
    )
    
    contract_document_name = fields.Char(
        string='Contract Document Name'
    )
    
    contract_document_size = fields.Integer(
        string='Contract Document Size (bytes)'
    )
    
    # Additional Documents
    additional_documents = fields.Binary(
        string='Additional Documents',
        help='Upload additional supporting documents'
    )
    
    additional_document_name = fields.Char(
        string='Additional Document Name'
    )
    
    additional_document_size = fields.Integer(
        string='Additional Document Size (bytes)'
    )
    
    # Document Count for UI
    document_count = fields.Integer(
        string='Document Count'
    )
    
    # Compliance and Evidence
    compliance_notes = fields.Text(
        string='Compliance Notes'
    )
    
    # Additional Information
    description = fields.Text(
        string='Description'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    # Computed Fields
    days_to_expiry = fields.Integer(
        string='Days to Expiry'
    )
    
    is_expiring_soon = fields.Boolean(
        string='Expiring Soon'
    )

    @api.depends('contract_id', 'version', 'amendment_date')
    def _compute_display_name(self):
        for amendment in self:
            amendment.display_name = f"{amendment.contract_number} - {amendment.version} ({amendment.amendment_date.strftime('%Y-%m-%d %H:%M')})"

    def action_view_contract_data(self):
        """View the contract data for this amendment"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Contract Data - {self.version}',
            'res_model': 'contract.management.amendment',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('contract_management.view_contract_amendment_data_form').id,
            'target': 'new',
            'context': {'show_contract_data': True}
        }

    def action_compare_with_current(self):
        """Compare this amendment with current contract"""
        self.ensure_one()
        
        # Get current contract data
        current_data = self.contract_id.read()[0]
        
        # Create comparison wizard
        comparison_wizard = self.env['contract.amendment.comparison'].create({
            'contract_id': self.contract_id.id,
            'amendment_id': self.id,
            'current_data': json.dumps(current_data),
            'amendment_data': json.dumps(self.read()[0])
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Compare {self.version} with Current',
            'res_model': 'contract.amendment.comparison',
            'res_id': comparison_wizard.id,
            'view_mode': 'form',
            'target': 'new'
        }

    def action_restore_version(self):
        """Restore this version as current contract"""
        self.ensure_one()
        
        # Create new amendment for current data before restoring
        self.contract_id._create_amendment_record('correction', 'Restoring to previous version')
        
        # Prepare data for restoration (exclude amendment-specific fields)
        amendment_data = self.read()[0]
        exclude_fields = ['id', 'contract_id', 'version', 'amendment_date', 'amended_by', 
                         'amendment_reason', 'amendment_type', 'display_name', 'is_current',
                         'create_date', 'write_date', '__last_update']
        
        update_data = {}
        for field_name, value in amendment_data.items():
            if field_name not in exclude_fields and field_name in self.contract_id._fields:
                update_data[field_name] = value
        
        # Update contract with restored data
        self.contract_id.write(update_data)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Version Restored'),
                'message': _('Contract has been restored to version %s') % self.version,
                'type': 'success',
            }
        }

    @api.model
    def create(self, vals_list):
        """Override create to validate contract state"""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        
        for vals in vals_list:
            if 'contract_id' in vals:
                contract = self.env['contract.management'].browse(
                    vals['contract_id'])
                if contract.state == 'draft':
                    raise UserError(
                        _('Cannot add amendments to a contract in draft '
                          'state. Please activate the contract first.'))
        
        amendments = super().create(vals_list)
        
        # Double check contract state after creation
        for amendment in amendments:
            if amendment.contract_id.state == 'draft':
                raise UserError(
                    _('Cannot add amendments to a contract in draft state. '
                      'Please activate the contract first.'))
        
        return amendments


class ContractAmendmentComparison(models.TransientModel):
    _name = 'contract.amendment.comparison'
    _description = 'Contract Amendment Comparison'

    contract_id = fields.Many2one(
        'contract.management',
        string='Contract',
        required=True
    )
    
    amendment_id = fields.Many2one(
        'contract.management.amendment',
        string='Amendment',
        required=True
    )
    
    current_data = fields.Text(
        string='Current Data',
        readonly=True
    )
    
    amendment_data = fields.Text(
        string='Amendment Data',
        readonly=True
    )
    
    comparison_result = fields.Html(
        string='Comparison Result',
        compute='_compute_comparison_result'
    )

    @api.depends('current_data', 'amendment_data')
    def _compute_comparison_result(self):
        for record in self:
            if not record.current_data or not record.amendment_data:
                record.comparison_result = '<p>No data available for comparison.</p>'
                return
            
            try:
                current = json.loads(record.current_data)
                amendment = json.loads(record.amendment_data)
                
                html = '<table class="table table-bordered"><thead><tr><th>Field</th><th>Current Value</th><th>Amendment Value</th><th>Status</th></tr></thead><tbody>'
                
                all_fields = set(current.keys()) | set(amendment.keys())
                
                for field in sorted(all_fields):
                    current_val = current.get(field, 'N/A')
                    amendment_val = amendment.get(field, 'N/A')
                    
                    if current_val != amendment_val:
                        status = '<span class="badge badge-warning">Changed</span>'
                        current_val = f'<span style="color: red;">{current_val}</span>'
                        amendment_val = f'<span style="color: green;">{amendment_val}</span>'
                    else:
                        status = '<span class="badge badge-success">Same</span>'
                    
                    html += f'<tr><td>{field}</td><td>{current_val}</td><td>{amendment_val}</td><td>{status}</td></tr>'
                
                html += '</tbody></table>'
                record.comparison_result = html
                
            except Exception as e:
                record.comparison_result = f'<p>Error comparing data: {str(e)}</p>'
