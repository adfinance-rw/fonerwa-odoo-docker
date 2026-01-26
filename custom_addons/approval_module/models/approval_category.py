# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'
        
    # Notification Configuration
    notification_user_ids = fields.Many2many(
        'res.users',
        'approval_category_notification_rel',
        'category_id',
        'user_id',
        string='Notify on Approval',
        help='Users who will be notified when requests in this category are fully approved'
    )
    
    # Withdrawal Prevention
    prevent_withdrawal_after_approval = fields.Boolean(
        string='Prevent Withdrawal After Final Approval',
        default=False,
        help='Prevent users from canceling the request after it has been fully approved'
    )
    
    # Sequential Approval
    approver_sequence = fields.Boolean(
        string='Require Sequential Approval',
        default=False,
        help='If checked, approvers must approve in sequence. Previous approvers must approve before later ones can approve.'
    )

    # Department restriction (optional)
    department_ids = fields.Many2many(
        'hr.department',
        'approval_category_department_rel',
        'category_id',
        'department_id',
        string='Departments',
        help='If set, only users in these departments can see this approval category.'
    )

    # Templates configured on the category
    checklist_template_ids = fields.One2many(
        comodel_name='approval.category.checklist',
        inverse_name='category_id',
        string='Checklist Templates'
    )
    approver_template_ids = fields.One2many(
        comodel_name='approval.category.approver.template',
        inverse_name='category_id',
        string='Approver Templates'
    )

    # Contract enforcement flags
    requires_contract = fields.Boolean(
        string='Requires Contract',
        help='If checked, requests in this category must reference a valid contract.'
    )
    require_unexpired_contract = fields.Boolean(
        string='Require Unexpired Contract',
        default=True,
        help='Block requests if the selected contract is expired.'
    )
    match_partner = fields.Boolean(
        string='Match Request Partner',
        help='Enforce that the request partner matches the contract partner.'
    )
    require_contract_document = fields.Boolean(
        string='Require Contract Document Upload',
        help='Ensure at least one checklist attachment is uploaded as contract evidence.'
    )

    # Description structure configuration
    description_show_subject = fields.Boolean(
        string='Show Subject Section',
        default=False,
        help='Enable Subject field in the Description section'
    )

    # Default number of days before Approval activities are due
    approval_deadline_days = fields.Integer(
        string='Approval Activity Deadline (days)',
        default=2,
        help='Number of days from assignment until an Approval activity is due for this category.'
    )
    description_show_background = fields.Boolean(
        string='Show Background Section',
        default=False,
        help='Enable Background field in the Description section'
    )
    description_show_budget_line = fields.Boolean(
        string='Show Budget Line Section',
        default=False,
        help='Enable Budget Line field in the Description section'
    )
    description_show_contract_price = fields.Boolean(
        string='Show Contract Price Section',
        default=False,
        help='Enable Contract Price table in the Description section'
    )
    
    # Available type options for this approval category
    available_type_ids = fields.One2many(
        comodel_name='approval.category.available.type',
        inverse_name='category_id',
        string='Available Type Options',
        help='Define which specific type options are available for requests in this category'
    )

    # Computed field for available type option IDs (used in domains)
    available_type_option_ids = fields.Many2many(
        'approval.type.option',
        compute='_compute_available_type_option_ids',
        string='Available Type Options',
        help='Computed list of available type options for filtering'
    )

    @api.depends('available_type_ids.type_option_id')
    def _compute_available_type_option_ids(self):
        """Compute which specific type options are available based on available_type_ids"""
        for rec in self:
            option_ids = rec.available_type_ids.mapped('type_option_id').ids
            rec.available_type_option_ids = [(6, 0, option_ids)]

    def _compute_request_to_validate_count(self):
        # Count only requests where the current user still has a pending approver line
        domain = [('user_has_pending', '=', True)]
        requests_data = self.env['approval.request']._read_group(domain, ['category_id'], ['__count'])
        requests_mapped_data = {category.id: count for category, count in requests_data}
        for category in self:
            category.request_to_validate_count = requests_mapped_data.get(category.id, 0)


