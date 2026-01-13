# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import time


class Contract(models.Model):
    _name = 'contract.management'
    _description = 'Contract Management'
    _order = 'create_date desc'

    # Basic Information
    name = fields.Char(
        string='Contract Title',
        required=True,
        tracking=True
    )
    
    contract_number = fields.Char(
        string='Contract ID',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contractor/Vendor',
        required=True,
        tracking=True
    )
    
    # Contract Classification (UR-02)
    contract_type_id = fields.Many2one(
        'contract.management.type',
        string='Type of Contract',
        required=True,
        default=lambda self: self.env.ref('contract_management.contract_type_contract', raise_if_not_found=False),
        tracking=True
    )
    
    classification_ids = fields.Many2many(
        'contract.management.classification',
        'contract_classification_rel',
        'contract_id',
        'classification_id',
        string='Classifications',
        required=True,
        tracking=True
    )
    
    category_ids = fields.Many2many(
        'contract.management.category',
        'contract_category_rel',
        'contract_id',
        'category_id',
        string='Categories',
        required=True,
        tracking=True
    )
    
    department_ids = fields.Many2many(
        'contract.management.department',
        'contract_department_rel',
        'contract_id',
        'department_id',
        string='Departments',
        required=True,
        tracking=True
    )
    
    classification_display = fields.Char(
        string='Classifications',
        compute='_compute_configuration_display'
    )
    
    category_display = fields.Char(
        string='Categories',
        compute='_compute_configuration_display'
    )
    
    department_display = fields.Char(
        string='Departments',
        compute='_compute_configuration_display'
    )
    
    facility_project = fields.Char(
        string='Facility/Project',
        tracking=True
    )

    contract_manager_id = fields.Many2one(
        'res.users',
        string='Contract Manager',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    # Dates and Value
    effective_date = fields.Date(
        string='Effective Date',
        required=True,
        tracking=True
    )
    
    expiry_date = fields.Date(
        string='Expiry Date',
        required=True,
        tracking=True
    )
    
    notice_period_days = fields.Integer(
        string='Expiration notice (Days)',
        default=7,
        tracking=True,
        help='Number of days before expiry to start sending daily notification '
             'emails. Emails will be sent daily from this day until expiration '
             'date (default: 7 days)'
    )
    
    expiration_notification_sent = fields.Boolean(
        string='Expiration Notification Sent',
        default=False,
        help='Indicates if expiration notification email has been sent'
    )
    
    last_notification_date = fields.Datetime(
        string='Last Notification Date',
        help='Date and time when the last expiration notification email was sent'
    )
    
    send_recurring_reminders = fields.Boolean(
        string='Send Recurring Reminders',
        default=True,
        help='Send daily reminder emails when contract is within the notice '
             'period. Emails will be sent daily until expiration date.'
    )
    
    contract_value = fields.Monetary(
        string='Contract Value',
        currency_field='currency_id',
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Status and Lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
        ('archived', 'Archived')
    ], string='Status', default='draft', tracking=True)
    
    # Version Control (UR-04)
    version = fields.Char(
        string='Version',
        default='v1',
        tracking=True
    )

    
    # Document Management (UR-01, UR-04) - Direct to Contract
    # Contract Documents
    contract_documents = fields.Binary(
        string='Contract Document',
        help='Upload the main contract document'
    )
    
    contract_document_name = fields.Char(
        string='Contract Document Name'
    )
    
    contract_document_size = fields.Integer(
        string='Contract Document Size (bytes)',
        compute='_compute_contract_document_size'
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
        string='Additional Document Size (bytes)',
        compute='_compute_additional_document_size'
    )
    
    # Document Count for UI
    document_count = fields.Integer(
        string='Document Count',
        compute='_compute_document_count'
    )
    
    # Enhanced Deliverable Management (UR-06)
    deliverable_ids = fields.One2many(
        'contract.deliverable',
        'contract_id',
        string='Deliverables'
    )
    
    deliverable_count = fields.Integer(
        string='Deliverable Count',
        compute='_compute_deliverable_count'
    )
    
    overdue_deliverable_count = fields.Integer(
        string='Overdue Deliverables',
        compute='_compute_overdue_deliverable_count'
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
        string='Days to Expiry',
        compute='_compute_days_to_expiry',
        search='_search_days_to_expiry'
    )
    
    is_expiring_soon = fields.Boolean(
        string='Expiring Soon',
        compute='_compute_is_expiring_soon'
    )
    
    # Amendment Tracking (UR-04)
    amendment_ids = fields.One2many(
        'contract.management.amendment',
        'contract_id',
        string='Amendments',
        context={'create': False}  # Disable direct creation
    )
    
    amendment_count = fields.Integer(
        string='Amendment Count',
        compute='_compute_amendment_count'
    )
    
    current_version = fields.Char(
        string='Current Version',
        compute='_compute_current_version'
    )
    
    # Termination Information
    termination_date = fields.Date(
        string='Termination Date',
        default=fields.Date.today,
        tracking=True
    )
    
    termination_reason = fields.Text(
        string='Termination Reason',
        tracking=True
    )
    
    termination_document = fields.Binary(
        string='Termination Document',
        tracking=True
    )
    
    termination_document_name = fields.Char(
        string='Termination Document Name'
    )
    
    terminated_by = fields.Many2one(
        'res.users',
        string='Terminated By',
        tracking=True
    )

    # Performance Guaranty Management
    performance_guaranty_ids = fields.One2many(
        'contract.performance.guaranty',
        'contract_id',
        string='Performance Guaranties',
        context={'create': True}
    )
    
    performance_guaranty_count = fields.Integer(
        string='Performance Guaranty Count',
        compute='_compute_performance_guaranty_count'
    )

    @api.depends('contract_documents')
    def _compute_contract_document_size(self):
        for contract in self:
            if contract.contract_documents:
                contract.contract_document_size = len(contract.contract_documents) * 3 / 4
            else:
                contract.contract_document_size = 0

    @api.depends('additional_documents')
    def _compute_additional_document_size(self):
        for contract in self:
            if contract.additional_documents:
                contract.additional_document_size = len(contract.additional_documents) * 3 / 4
            else:
                contract.additional_document_size = 0

    @api.depends('contract_documents', 'additional_documents')
    def _compute_document_count(self):
        for contract in self:
            count = 0
            if contract.contract_documents:
                count += 1
            if contract.additional_documents:
                count += 1
            contract.document_count = count

    @api.depends('deliverable_ids')
    def _compute_deliverable_count(self):
        for contract in self:
            contract.deliverable_count = len(contract.deliverable_ids)
    
    @api.depends('amendment_ids')
    def _compute_amendment_count(self):
        for contract in self:
            contract.amendment_count = len(contract.amendment_ids)
    
    @api.depends('amendment_ids', 'amendment_ids.version')
    def _compute_current_version(self):
        for contract in self:
            if contract.amendment_ids:
                # Get the highest version number
                versions = []
                for amendment in contract.amendment_ids:
                    if amendment.version and amendment.version.startswith('v'):
                        try:
                            version_num = int(amendment.version[1:])
                            versions.append(version_num)
                        except ValueError:
                            continue
                if versions:
                    contract.current_version = f"v{max(versions)}"
                else:
                    contract.current_version = "v1"
            else:
                contract.current_version = "v1"

    @api.depends('deliverable_ids', 'deliverable_ids.is_overdue')
    def _compute_overdue_deliverable_count(self):
        for contract in self:
            contract.overdue_deliverable_count = len(
                contract.deliverable_ids.filtered('is_overdue'))

    def _compute_days_to_expiry(self):
        today = fields.Date.today()
        for contract in self:
            if contract.expiry_date:
                contract.days_to_expiry = (contract.expiry_date - today).days
            else:
                contract.days_to_expiry = 0

    def _search_days_to_expiry(self, operator, value):
        """Search method for days_to_expiry computed field"""
        today = fields.Date.today()
        if operator == '<':
            # Find contracts expiring in less than value days
            # i.e., days_to_expiry < value means expiry_date - today < value
            # so expiry_date < today + timedelta(days=value)
            target_date = today + timedelta(days=value)
            return [('expiry_date', '<', target_date)]
        elif operator == '>':
            # Find contracts expiring in more than value days
            target_date = today + timedelta(days=value)
            return [('expiry_date', '>', target_date)]
        elif operator in ['<=', '>=']:
            # Handle <= and >= operators
            target_date = today + timedelta(days=value)
            op = '<=' if operator == '<=' else '>='
            return [('expiry_date', op, target_date)]
        elif operator == '=':
            # Find contracts expiring on exactly value days from now
            target_date = today + timedelta(days=value)
            return [('expiry_date', '=', target_date)]
        else:
            return [('id', 'in', [])]

    def _compute_is_expiring_soon(self):
        """Compute if contract is expiring soon (within 30 days)"""
        today = fields.Date.today()
        for contract in self:
            if contract.expiry_date and contract.state == 'active':
                days_to_expiry = (contract.expiry_date - today).days
                contract.is_expiring_soon = 0 <= days_to_expiry <= 30
            else:
                contract.is_expiring_soon = False

    @api.depends('performance_guaranty_ids')
    def _compute_performance_guaranty_count(self):
        """Compute performance guaranty count"""
        for contract in self:
            contract.performance_guaranty_count = len(contract.performance_guaranty_ids)

    @api.depends('classification_ids', 'category_ids', 'department_ids')
    def _compute_configuration_display(self):
        for contract in self:
            contract.classification_display = ", ".join(contract.classification_ids.mapped('name'))
            contract.category_display = ", ".join(contract.category_ids.mapped('name'))
            contract.department_display = ", ".join(contract.department_ids.mapped('name'))

    @api.onchange('contract_type_id')
    def _onchange_contract_type_id(self):
        """Clear and filter classifications, categories, and departments when contract type changes"""
        if self.contract_type_id:
            # Filter to only show options related to selected contract type
            self.classification_ids = self.classification_ids.filtered(
                lambda c: self.contract_type_id in c.contract_type_ids
            )
            self.category_ids = self.category_ids.filtered(
                lambda c: self.contract_type_id in c.contract_type_ids
            )
            self.department_ids = self.department_ids.filtered(
                lambda d: self.contract_type_id in d.contract_type_ids
            )
        else:
            # If no contract type selected, clear all
            self.classification_ids = False
            self.category_ids = False
            self.department_ids = False

    @api.constrains('classification_ids', 'category_ids', 'contract_type_id')
    def _check_configuration_requirements(self):
        for contract in self:
            if not contract.classification_ids:
                raise ValidationError(_('Please select at least one classification.'))
            if not contract.category_ids:
                raise ValidationError(_('Please select at least one category.'))
            # Validate that selected options match the contract type
            if contract.contract_type_id:
                invalid_classifications = contract.classification_ids.filtered(
                    lambda c: contract.contract_type_id not in c.contract_type_ids
                )
                if invalid_classifications:
                    raise ValidationError(
                        _('Classification "%s" is not valid for contract type "%s".') %
                        (invalid_classifications[0].name, contract.contract_type_id.name)
                    )
                invalid_categories = contract.category_ids.filtered(
                    lambda c: contract.contract_type_id not in c.contract_type_ids
                )
                if invalid_categories:
                    raise ValidationError(
                        _('Category "%s" is not valid for contract type "%s".') %
                        (invalid_categories[0].name, contract.contract_type_id.name)
                    )
                invalid_departments = contract.department_ids.filtered(
                    lambda d: contract.contract_type_id not in d.contract_type_ids
                )
                if invalid_departments:
                    raise ValidationError(
                        _('Department "%s" is not valid for contract type "%s".') %
                        (invalid_departments[0].name, contract.contract_type_id.name)
                    )

    def _check_automatic_expiration(self):
        """Check if contract should be automatically expired"""
        today = fields.Date.today()
        if (self.state == 'active' and 
            self.expiry_date and 
            self.expiry_date < today):
            
            # Update contract state to expired without creating amendment (avoid recursion)
            self.with_context(skip_amendment=True).write({'state': 'expired'})
            
            return True
        return False

    @api.model
    def create(self, vals):
        # Always assign contract number during creation
        if not vals.get('contract_number') or vals.get('contract_number') == _('New'):
            sequence = self.env['ir.sequence'].search([('code', '=', 'contract.management')])
            if not sequence:
                # Find the maximum existing contract number
                existing_contracts = self.search([('contract_number', '!=', 'New'), ('contract_number', '!=', False)])
                max_number = 0
                
                for contract in existing_contracts:
                    if contract.contract_number and contract.contract_number.startswith('CON'):
                        try:
                            # Extract number from CON0001 format
                            number_part = contract.contract_number[3:]  # Remove 'CON' prefix
                            number = int(number_part)
                            max_number = max(max_number, number)
                        except (ValueError, IndexError):
                            continue
                
                # Create sequence starting from max_number + 1
                sequence = self.env['ir.sequence'].create({
                    'name': 'Contract Management',
                    'code': 'contract.management',
                    'prefix': 'CON',
                    'padding': 4,
                    'number_next': max_number + 1,
                    'number_increment': 1,
                })
            
            # Get next sequence number
            vals['contract_number'] = sequence.next_by_code('contract.management') or _('New')
        
        # Validate contract value (amount)
        contract_value = vals.get('contract_value', 0)
        if not contract_value or contract_value <= 0:
            raise UserError(_('Contract Value is required and must be greater than zero.'))
        
        # Validate contract document
        if not vals.get('contract_documents'):
            raise UserError(_('Contract Document is required. Please upload the contract document.'))
        
        # Create the contract
        contract = super(Contract, self).create(vals)
        
        return contract
    
    def read(self, fields=None, load='_classic_read'):
        """Override read to check for automatic expiration"""
        result = super().read(fields, load)
        
        # Check for automatic expiration for each contract (unless explicitly skipped)
        skip_expiration_check = self.env.context.get('skip_expiration_check', False)
        if not skip_expiration_check:
            for contract in self:
                contract._check_automatic_expiration()
        
        return result

    def action_activate(self):
        # Ensure contract has a proper number before activation
        if self.contract_number == 'New':
            sequence = self.env['ir.sequence'].search([('code', '=', 'contract.management')])
            if not sequence:
                # Find the maximum existing contract number
                existing_contracts = self.search([('contract_number', '!=', 'New'), ('contract_number', '!=', False)])
                max_number = 0
                
                for contract in existing_contracts:
                    if contract.contract_number and contract.contract_number.startswith('CON'):
                        try:
                            # Extract number from CON0001 format
                            number_part = contract.contract_number[3:]  # Remove 'CON' prefix
                            number = int(number_part)
                            max_number = max(max_number, number)
                        except (ValueError, IndexError):
                            continue
                
                # Create sequence starting from max_number + 1
                sequence = self.env['ir.sequence'].create({
                    'name': 'Contract Management',
                    'code': 'contract.management',
                    'prefix': 'CON',
                    'padding': 4,
                    'number_next': max_number + 1,
                    'number_increment': 1,
                })
            
            # Assign contract number
            new_number = sequence.next_by_code('contract.management')
            self.write({'contract_number': new_number})
        
        self.write({'state': 'active'})

    def action_expire(self):
        self.write({'state': 'expired'})


    def write(self, vals):
        """Override write to handle amendment tracking and validate
        deliverables"""
        # Validate deliverables amounts if contract value is being changed
        if 'contract_value' in vals:
            for contract in self:
                total_deliverable_amount = sum(
                    d.payment_amount or 0
                    for d in contract.deliverable_ids
                )
                new_contract_value = (
                    vals.get('contract_value', contract.contract_value) or 0)
                
                if total_deliverable_amount > new_contract_value:
                    raise UserError(
                        _('Cannot set contract value to %.2f. The sum of all '
                          'deliverable amounts (%.2f) exceeds this value. '
                          'Please adjust the deliverable amounts first.')
                        % (new_contract_value, total_deliverable_amount))
        
        # Only create amendment if explicitly requested via context (from wizard)
        create_amendment = self.env.context.get('create_amendment', False)
        
        if create_amendment:
            for contract in self:
                # Get the amendment details from context
                amendment_type = self.env.context.get('amendment_type', 'amendment')
                change_summary = self.env.context.get('amendment_reason', 
                                                      'Contract data updated')
                amendment, next_version = contract._create_amendment_record(amendment_type, change_summary)
                
                # Update the contract version to the next version
                vals['version'] = next_version
        
        return super().write(vals)

    def _create_amendment_record(self, amendment_type='amendment', change_summary=''):
        """Create an amendment record before updating contract data"""
        for contract in self:
            # Get current contract data (skip automatic expiration check to avoid recursion)
            current_data = contract.with_context(skip_expiration_check=True).read()[0]
            
            # Get current contract version (this will be stored in the amendment)
            current_contract_version = contract.version or 'v1'
            
            # Normalize current version to v1 format if it's in old format (1.0)
            if current_contract_version and current_contract_version.replace('.', '').isdigit():
                # Convert '1.0' to 'v1'
                version_num = current_contract_version.split('.')[0]
                current_contract_version = f"v{version_num}"
            elif not current_contract_version or not current_contract_version.startswith('v'):
                current_contract_version = 'v1'
            
            # Parse current version to determine next version
            if current_contract_version.startswith('v'):
                try:
                    version_num = int(current_contract_version[1:])
                    next_version = f"v{version_num + 1}"
                except ValueError:
                    next_version = "v2"
            else:
                # Default case - should not happen but just in case
                next_version = "v2"
            
            # Prepare amendment data with all contract fields
            amendment_data = {
                'contract_id': contract.id,
                'version': current_contract_version,  # Store the CURRENT contract version
                'amendment_type': amendment_type,
                'amendment_reason': change_summary,
                'amended_by': self.env.user.id,
                'amendment_date': fields.Datetime.now(),
                'is_current': False,  # Will be updated after the contract is updated
            }
            
            # Copy only fields that exist in the amendment model
            amendment_model = self.env['contract.management.amendment']
            amendment_fields = set(amendment_model._fields.keys())
            
            for field_name, value in current_data.items():
                if field_name in amendment_fields and field_name not in ['id', 'create_date', 'write_date', '__last_update']:
                    # Handle Many2one fields - extract ID from tuple
                    if isinstance(value, tuple) and len(value) == 2:
                        amendment_data[field_name] = value[0]  # Extract ID from (id, name) tuple
                    else:
                        amendment_data[field_name] = value
            
            # Create the amendment record
            amendment = self.env['contract.management.amendment'].create(amendment_data)
            
            # Mark previous amendments as not current
            contract.amendment_ids.write({'is_current': False})
            
            return amendment, next_version  # Return next version to update contract

    def action_create_amendment(self):
        """Open amendment creation wizard"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Amendment'),
            'res_model': 'contract.amendment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'contract.management',
                'active_id': self.id,
                'default_contract_id': self.id,
            }
        }



    def action_terminate(self):
        """Open termination wizard"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Terminate Contract'),
            'res_model': 'contract.termination.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'contract.management',
                'active_id': self.id,
                'default_contract_id': self.id,
            }
        }

    def action_archive(self):
        self.write({'state': 'archived'})

    def action_fix_contract_numbers(self):
        """Fix contracts that have 'New' as contract number"""
        contracts_with_new = self.search([('contract_number', '=', 'New')])
        
        # Get or create sequence
        sequence = self.env['ir.sequence'].search([('code', '=', 'contract.management')])
        if not sequence:
            # Find the maximum existing contract number
            existing_contracts = self.search([('contract_number', '!=', 'New'), ('contract_number', '!=', False)])
            max_number = 0
            
            for contract in existing_contracts:
                if contract.contract_number.startswith('CON'):
                    try:
                        # Extract number from CON0001 format
                        number_part = contract.contract_number[3:]  # Remove 'CON' prefix
                        number = int(number_part)
                        max_number = max(max_number, number)
                    except (ValueError, IndexError):
                        continue
            
            # Create sequence starting from max_number + 1
            sequence = self.env['ir.sequence'].create({
                'name': 'Contract Management',
                'code': 'contract.management',
                'prefix': 'CON',
                'padding': 4,
                'number_next': max_number + 1,
                'number_increment': 1,
            })
        else:
            # Update existing sequence to continue from max existing number
            existing_contracts = self.search([('contract_number', '!=', 'New'), ('contract_number', '!=', False)])
            max_number = 0
            
            for contract in existing_contracts:
                if contract.contract_number.startswith('CON'):
                    try:
                        # Extract number from CON0001 format
                        number_part = contract.contract_number[3:]  # Remove 'CON' prefix
                        number = int(number_part)
                        max_number = max(max_number, number)
                    except (ValueError, IndexError):
                        continue
            
            # Update sequence to continue from max existing number
            sequence.write({'number_next': max_number + 1})
        
        # Fix contracts with 'New' numbers
        for contract in contracts_with_new:
            # Assign next sequence number
            new_number = sequence.next_by_code('contract.management')
            contract.write({'contract_number': new_number})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Contract Numbers Fixed',
                'message': f'Fixed {len(contracts_with_new)} contracts with proper sequence numbers. Sequence now starts from {sequence.number_next}.',
                'type': 'success',
            }
        }


    def action_download_contract_document(self):
        """Download main contract document"""
        if not self.contract_documents:
            raise UserError(_('No contract document available for download.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=contract.management&id={self.id}&field=contract_documents&filename_field=contract_document_name&download=true',
            'target': 'self',
        }

    def action_download_additional_document(self):
        """Download additional document"""
        if not self.additional_documents:
            raise UserError(_('No additional document available for download.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=contract.management&id={self.id}&field=additional_documents&filename_field=additional_document_name&download=true',
            'target': 'self',
        }

    def action_view_deliverables(self):
        """View contract deliverables"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contract Deliverables',
            'res_model': 'contract.deliverable',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }


    def action_archive_wizard(self):
        """Open archive wizard (UR-13)"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Archive Contract',
            'res_model': 'contract.archive.wizard',
            'view_mode': 'form',
            'context': {'default_contract_ids': [(6, 0, [self.id])]},
            'target': 'new',
        }

    def action_view_contract(self):
        """View the contract from amendment list"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'View Contract',
            'res_model': 'contract.management',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_send_deliverable_alerts(self):
        """Send alerts for upcoming deliverables (UR-05)"""
        today = fields.Date.today()
        upcoming_deliverables = self.deliverable_ids.filtered(
            lambda d: (d.status == 'pending' and 
                      d.deliverable_date >= today and 
                      d.deliverable_date <= today + timedelta(
                          days=d.alert_days_before) and
                      not d.alert_sent)
        )
        
        for deliverable in upcoming_deliverables:
            deliverable.action_send_alert()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Deliverable Alerts',
                'message': f'Alerts sent for {len(upcoming_deliverables)} '
                           f'upcoming deliverables.',
                'type': 'success',
            }
        }

    def action_create_amendment_from_line(self):
        """Handle 'Add a line' action for amendment_ids field"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Amendment'),
            'res_model': 'contract.amendment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'contract.management',
                'active_id': self.id,
                'default_contract_id': self.id,
            }
        }

    def send_expiration_notification(self, force_send=True):
        """Send email notification when contract is about to expire"""
        self.ensure_one()
        import logging
        _logger = logging.getLogger(__name__)
        
        if not self.contract_manager_id:
            _logger.warning(
                'Contract %s: No contract manager assigned',
                self.contract_number or 'N/A'
            )
            return False
        
        if not self.contract_manager_id.email:
            _logger.warning(
                'Contract %s: Contract manager %s has no email address',
                self.contract_number or 'N/A',
                self.contract_manager_id.name
            )
            return False
        
        _logger.info(
            'Contract %s: Attempting to send notification to %s',
            self.contract_number or 'N/A',
            self.contract_manager_id.email
        )
        
        # Get email template
        template = self.env.ref(
            'contract_management.email_template_contract_expiration', False)
        if not template:
            _logger.warning(
                'Contract %s: Email template not found, using fallback',
                self.contract_number or 'N/A'
            )
            # Fallback: send email manually if template doesn't exist
            result = self._send_expiration_email_manual()
        else:
            _logger.info(
                'Contract %s: Using email template %s',
                self.contract_number or 'N/A',
                template.name
            )
            # Use email template
            try:
                # Check mail server configuration before sending
                mail_server = self.env['ir.mail_server'].search([('active', '=', True)], limit=1)
                if not mail_server:
                    _logger.warning(
                        'Contract %s: No active mail server configured. Email will be queued but may not be sent.',
                        self.contract_number or 'N/A'
                    )
                    _logger.warning(
                        'Please configure an outgoing mail server at: Settings > Technical > Outgoing Mail Servers'
                    )
                
                # Manually render template and create mail record with explicit recipients
                # This ensures template variables are properly replaced
                try:
                    # First, try to render the template to verify it works
                    # This way we don't create an email that needs to be deleted
                    records = self.browse([self.id])
                    
                    # Try rendering the template fields
                    try:
                        rendered_subject = template._render_template(
                            template.subject, self._name, records.ids
                        )[self.id]
                        
                        # Check if rendering worked - if placeholders still present, use fallback
                        if '${object.' in rendered_subject:
                            _logger.warning(
                                'Contract %s: Template rendering failed - placeholders in subject. Using fallback method.',
                                self.contract_number or 'N/A'
                            )
                            result = self._send_expiration_email_manual()
                            return result
                        
                        # Rendering worked, now render body and email_from
                        rendered_body = template._render_template(
                            template.body_html, self._name, records.ids
                        )[self.id]
                        rendered_from = template._render_template(
                            template.email_from or '', self._name, records.ids
                        ).get(self.id, '')
                        
                        _logger.info(
                            'Contract %s: Template rendered successfully - Subject: %s',
                            self.contract_number or 'N/A',
                            rendered_subject[:100] if rendered_subject else 'None'
                        )
                        
                        # Create mail.mail record with rendered content and explicit recipients
                        mail = self.env['mail.mail'].create({
                            'subject': rendered_subject,
                            'body_html': rendered_body,
                            'email_from': rendered_from or False,
                            'email_to': self.contract_manager_id.email,
                            'partner_ids': [(6, 0, [self.contract_manager_id.id])],
                            'model': self._name,
                            'res_id': self.id,
                            'auto_delete': template.auto_delete,
                        })
                        
                        _logger.info(
                            'Contract %s: Email created with rendered template (ID: %s, To: %s)',
                            self.contract_number or 'N/A',
                            mail.id,
                            self.contract_manager_id.email
                        )
                        
                        # Send the email if requested
                        if force_send:
                            mail.send()
                            
                    except Exception as render_error:
                        _logger.error(
                            'Contract %s: Template rendering error: %s. Using fallback method.',
                            self.contract_number or 'N/A',
                            str(render_error)
                        )
                        result = self._send_expiration_email_manual()
                        return result
                    
                    # Wait a moment and check the mail state
                    time.sleep(0.5)  # Small delay to allow processing
                    
                    # Refresh and check mail state (re-browse to get fresh data)
                    mail.invalidate_recordset()
                    mail = self.env['mail.mail'].browse(mail.id)
                    if not mail.exists():
                        _logger.warning(
                            'Contract %s: Email record was auto-deleted. This may indicate it was sent successfully.',
                            self.contract_number or 'N/A'
                        )
                        result = True  # Assume success if auto-deleted
                    else:
                        _logger.info(
                            'Contract %s: Email state: %s, Recipients: %s, Failure: %s',
                            self.contract_number or 'N/A',
                            mail.state,
                            mail.email_to or 'None',
                            mail.failure_reason or 'None'
                        )
                        
                        if mail.state == 'exception':
                            _logger.error(
                                'Contract %s: Email failed to send. State: %s, Reason: %s',
                                self.contract_number or 'N/A',
                                mail.state,
                                mail.failure_reason or 'Unknown error'
                            )
                            result = False
                        elif mail.state in ('sent', 'outgoing'):
                            _logger.info(
                                'Contract %s: Email queued/sent successfully (State: %s)',
                                self.contract_number or 'N/A',
                                mail.state
                            )
                            result = True
                        else:
                            _logger.warning(
                                'Contract %s: Email in unexpected state: %s',
                                self.contract_number or 'N/A',
                                mail.state
                            )
                            result = True  # Still consider it queued
                            
                except Exception as template_error:
                    _logger.error(
                        'Contract %s: Failed to send email via template: %s',
                        self.contract_number or 'N/A',
                        str(template_error),
                        exc_info=True
                    )
                    # Don't use fallback to avoid duplicate emails
                    # The email was likely already created, just log the error
                    result = False
                    return result
                    
            except Exception as e:
                _logger.error(
                    'Contract %s: Failed to send email via template: %s',
                    self.contract_number or 'N/A',
                    str(e),
                    exc_info=True
                )
                result = False
        
        if result:
            # Mark notification as sent and update last notification date
            self.write({
                'expiration_notification_sent': True,
                'last_notification_date': fields.Datetime.now()
            })
            _logger.info(
                'Contract %s: Notification marked as sent',
                self.contract_number or 'N/A'
            )
        
        return result

    def _send_expiration_email_manual(self):
        """Send expiration email manually if template is not available"""
        self.ensure_one()

        if not self.contract_manager_id or not \
                self.contract_manager_id.email:
            return False

        # Prepare email content
        subject = _('Contract Expiration Notice: %s') % self.name
        expiry_date_str = (
            self.expiry_date.strftime('%Y-%m-%d')
            if self.expiry_date else 'N/A'
        )
        partner_name = (
            self.partner_id.name if self.partner_id else 'N/A'
        )
        currency_name = (
            self.currency_id.name if self.currency_id else ''
        )
        body_html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2 style="color: #875A7B;">Contract Expiration Notice</h2>
            <p>Dear {self.contract_manager_id.name},</p>
            <p>This is to notify you that the following contract is
            expiring soon:</p>
            <table style="border-collapse: collapse; width: 100%;
            margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Contract Number:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {self.contract_number or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Contract Title:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {self.name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Contractor/Vendor:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {partner_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Expiry Date:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    color: #d9534f; font-weight: bold;">
                    {expiry_date_str}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Days to Expiry:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    color: #d9534f; font-weight: bold;">
                    {self.days_to_expiry} days</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Contract Value:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {self.contract_value or 0.0} {currency_name}</td>
                </tr>
            </table>
            <p style="color: #d9534f; font-weight: bold;">Please take
            necessary action to renew or extend this contract before it
            expires.</p>
            <p>Best regards,<br/>Contract Management System</p>
        </div>
        """
        
        # Create and send mail
        mail_values = {
            'subject': subject,
            'body_html': body_html,
            'email_to': self.contract_manager_id.email,
            'email_from': self.env.user.email or self.env.company.email,
            'model': self._name,
            'res_id': self.id,
        }
        
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()
        
        return True

    