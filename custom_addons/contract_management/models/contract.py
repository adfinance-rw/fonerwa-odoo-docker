# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import time
import logging

_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _name = 'contract.management'
    _description = 'Contract Management'
    _order = 'create_date desc'

    # Note: We override search() method, not _search()
    # The _search() method should not be overridden as it's an internal method

    @api.model
    def _apply_ir_rules(self, query, mode='read'):
        """Override to bypass record rules for Contract Users so they see ALL contracts"""
        user = self.env.user
        has_contract_user = user.has_group('contract_management.group_contract_user')
        has_contract_manager = user.has_group('contract_management.group_contract_manager')
        has_contract_procurement = user.has_group('contract_management.group_contract_procurement')
        
        _logger.info('=' * 80)
        _logger.info('_apply_ir_rules CALLED')
        _logger.info('User: %s (ID: %s)', user.name, user.id)
        _logger.info('Mode: %s', mode)
        _logger.info('Has Contract User: %s', has_contract_user)
        _logger.info('Has Contract Manager: %s', has_contract_manager)
        _logger.info('Has Contract Procurement: %s', has_contract_procurement)
        _logger.info('Is Admin: %s', user._is_admin())
        
        # For Contract Users, bypass ALL record rules to see all contracts
        if mode == 'read' and has_contract_user:
            if not has_contract_manager and not has_contract_procurement:
                _logger.info('BYPASSING RECORD RULES for Contract User - returning query as-is')
                _logger.info('Query before bypass: %s', str(query)[:500])
                # Don't apply any record rules - return query as-is
                # This ensures Contract Users see ALL contracts
                result = query
                _logger.info('Query after bypass: %s', str(result)[:500])
                _logger.info('=' * 80)
                return result
        
        _logger.info('APPLYING NORMAL RECORD RULES')
        _logger.info('Query before applying rules: %s', str(query)[:500])
        
        # Log active rules that might affect this query
        try:
            rules = self.env['ir.rule'].sudo().search([
                ('model_id.model', '=', 'contract.management'),
                ('active', '=', True)
            ])
            _logger.info('Active record rules for contract.management: %s',
                        len(rules))
            for rule in rules:
                user_groups = set(user.groups_id.ids)
                rule_groups = set(rule.groups.ids) if rule.groups else set()
                applies = False
                if rule.groups:
                    # Rule applies if user has any of the rule's groups
                    applies = bool(user_groups & rule_groups)
                else:
                    # Global rule applies to everyone
                    applies = True
                
                _logger.info('  Rule: %s (ID: %s)', rule.name, rule.id)
                _logger.info('    Domain: %s', rule.domain_force)
                # Check if rule is global (no groups means global)
                is_global = not rule.groups
                _logger.info('    Global: %s', is_global)
                _logger.info('    Groups: %s', [g.name for g in rule.groups])
                _logger.info('    User Groups: %s',
                            [g.name for g in user.groups_id])
                _logger.info('    Applies to user: %s', applies)
                _logger.info('    Perm Read: %s, Write: %s, Create: %s, '
                           'Unlink: %s',
                           rule.perm_read, rule.perm_write, rule.perm_create,
                           rule.perm_unlink)
        except Exception as e:
            _logger.error('Error logging record rules: %s', str(e))
        
        result = super()._apply_ir_rules(query, mode)
        if result is None:
            _logger.warning('ACCESS DENIED: Query returned None after '
                          'applying rules')
            _logger.warning('This means record rules blocked access to '
                          'the contract(s)')
        else:
            _logger.info('Query after applying rules: %s',
                        str(result)[:500])
        _logger.info('=' * 80)
        return result
    
    @api.model
    def _log_active_record_rules(self):
        """Log all active record rules for contract.management model"""
        try:
            rules = self.env['ir.rule'].sudo().search([
                ('model_id.model', '=', 'contract.management'),
                ('active', '=', True)
            ])
            _logger.info('=' * 80)
            _logger.info('ACTIVE RECORD RULES for contract.management')
            _logger.info('Total active rules: %s', len(rules))
            for rule in rules:
                _logger.info('  Rule ID: %s', rule.id)
                _logger.info('    Name: %s', rule.name)
                _logger.info('    Domain: %s', rule.domain_force)
                # Check if rule is global (no groups means global)
                is_global = not rule.groups
                _logger.info('    Global: %s', is_global)
                _logger.info('    Groups: %s', [g.name for g in rule.groups])
                _logger.info('    Perm Read: %s, Write: %s, Create: %s, Unlink: %s', 
                           rule.perm_read, rule.perm_write, rule.perm_create, rule.perm_unlink)
            _logger.info('=' * 80)
        except Exception as e:
            _logger.error('Error logging record rules: %s', str(e))
    
    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """Override search to ensure Contract Users can see ALL contracts"""
        user = self.env.user
        has_contract_user = user.has_group('contract_management.group_contract_user')
        has_contract_manager = user.has_group('contract_management.group_contract_manager')
        has_contract_procurement = user.has_group('contract_management.group_contract_procurement')
        
        _logger.info('=' * 80)
        _logger.info('SEARCH METHOD CALLED')
        _logger.info('User: %s (ID: %s)', user.name, user.id)
        _logger.info('Is Admin: %s', user._is_admin())
        _logger.info('Has Contract User: %s', has_contract_user)
        _logger.info('Has Contract Manager: %s', has_contract_manager)
        _logger.info('Has Contract Procurement: %s', has_contract_procurement)
        _logger.info('Original Domain: %s', domain)
        _logger.info('Offset: %s, Limit: %s, Order: %s', offset, limit, order)
        
        # Log active record rules
        self._log_active_record_rules()
        
        # For Contract Users, ensure they see ALL contracts regardless of admin status
        if has_contract_user:
            if not has_contract_manager and not has_contract_procurement:
                # Remove create_uid filters from domain
                filtered_domain = []
                removed_filters = []
                for d in domain:
                    if isinstance(d, (list, tuple)) and len(d) == 3:
                        if d[0] == 'create_uid':
                            removed_filters.append(d)
                            _logger.info('REMOVED create_uid filter: %s', d)
                            continue
                    filtered_domain.append(d)
                domain = filtered_domain
                
                _logger.info('Filtered Domain (after removing create_uid): %s', domain)
                _logger.info('Removed %s create_uid filter(s)', len(removed_filters))
                
                # Search with current user - _apply_ir_rules override will bypass rules
                _logger.info('Calling super().search() - _apply_ir_rules will bypass rules')
                result = super().search(domain, offset=offset, limit=limit, order=order)
                _logger.info('Search Result: Found %s contract(s)', len(result))
                _logger.info('Contract IDs: %s', result.ids[:20] if len(result) > 20 else result.ids)
                _logger.info('=' * 80)
                return result
        
        _logger.info('Using normal search (not Contract User only)')
        result = super().search(domain, offset=offset, limit=limit, order=order)
        _logger.info('Search Result: Found %s contract(s)', len(result))
        _logger.info('Contract IDs: %s', result.ids[:20] if len(result) > 20 else result.ids)
        _logger.info('=' * 80)
        return result
    
    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """Override get_view (Odoo 18) to hide New button for Contract Users"""
        # ALWAYS log to verify method is called
        _logger.info('=' * 80)
        _logger.info('get_view CALLED (Odoo 18 method)')
        _logger.info('Model: %s, View Type: %s, User: %s (ID: %s)', 
                     self._name, view_type, self.env.user.name, self.env.user.id)
        _logger.info('View ID: %s, Options: %s', view_id, options)
        _logger.info('=' * 80)
        
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        
        # Also call fields_view_get for backward compatibility
        return self._modify_view_for_create_button(result, view_type)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """Override fields_view_get (legacy method) to hide New button for Contract Users"""
        # ALWAYS log to verify method is called
        _logger.info('=' * 80)
        _logger.info('fields_view_get CALLED (legacy method)')
        _logger.info('Model: %s, View Type: %s, User: %s (ID: %s)', 
                     self._name, view_type, self.env.user.name, self.env.user.id)
        _logger.info('View ID: %s, Toolbar: %s', view_id, toolbar)
        _logger.info('=' * 80)
        
        result = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return self._modify_view_for_create_button(result, view_type)
    
    def _modify_view_for_create_button(self, result, view_type):
        """Modify view XML to control New button visibility"""
        # Check if user is Contract User ONLY (without Manager/Procurement)
        has_contract_user = self.env.user.has_group('contract_management.group_contract_user')
        has_contract_manager = self.env.user.has_group('contract_management.group_contract_manager')
        has_contract_procurement = self.env.user.has_group('contract_management.group_contract_procurement')
        
        is_contract_user_only = has_contract_user and not has_contract_manager and not has_contract_procurement
        
        _logger.info('Group Check - User: %s, Contract User: %s, Manager: %s, Procurement: %s', 
                     self.env.user.name, has_contract_user, has_contract_manager, has_contract_procurement)
        _logger.info('is_contract_user_only: %s', is_contract_user_only)
        
        # Control New button visibility based on user groups
        if view_type in ('list', 'tree', 'form'):
            arch = result.get('arch', '')
            if arch:
                import re
                # Map view_type to XML tag name
                if view_type in ('list', 'tree'):
                    tag_name = 'list'
                else:
                    tag_name = 'form'
                
                # Determine create attribute value
                if is_contract_user_only:
                    # Contract User ONLY: Hide New button
                    create_value = '0'
                    _logger.info('HIDING NEW BUTTON for Contract User')
                elif has_contract_manager or has_contract_procurement:
                    # Contract Manager or Procurement: Show New button
                    create_value = '1'
                    _logger.info('SHOWING NEW BUTTON for Manager/Procurement')
                else:
                    # Other users: Keep default (usually hidden)
                    create_value = '0'
                    _logger.info('HIDING NEW BUTTON for other users')
                
                # Determine delete attribute value
                # Only Contract Procurement can delete contracts
                if has_contract_procurement:
                    delete_value = '1'
                    _logger.info('SHOWING DELETE OPTION for Procurement')
                else:
                    # Contract User and Contract Manager cannot delete
                    delete_value = '0'
                    _logger.info('HIDING DELETE OPTION for User/Manager')
                
                # Determine duplicate attribute value
                # Only Contract Procurement can duplicate contracts
                if has_contract_procurement:
                    duplicate_value = '1'
                    _logger.info('SHOWING DUPLICATE OPTION for Procurement')
                else:
                    # Contract User and Contract Manager cannot duplicate
                    duplicate_value = '0'
                    _logger.info('HIDING DUPLICATE OPTION for User/Manager')
                
                _logger.info('Setting create="%s", delete="%s", duplicate="%s" for %s view', 
                           create_value, delete_value, duplicate_value, tag_name)
                
                # FORCE remove ALL existing create, delete, and duplicate attributes
                # Match both numeric (0, 1) and boolean (true, false) values, with or without quotes
                # Be very aggressive - match any value after the equals sign until space or >
                arch = re.sub(
                    r'\s+create\s*=\s*["\']?[^"\'>\s]+["\']?',
                    '',
                    arch,
                    flags=re.IGNORECASE
                )
                arch = re.sub(
                    r'\s+delete\s*=\s*["\']?[^"\'>\s]+["\']?',
                    '',
                    arch,
                    flags=re.IGNORECASE
                )
                arch = re.sub(
                    r'\s+duplicate\s*=\s*["\']?[^"\'>\s]+["\']?',
                    '',
                    arch,
                    flags=re.IGNORECASE
                )
                
                # Find the opening tag and FORCE add create, delete, and duplicate attributes
                # Try multiple patterns to ensure we catch it
                attrs = f'create="{create_value}" delete="{delete_value}" duplicate="{duplicate_value}"'
                patterns = [
                    (r'(<' + tag_name + r')(\s+[^>]*?)(>)', 
                     r'\1\2 ' + attrs + r'\3'),  # With attributes
                    (r'(<' + tag_name + r')(\s+)(>)', 
                     r'\1\2' + attrs + r'\3'),  # With whitespace only
                    (r'(<' + tag_name + r')(>)', 
                     r'\1 ' + attrs + r'\2'),  # No attributes
                ]
                
                modified = False
                for pattern, replacement in patterns:
                    if re.search(pattern, arch):
                        arch = re.sub(pattern, replacement, arch, count=1)
                        modified = True
                        _logger.info('Pattern matched and replaced!')
                        break
                
                if modified:
                    result['arch'] = arch
                    # Double-check it's there
                    if (f'create="{create_value}"' in arch and 
                        f'delete="{delete_value}"' in arch and
                        f'duplicate="{duplicate_value}"' in arch):
                        _logger.info('SUCCESS: create="%s", delete="%s", duplicate="%s" added', 
                                   create_value, delete_value, duplicate_value)
                    else:
                        _logger.warning('ERROR: Attributes not found after modification!')
                        _logger.warning('Expected: create="%s", delete="%s", duplicate="%s"', 
                                      create_value, delete_value, duplicate_value)
                        _logger.warning('Arch after: %s', arch[:300])
                else:
                    _logger.warning('ERROR: Could not find %s tag to modify!', tag_name)
                    _logger.warning('Arch: %s', arch[:500])
        
        _logger.info('=' * 80)
        return result

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
        tracking=True,
        domain=[('is_contract', '=', True)],
        help='Select a contractor/vendor. Only partners marked as contractors/vendors are shown.'
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
        default=30,
        tracking=True,
        help='Number of days before expiry to start sending daily notification '
             'emails. Emails will be sent daily from this day until expiration '
             'date (default: 30 days)'
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
        default=lambda self: self.env.company.currency_id,
        domain=[('active', '=', True)],
        help='Select the currency for the contract value (RWF, USD, or EUR)'
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
    
    can_edit_as_manager = fields.Boolean(
        string='Can Edit as Manager',
        compute='_compute_can_edit_as_manager',
        store=False,
        help='True if current user is Contract Manager and is assigned as this contract\'s manager'
    )
    
    is_contract_user_only = fields.Boolean(
        string='Is Contract User Only',
        compute='_compute_is_contract_user_only',
        store=False,
        help='True if current user is Contract User but NOT Manager and NOT Procurement'
    )
    
    @api.depends('contract_manager_id')
    def _compute_can_edit_as_manager(self):
        """Compute if current user can edit as Contract Manager"""
        for contract in self:
            # Procurement users can always edit (full access)
            if self.env.user.has_group('contract_management.group_contract_procurement'):
                contract.can_edit_as_manager = True
            # Contract Manager users can only edit if they are the assigned Contract Manager
            elif self.env.user.has_group('contract_management.group_contract_manager'):
                contract.can_edit_as_manager = contract.contract_manager_id == self.env.user
            else:
                # Contract Users and others cannot edit
                contract.can_edit_as_manager = False
    
    @api.depends(lambda self: [])  # No field dependencies - depends on current user
    def _compute_is_contract_user_only(self):
        """Compute if current user is Contract User ONLY (without Manager/Procurement)"""
        has_contract_user = self.env.user.has_group('contract_management.group_contract_user')
        has_contract_manager = self.env.user.has_group('contract_management.group_contract_manager')
        has_contract_procurement = self.env.user.has_group('contract_management.group_contract_procurement')
        
        is_contract_user_only = has_contract_user and not has_contract_manager and not has_contract_procurement
        
        # Log for debugging
        _logger.info('Computing is_contract_user_only for user: %s', self.env.user.name)
        _logger.info('Has Contract User: %s, Manager: %s, Procurement: %s', 
                    has_contract_user, has_contract_manager, has_contract_procurement)
        _logger.info('is_contract_user_only = %s', is_contract_user_only)
        
        # Set for all records (this is a context-based field)
        for record in self:
            record.is_contract_user_only = is_contract_user_only
    
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
        """Override create to prevent Contract Users from creating contracts"""
        # Security check: Contract Users cannot create contracts
        # Button is visible but clicking it will show this error message
        # Check user groups explicitly
        has_contract_user = self.env.user.has_group('contract_management.group_contract_user')
        has_contract_manager = self.env.user.has_group('contract_management.group_contract_manager')
        has_contract_procurement = self.env.user.has_group('contract_management.group_contract_procurement')
        is_admin = self.env.user._is_admin()
        
        # Log for debugging
        _logger.info('=' * 60)
        _logger.info('CREATE METHOD CALLED')
        _logger.info('User: %s (ID: %s)', self.env.user.name, self.env.user.id)
        _logger.info('Is Admin: %s', is_admin)
        _logger.info('Has Contract User: %s', has_contract_user)
        _logger.info('Has Contract Manager: %s', has_contract_manager)
        _logger.info('Has Contract Procurement: %s', has_contract_procurement)
        _logger.info('=' * 60)
        
        # If user has Contract User group but NOT Manager and NOT Procurement, deny access
        # This applies even if user is admin (as per user requirement)
        if has_contract_user and not has_contract_manager and not has_contract_procurement:
            _logger.error('=' * 60)
            _logger.error('CREATE BLOCKED - Contract User attempted to create contract')
            _logger.error('User: %s (ID: %s) - BLOCKED', self.env.user.name, self.env.user.id)
            _logger.error('=' * 60)
            raise UserError(
                _('Access Denied!\n\n'
                  'You do not have permission to create contracts.\n\n'
                  'Only Contract Managers and Contract Procurement users can create contracts.\n\n'
                  'Please contact your administrator if you need to create a contract.')
            )
        
        _logger.info('CREATE ALLOWED - User has Manager or Procurement group')
        _logger.info('Proceeding with contract creation...')
        
        # Security check: Contract Managers can only assign themselves as Contract Manager
        if self.env.user.has_group('contract_management.group_contract_manager'):
            if not self.env.user.has_group('contract_management.group_contract_procurement'):
                if 'contract_manager_id' in vals and vals.get('contract_manager_id') != self.env.user.id:
                    raise UserError(
                        _('You can only assign yourself as the Contract Manager when creating contracts.')
                    )
                # Ensure contract_manager_id is set to current user if not provided
                if 'contract_manager_id' not in vals:
                    vals['contract_manager_id'] = self.env.user.id
        
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
        _logger.info('Calling super().create() now...')
        contract = super(Contract, self).create(vals)
        _logger.info('Contract created successfully: ID %s', contract.id)
        
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
        # Security check: Contract Managers can only edit contracts where they are the Contract Manager
        if self.env.user.has_group('contract_management.group_contract_manager'):
            if not self.env.user.has_group('contract_management.group_contract_procurement'):
                for contract in self:
                    if contract.contract_manager_id != self.env.user:
                        raise UserError(
                            _('You can only edit contracts where you are assigned as the Contract Manager. '
                              'Please contact a Contract Procurement user to '
                              'modify contracts assigned to other managers.')
                        )
                    # Prevent Contract Managers from changing contract_manager_id
                    if 'contract_manager_id' in vals and vals.get('contract_manager_id') != self.env.user.id:
                        raise UserError(
                            _('You cannot change the Contract Manager assignment. '
                              'Please contact a Contract Procurement user to reassign contracts.')
                        )
        
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
        
        # Security check: Contract Managers can only terminate contracts they manage
        if self.env.user.has_group('contract_management.group_contract_manager'):
            if not self.env.user.has_group('contract_management.group_contract_procurement'):
                if self.contract_manager_id != self.env.user:
                    raise UserError(
                        _('You can only terminate contracts where you are assigned as the Contract Manager. '
                          'Please contact a Contract Procurement user to '
                          'terminate contracts assigned to other managers.')
                    )
        
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
        
        # Security check: Contract Managers can only create amendments for contracts where they are the Contract Manager
        if self.env.user.has_group('contract_management.group_contract_manager'):
            if not self.env.user.has_group('contract_management.group_contract_procurement'):
                if self.contract_manager_id != self.env.user:
                    raise UserError(
                        _('You can only create amendments for contracts where you are assigned as the Contract Manager. '
                          'Please contact a Contract Procurement user to amend contracts assigned to other managers.')
                    )
        
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

    