class ApprovalCategoryAvailableType(models.Model):
    """Defines which specific types are available for a memo category"""
    _name = 'approval.category.available.type'
    _description = 'Approval Category Available Type'
    _order = 'sequence asc, id asc'

    category_id = fields.Many2one(
        'approval.category',
        required=True,
        ondelete='cascade',
        string='Approval Category'
    )
    
    # Generic type option selection
    type_option_id = fields.Many2one(
        'approval.type.option',
        string='Type Option',
        required=True,
        ondelete='cascade',
        help='Select or create a type option'
    )
    
    sequence = fields.Integer(default=10)

    @api.constrains('category_id', 'type_option_id')
    def _check_no_duplicate_types(self):
        """Prevent duplicate types in the same category"""
        for rec in self:
            if not rec.type_option_id:
                continue
            
            duplicates = self.search([
                ('category_id', '=', rec.category_id.id),
                ('type_option_id', '=', rec.type_option_id.id),
                ('id', '!=', rec.id)
            ])
            if duplicates:
                raise ValidationError(_('This type option is already added to the available types.'))

    @api.model
    def default_get(self, fields_list):
        """Set default category_id from context"""
        res = super().default_get(fields_list)
        if 'default_category_id' in self.env.context:
            res['category_id'] = self.env.context['default_category_id']
        return res

    @api.onchange('category_id')
    def _onchange_category_id(self):
        """Clear type option when category changes"""
        self.type_option_id = False
        # Type options are now independent, no domain filtering needed
        return {'domain': {'type_option_id': []}}

    def name_get(self):
        """Display the selected type option name"""
        result = []
        for rec in self:
            name = rec.type_option_id.name if rec.type_option_id else _('(Not Set)')
            result.append((rec.id, name))
        return result


class ApprovalCategoryChecklist(models.Model):
    _name = 'approval.category.checklist'
    _description = 'Approval Category Checklist Template'

    category_id = fields.Many2one('approval.category', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    is_required = fields.Boolean(default=True)
    require_after_approval = fields.Boolean(
        string='Require After Approval',
        default=False,
        help='If checked, this checklist item must be completed after all approvers have approved. '
             'The request will be returned to the requester if this item is missing after approval.'
    )
    
    # Thresholds
    po_amount_operator = fields.Selection(
        selection=[('gt','>'), ('ge','≥'), ('lt','<'), ('le','≤'), ('eq','=')],
        string='Amount Operator'
    )
    po_amount = fields.Monetary(string='Amount', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='category_id.company_id.currency_id', readonly=True)

    # Applicability by type options - generic approach
    type_option_ids = fields.Many2many(
        comodel_name='approval.type.option',
        relation='approval_category_checklist_type_option_rel',
        column1='checklist_id', column2='type_option_id',
        string='Type Options',
        help='This checklist applies to these type options. Leave empty to apply to all types in the category.'
    )

class ApprovalCategoryApprover(models.Model):
    _name = 'approval.category.approver.template'
    _description = 'Approval Category Approver Template'
    _order = 'sequence asc, id asc'

    category_id = fields.Many2one('approval.category', required=True, ondelete='cascade')
    user_ids = fields.Many2many(
        'res.users',
        'approval_category_approver_user_rel',
        'approver_id',
        'user_id',
        string='Users',
        required=True,
        help='Users who will be added as approvers based on this template'
    )
    role = fields.Selection([
        ('reviewer', 'Reviewer (Line Manager)'),
        ('cfo', 'CFO'),
        ('senior', 'CEO Office (Pre-authorization)'),
        ('ceo', 'CEO'),
    ], required=False, help='Deprecated: Use Users field instead')
    required = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    
    # Thresholds
    po_amount_operator = fields.Selection(
        selection=[('gt','>'), ('ge','≥'), ('lt','<'), ('le','≤'), ('eq','=')],
        string='Amount Operator'
    )
    po_amount = fields.Monetary(string='Amount', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='category_id.company_id.currency_id', readonly=True)

    # Applicability by type options - generic approach
    type_option_ids = fields.Many2many(
        comodel_name='approval.type.option',
        relation='approval_category_approver_type_option_rel',
        column1='approver_id', column2='type_option_id',
        string='Applicable Type Options',
        help='This approver applies to these type options. Leave empty to apply to all types in the category.'
    )

class ApprovalTypeOption(models.Model):
    """Generic Type Options - can be used across different approval categories"""
    _name = 'approval.type.option'
    _description = 'Approval Type Option'
    _order = 'sequence asc, name asc, id asc'

    name = fields.Char(required=True, string='Option Name')
    code = fields.Char(index=True, string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')

    @api.model
    def create(self, vals):
        """Auto-generate code from name"""
        if 'name' in vals:
            vals['code'] = vals['name'].lower().replace(' ', '_').replace('-', '_')
        return super().create(vals)
    
    def write(self, vals):
        """Auto-update code when name changes"""
        if 'name' in vals:
            vals['code'] = vals['name'].lower().replace(' ', '_').replace('-', '_')
        return super().write(vals)
    
    def name_get(self):
        """Display name"""
        result = []
        for rec in self:
            result.append((rec.id, rec.name))
        return result