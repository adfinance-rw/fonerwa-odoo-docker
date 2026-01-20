# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError
from datetime import timedelta


class ApprovalRequest(models.Model):

    _inherit = "approval.request"
    _order = 'create_date desc, id desc'  # NEW: Order by request time (most recent first)
    
    # Display fields to show approval roles clearly
    cfo_approver_id = fields.Many2one(
        'approval.approver', 
        string='CFO Approval',
        compute='_compute_role_approvers',
        help='Chief Finance Officer approval status'
    )
    senior_approver_id = fields.Many2one(
        'approval.approver',
        string='CEO office approver', 
        compute='_compute_role_approvers',
        help='Senior Approver/Deputy CEO pre-authorization status'
    )
    ceo_approver_id = fields.Many2one(
        'approval.approver',
        string='CEO Authorization', 
        compute='_compute_role_approvers',
        help='Chief Executive Officer authorization status'
    )
    reviewer_approver_id = fields.Many2one(
        'approval.approver',
        string='Department Manager Review',
        compute='_compute_role_approvers',
        help='Department Manager/Line Manager review status'
    )
    delegate_user_ids = fields.Many2many(
        'res.users',
        string='Delegates',
        compute='_compute_delegate_user_ids',
        help='Users who can approve on behalf of approvers via delegation'
    )

    @api.depends_context('uid')
    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        """
        Make approvals resilient when the same user appears on multiple approver lines.

        Standard Odoo (approvals) assumes a single approver line per user and does:
            approver_ids.filtered(...).status
        which crashes with:
            ValueError: Expected singleton: approval.approver(x, y)

        This can legitimately happen in our setup when a delegate is assigned for multiple approvers
        on the same request (delegate user becomes the approver on multiple lines).
        """
        current_user = self.env.user
        for approval in self:
            lines = approval.approver_ids.filtered(lambda a: a.user_id == current_user)
            if not lines:
                approval.user_status = False
                continue

            # If multiple lines exist, pick the most restrictive / actionable status for UI.
            statuses = set(lines.mapped('status'))
            if 'pending' in statuses:
                approval.user_status = 'pending'
            elif 'waiting' in statuses:
                approval.user_status = 'waiting'
            elif 'refused' in statuses:
                approval.user_status = 'refused'
            elif 'cancel' in statuses:
                approval.user_status = 'cancel'
            elif 'approved' in statuses:
                approval.user_status = 'approved'
            elif 'new' in statuses:
                approval.user_status = 'new'
            else:
                # fallback for any unexpected values
                approval.user_status = next(iter(statuses))
    
    # Computed & stored field to identify category type based on category name
    category_type = fields.Selection(
        selection=[
            ('purchase_order', 'Purchase Order'),
            ('invoice_payment', 'Invoice Payment'),
            ('other_payment', 'Other Payment'),
        ],
        string='Category Type',
        compute='_compute_category_type',
        store=True,
        help='Identifies if category is purchase_order, invoice_payment, or other_payment'
    )
    
    @api.depends('category_id', 'category_id.name')
    def _compute_category_type(self):
        """Identify category type based on category name (stored for search/domains)."""
        for request in self:
            if not request.category_id:
                request.category_type = False
                continue
            
            category_name = request.category_id.name.lower()
            
            # Identify based on category name keywords
            if 'purchase' in category_name or 'po' in category_name:
                request.category_type = 'purchase_order'
            elif 'invoice' in category_name:
                request.category_type = 'invoice_payment'
            elif 'payment' in category_name or 'disbursement' in category_name or 'mission' in category_name:
                request.category_type = 'other_payment'
            else:
                request.category_type = False
    
    @api.depends('amount')
    def _compute_po_thresholds(self):
        """Auto-compute PO threshold checkboxes based on amount."""
        for request in self:
            amount = request.amount or 0
            request.po_exceeds_10m = amount > 10000000
            request.po_exceeds_20m = amount > 20000000
    
    @api.depends('approver_ids', 'approver_ids.user_id', 'approver_ids.status')
    def _compute_role_approvers(self):
        """Compute which approver corresponds to which role (CFO, Senior Approver, CEO, Reviewer)"""
        for request in self:
            cfo = request.company_id.cfo_id if hasattr(request.company_id, 'cfo_id') else False
            senior_approver = request.company_id.senior_approver_id if hasattr(request.company_id, 'senior_approver_id') else False
            ceo = request.company_id.ceo_id if hasattr(request.company_id, 'ceo_id') else False
            
            # Find reviewer (line manager or department manager)
            requester = request.request_owner_id or request.create_uid
            dept_manager_user = False
            try:
                emp = requester.employee_id if hasattr(requester, 'employee_id') else False
                dept = emp.department_id if emp and hasattr(emp, 'department_id') else False
                manager = dept.manager_id if dept and hasattr(dept, 'manager_id') else False
                dept_manager_user = manager.user_id if manager and hasattr(manager, 'user_id') else False
            except Exception:
                dept_manager_user = False
            # Fallback to the employee's direct manager (parent_id.user_id) when no department manager
            parent_manager_user = False
            try:
                parent = emp and hasattr(emp, 'parent_id') and emp.parent_id or False
                parent_manager_user = parent and hasattr(parent, 'user_id') and parent.user_id or False
            except Exception:
                parent_manager_user = False
            reviewer = parent_manager_user or dept_manager_user
            
            # Find corresponding approver records
            request.cfo_approver_id = request.approver_ids.filtered(lambda a: cfo and a.user_id.id == cfo.id)[:1] if cfo else False
            request.senior_approver_id = request.approver_ids.filtered(lambda a: senior_approver and a.user_id.id == senior_approver.id)[:1] if senior_approver else False
            request.ceo_approver_id = request.approver_ids.filtered(lambda a: ceo and a.user_id.id == ceo.id)[:1] if ceo else False
            request.reviewer_approver_id = request.approver_ids.filtered(lambda a: reviewer and a.user_id.id == reviewer.id)[:1] if reviewer else False
    
    @api.depends('approver_ids', 'approver_ids.user_id', 'approver_ids.status', 'category_id')
    def _compute_delegate_user_ids(self):
        """Compute users who can approve via delegation for pending approvers"""
        for request in self:
            delegate_users = self.env['res.users']
            if request.approver_ids:
                delegation_model = self.env['approval.delegation']
                category_id = request.category_id.id if request.category_id else None
                for approver in request.approver_ids.filtered(lambda a: a.status == 'pending' and a.user_id):
                    delegation = delegation_model.get_active_delegation(
                        approver.user_id.id,
                        category_id
                    )
                    if delegation:
                        delegate_users |= delegation.delegate_id
            request.delegate_user_ids = delegate_users
    
    # Generic type option field (replaces payment_kind_id and purchase_kind_id)
    type_option_id = fields.Many2one(
        'approval.type.option',
        string='Type',
        help='Select the type option based on the category configuration'
    )

    # Backward-compatibility fields for other modules expecting legacy names
    invoice_payment_type = fields.Char(
        string='Payment Type (Invoice)',
        compute='_compute_legacy_types',
        inverse='_inverse_legacy_types',
        store=False
    )
    other_payment_type = fields.Char(
        string='Payment Type (Other)',
        compute='_compute_legacy_types',
        inverse='_inverse_legacy_types',
        store=False
    )
    purchase_type = fields.Char(
        string='Purchase Type',
        compute='_compute_legacy_types',
        inverse='_inverse_legacy_types',
        store=False
    )

    def _compute_legacy_types(self):
        """Compute legacy type fields from generic type_option_id"""
        for rec in self:
            code = rec.type_option_id and rec.type_option_id.code or False
            if rec.category_type == 'invoice_payment':
                rec.invoice_payment_type = code
                rec.other_payment_type = False
                rec.purchase_type = False
            elif rec.category_type == 'other_payment':
                rec.other_payment_type = code
                rec.invoice_payment_type = False
                rec.purchase_type = False
            elif rec.category_type == 'purchase_order':
                rec.purchase_type = code
                rec.invoice_payment_type = False
                rec.other_payment_type = False
            else:
                rec.invoice_payment_type = False
                rec.other_payment_type = False
                rec.purchase_type = False

    def _inverse_legacy_types(self):
        """Map legacy type fields back to generic type_option_id by code"""
        for rec in self:
            desired_code = rec.invoice_payment_type or rec.other_payment_type or rec.purchase_type
            if desired_code:
                # Find the type option by code
                option = self.env['approval.type.option'].search([
                    ('code', '=', desired_code)
                ], limit=1)
                rec.type_option_id = option

    po_exceeds_10m = fields.Boolean(
        string='Exceeds 10 million',
        compute='_compute_po_thresholds',
        store=True,
        help='Automatically checked when amount exceeds 10,000,000'
    )
    po_exceeds_20m = fields.Boolean(
        string='Exceeds 20 million (Guarantee Required)',
        compute='_compute_po_thresholds',
        store=True,
        help='Automatically checked when amount exceeds 20,000,000'
    )

    # Contract linkage
    category_requires_contract = fields.Boolean(
        related='category_id.requires_contract',
        string='Requires Contract',
        readonly=True,
        store=False
    )
    category_require_unexpired_contract = fields.Boolean(
        related='category_id.require_unexpired_contract',
        string='Require Active Contract',
        readonly=True,
        store=False
    )
    
    # Amount requirement
    category_has_amount = fields.Selection(
        related='category_id.has_amount',
        string='Amount Requirement',
        readonly=True,
        store=False
    )
    
    # Sequential approval requirement
    category_approver_sequence = fields.Boolean(
        related='category_id.approver_sequence',
        string='Require Sequential Approval',
        readonly=True,
        store=False
    )
    
    # Override approval_minimum to auto-calculate from required approvers
    approval_minimum = fields.Integer(
        string='Minimum Approvals',
        compute='_compute_approval_minimum',
        store=True,
        help='Automatically calculated as the count of required approvers'
    )
    
    @api.depends('approver_ids', 'approver_ids.required')
    def _compute_approval_minimum(self):
        """Auto-calculate approval_minimum based on count of required approvers"""
        for request in self:
            required_approvers = request.approver_ids.filtered(lambda a: a.required)
            request.approval_minimum = len(required_approvers) if required_approvers else 0
    
    # Related field to access category's available type options for domain filtering
    category_available_type_option_ids = fields.Many2many(
        'approval.type.option',
        related='category_id.available_type_option_ids',
        string='Category Available Type Options',
        readonly=True,
        store=False
    )
    # Computed deadline from approval activities (for list view, stored so it can be ordered in SQL)
    activity_deadline = fields.Date(
        string='Deadline',
        compute='_compute_activity_deadline',
        store=True,
        help='Shows the nearest approval activity deadline for this request.'
    )
    contract_id = fields.Many2one(
        'contract.management',
        string='Contract',
        domain=[('state', '=', 'active')],
        help='Link an existing active contract to this approval request.'
    )
    contract_expiry_date = fields.Date(related='contract_id.expiry_date', store=False)
    contract_partner_id = fields.Many2one(related='contract_id.partner_id', store=False)
    contract_value = fields.Monetary(related='contract_id.contract_value', store=False, string='Contract Value', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.depends('activity_ids.date_deadline', 'activity_ids.activity_type_id', 'activity_ids.user_id')
    def _compute_activity_deadline(self):
        """Compute the nearest approval activity deadline for this request."""
        ApprovalActivityType = self.env.ref('approvals.mail_activity_data_approval', raise_if_not_found=False)
        for request in self:
            deadline = False
            if not ApprovalActivityType:
                request.activity_deadline = False
                continue
            # Activities of type "Approval" for this request
            activities = request.activity_ids.filtered(lambda a: a.activity_type_id.id == ApprovalActivityType.id)
            if not activities:
                request.activity_deadline = False
                continue
            # Prefer activities assigned to the current user; fallback to any
            user_activities = activities.filtered(lambda a: a.user_id == self.env.user)
            target_activities = user_activities or activities
            dates = [a.date_deadline for a in target_activities if a.date_deadline]
            deadline = dates and min(dates) or False
            request.activity_deadline = deadline

    
    @api.onchange('category_id', 'category_require_unexpired_contract')
    def _onchange_category_contract_domain(self):
        """Update contract domain when category changes"""
        # Base domain: always filter by state (only active contracts)
        domain = [('state', '=', 'active')]
        
        # If category requires unexpired contract, add expiry date check to domain
        if self.category_id and self.category_require_unexpired_contract:
            today = fields.Date.today()
            domain.append(('expiry_date', '>=', today))
            
            # Clear contract if current selection is expired
            if self.contract_id and self.contract_id.expiry_date:
                if self.contract_id.expiry_date < today:
                    self.contract_id = False
                    return {
                        'warning': {
                            'title': _('Expired Contract'),
                            'message': _('The selected contract has expired. Please select an active contract.')
                        },
                        'domain': {'contract_id': domain}
                    }
        
        # Always return the domain (with or without expiry filter)
        return {'domain': {'contract_id': domain}}
    
    @api.model
    def default_get(self, fields_list):
        """Set initial domain for contract_id based on category"""
        res = super().default_get(fields_list)
        # Domain will be set via onchange when category is selected
        return res

    @api.onchange('contract_id')
    def _onchange_contract_id_link(self):
        for rec in self:
            if rec.contract_id:
                # Check if contract is expired when category requires unexpired contract
                if rec.category_id and rec.category_require_unexpired_contract:
                    if rec.contract_id.expiry_date:
                        today = fields.Date.today()
                        if rec.contract_id.expiry_date < today:
                            # Store expiry date before clearing
                            expiry_date = rec.contract_id.expiry_date
                            # Clear the expired contract
                            rec.contract_id = False
                            return {
                                'warning': {
                                    'title': _('Expired Contract'),
                                    'message': _('The selected contract has expired on %s. Please select an active contract.') % expiry_date
                                }
                            }
                
                # Auto-link partner if not set (only if contract is valid)
                if rec.contract_id and not rec.partner_id:
                    rec.partner_id = rec.contract_id.partner_id


    checklist_line_ids = fields.One2many(
        comodel_name="approval.checklist.line",
        inverse_name="request_id",
        string="Checklist Items",
    )

    optional_approver_ids = fields.One2many(
        comodel_name='approval.optional.approver',
        inverse_name='request_id',
        string='Optional Approvers',
        help='Extra approvers the requester can add. They will review before default approvers.'
    )

    purchase_request_number = fields.Many2one(
        'approval.request', 
        string='Purchase Request Number',
        domain="[('category_type', '=', 'purchase_order'), ('request_status', '=', 'approved')]",
        help='Select the approved Purchase Order request that this invoice payment relates to'
    )
    
    @api.depends('purchase_request_number')
    def _compute_purchase_request_display(self):
        for record in self:
            if record.purchase_request_number:
                record.purchase_request_display = f"{record.purchase_request_number.name}"
            else:
                record.purchase_request_display = False
    
    purchase_request_display = fields.Char(
        string='Purchase Request',
        compute='_compute_purchase_request_display',
        store=False
    )

    # Description fields - structured sections (configurable per category)
    description_subject = fields.Char(
        string='Subject',
        help='Subject of the approval request'
    )
    description_background = fields.Html(
        string='Purpose',
        help='Purpose of the approval request'
    )
    description_budget_line = fields.Char(
        string='Budget Line',
        help='Budget line information for the approval request'
    )
    contract_price_line_ids = fields.One2many(
        comodel_name='approval.contract.price.line',
        inverse_name='request_id',
        string='Contract Price Items',
        help='Contract price items table'
    )
    
    @api.onchange('contract_price_line_ids')
    def _onchange_contract_price_lines(self):
        """Auto-calculate amount from sum of contract price lines (VAT Inclusive)"""
        for rec in self:
            if rec.contract_price_line_ids:
                # Calculate total from contract price lines (VAT inclusive)
                total_vat_inclusive = sum(rec.contract_price_line_ids.mapped('total_price_vat_inclusive'))
                if total_vat_inclusive > 0:
                    rec.amount = total_vat_inclusive
    
    # Related fields from category for view visibility
    category_show_subject = fields.Boolean(
        related='category_id.description_show_subject',
        string='Show Subject',
        readonly=True,
        store=False
    )
    category_show_background = fields.Boolean(
        related='category_id.description_show_background',
        string='Show Background',
        readonly=True,
        store=False
    )
    category_show_budget_line = fields.Boolean(
        related='category_id.description_show_budget_line',
        string='Show Budget Line',
        readonly=True,
        store=False
    )
    category_show_contract_price = fields.Boolean(
        related='category_id.description_show_contract_price',
        string='Show Contract Price',
        readonly=True,
        store=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Server-side finalize: compute approvers based on current values
        for rec in records:
            if hasattr(rec, 'approver_ids') and rec.request_status in (False, 'new'):
                rec._recompute_approvers()
        # records._link_attachments_to_request()
        return records

    def write(self, vals):
        # Prevent setting status to 'approved' if not all required approvers have approved
        if 'request_status' in vals and vals['request_status'] == 'approved':
            for rec in self:
                required_approvers = rec.approver_ids.filtered(lambda a: a.required)
                if required_approvers:
                    all_required_approved = all(
                        approver.status == 'approved' 
                        for approver in required_approvers
                    )
                    if not all_required_approved:
                        # Don't allow setting to approved if not all required approvers have approved
                        # Keep current status or set to pending
                        if rec.request_status != 'approved':
                            vals['request_status'] = rec.request_status
                        else:
                            vals['request_status'] = 'pending'
        
        res = super().write(vals)
        # Recompute approvers when key drivers change while request is new
        keys = set(vals.keys())
        trigger = {'amount', 'category_id', 'type_option_id', 'optional_approver_ids'}
        if keys & trigger:
            for rec in self:
                if hasattr(rec, 'approver_ids') and rec.request_status in (False, 'new'):
                    rec._recompute_approvers()
        
        # Recompute approval_minimum when approver_ids change
        if 'approver_ids' in vals:
            self._compute_approval_minimum()
        
        return res

    @api.onchange('purchase_request_number')
    def _onchange_purchase_request_number(self):
        """Auto-populate fields when a purchase request is selected"""
        if self.purchase_request_number:
            # Auto-populate amount if not already set
            if not self.amount and self.purchase_request_number.amount:
                self.amount = self.purchase_request_number.amount
            
            # Auto-populate partner if not already set
            if not self.partner_id and self.purchase_request_number.partner_id:
                self.partner_id = self.purchase_request_number.partner_id
            
            # Auto-populate date if not already set
            if not self.date and self.purchase_request_number.date:
                self.date = self.purchase_request_number.date

            # Auto-populate budget line if not already set
            if (self.purchase_request_number.description_budget_line):
                self.description_budget_line = self.purchase_request_number.description_budget_line
            else:
                self.description_budget_line = False
        else:
            # If purchase request is cleared, also clear dependent fields that come from it.
            self.description_budget_line = False

    @api.onchange('category_id')
    def _onchange_category_id(self):
        # Reset dependent fields and approvers
        for rec in self:
            rec.type_option_id = False

        # Recompute approvers when category changes
        self._recompute_approvers()
        
        # Trigger contract domain update
        self._onchange_category_contract_domain()
        
        # Update domain for type_option_id - only show types defined in category's available_type_ids
        if self.category_id and self.category_id.available_type_option_ids:
            # Get the IDs directly from available_type_ids
            option_ids = self.category_id.available_type_option_ids.ids
            if option_ids:
                return {
                    'domain': {
                        'type_option_id': [('id', 'in', option_ids)]
                    }
                }
        return {'domain': {'type_option_id': []}}

    @api.onchange('type_option_id')
    def _onchange_type_option(self):
        """Trigger checklist and approver recomputation when type option changes"""
        self._onchange_payment_type_populate_checklist()
        self._recompute_approvers()

    @api.onchange('amount')
    def _onchange_amount(self):
        """Trigger approver population and checklist when amount changes"""
        if self.category_type == 'invoice_payment':
            self._recompute_approvers()
        if self.category_type == 'purchase_order':
            # Amount change affects po_exceeds_10m/20m which affects approvers and checklist
            self._recompute_approvers()
            self._onchange_payment_type_populate_checklist()

    @api.onchange('optional_approver_ids')
    def _onchange_optional_approvers(self):
        # When optional approvers change, rebuild the approver flow while request is new
        if self.request_status in (False, 'new'):
            self._recompute_approvers()

    @api.onchange('type_option_id', 'po_exceeds_20m', 'amount')
    def _onchange_payment_type_populate_checklist(self):
        # Use configuration on the selected category when available
        if self.category_id and hasattr(self.category_id, 'checklist_template_ids') and self.category_id.checklist_template_ids:
            commands = [fields.Command.clear()]
            for tmpl in self.category_id.checklist_template_ids:
                # Filter by type option if specified
                if tmpl.type_option_ids and self.type_option_id and self.type_option_id not in tmpl.type_option_ids:
                    continue
                # Filter by amount threshold (operator/amount)
                if getattr(tmpl, 'po_amount', 0):
                    amt = self.amount or 0.0
                    thr = tmpl.po_amount
                    op = tmpl.po_amount_operator or 'ge'
                    if op == 'gt' and not (amt > thr):
                        continue
                    if op == 'ge' and not (amt >= thr):
                        continue
                    if op == 'lt' and not (amt < thr):
                        continue
                    if op == 'le' and not (amt <= thr):
                        continue
                    if op == 'eq' and not (amt == thr):
                        continue
                commands.append(fields.Command.create({
                    'name': tmpl.name,
                    'is_required': tmpl.is_required,
                }))
            self.checklist_line_ids = commands
            return

        # No templates defined: clear checklist and let user add manually
        self.checklist_line_ids = [fields.Command.clear()]

    @api.constrains('category_id', 'type_option_id')
    def _check_type_option_alignment(self):
        """Validate that the selected type option is from the category's available types"""
        for rec in self:
            # Skip validation for existing approved/cancelled records (backward compatibility)
            if rec.request_status in ('approved', 'cancel', 'refused'):
                continue
            
            # If category has specific available types configured, ensure selection is from that list
            if rec.category_id and rec.category_id.available_type_option_ids and rec.type_option_id:
                if rec.type_option_id not in rec.category_id.available_type_option_ids:
                    raise ValidationError(
                        _("The selected type option '%s' is not available for this category. "
                          "Please select from the configured available types.") % rec.type_option_id.name
                    )

    def _raise_if_missing_required_documents(self):
        for request in self:
            missing_lines = request.checklist_line_ids.filtered(lambda l: l.is_required and not l.document_ids)
            if missing_lines:
                names = ", ".join(missing_lines.mapped('name'))
                raise ValidationError(_(f"You must upload documents for required items: {names}"))

    @api.constrains('contract_price_line_ids', 'category_show_contract_price')
    def _check_contract_price_lines_required(self):
        """Ensure at least one contract price line is present when section is active."""
        for rec in self:
            if rec.category_show_contract_price and not rec.contract_price_line_ids:
                raise ValidationError(_("Please add at least one Contract Price line."))

    def _check_contract_rules(self):
        for rec in self:
            cat = rec.category_id
            if not cat:
                continue
            # Enforce category-driven contract rules
            if getattr(cat, 'requires_contract', False):
                if not rec.contract_id:
                    raise ValidationError(_("This approval requires selecting a contract."))
                c = rec.contract_id
                if getattr(cat, 'require_unexpired_contract', True) and c.expiry_date and c.expiry_date < fields.Date.today():
                    raise ValidationError(_("Selected contract is expired."))
                if getattr(cat, 'match_partner', False) and rec.partner_id and c.partner_id and c.partner_id.id != rec.partner_id.id:
                    raise ValidationError(_("Contract partner must match the request partner."))
                if getattr(cat, 'require_contract_document', False):
                    # Require at least one attachment on any checklist line
                    has_any_attachment = bool(rec.checklist_line_ids.mapped('document_ids'))
                    if not has_any_attachment:
                        raise ValidationError(_("Upload the contract document as per checklist to proceed."))

    def action_confirm(self):
        # FIRST: Check if this is a resubmission after guarantee was returned
        # If all approvers are already approved and guarantee is now attached, bypass normal flow
        for request in self:
            if request.request_status == 'new' and request.approver_ids:
                # Check if all approvers are already approved (resubmission scenario)
                all_approvers_approved = all(
                    approver.status == 'approved' 
                    for approver in request.approver_ids 
                    if approver.required
                )
                
                if all_approvers_approved:
                    # This is a resubmission - check if guarantee is required and attached
                    if request._requires_performance_guarantee():
                        if request._has_performance_guarantee():
                            # All approvers approved + guarantee attached = approve immediately
                            request.sudo().write({'request_status': 'approved'})
                            # Send notifications
                            request._send_approval_notifications()
                            return True
                        else:
                            # Guarantee still missing - block resubmission
                            threshold_info = request._get_guarantee_threshold_info()
                            threshold_text = threshold_info if threshold_info else 'the configured threshold'
                            raise ValidationError(
                                _("Performance Guarantee document is still required for amounts exceeding %s.\n\n"
                                  "Please attach the Performance Guarantee document in the Checklist section before resubmitting.") % threshold_text
                            )
                    else:
                        # No guarantee required, proceed with normal flow
                        pass
        
        # Normal submission flow - validate everything
        # Validate contract linkage rules before submitting
        self._check_contract_rules()
        
        # Validate amount requirement
        for request in self:
            if request.category_has_amount == 'required':
                if not request.amount or request.amount == 0:
                    raise ValidationError(_("Amount is required for this approval category. Please enter an amount greater than 0."))
        
        # Validate contract price total matches amount when contract price is shown
        for request in self:
            if request.category_show_contract_price and request.contract_price_line_ids:
                # Calculate total from contract price lines (VAT inclusive)
                total_vat_inclusive = sum(request.contract_price_line_ids.mapped('total_price_vat_inclusive'))
                
                if request.amount:
                    if abs(total_vat_inclusive - request.amount) != 0:
                        raise ValidationError(
                            _("The total of Contract Price items (VAT Inclusive) must equal the Amount.\n\n"
                              "Contract Price Total: %s\n"
                              "Amount: %s\n\n"
                              "Please adjust the contract price items or the amount to match.") % 
                            ('{:,.2f}'.format(total_vat_inclusive), '{:,.2f}'.format(request.amount))
                        )
        
        # Prevent submission when requester doesn't have digital signature
        for request in self:
            requester = getattr(request, 'request_owner_id', False) or request.create_uid
            if requester:
                try:
                    # Use sudo to bypass read restriction on sign_signature
                    has_signature = bool(requester.sudo().sign_signature)
                except Exception:
                    has_signature = False
                
                if not has_signature:
                    raise UserError(_("You must configure your digital signature before submitting an approval request."))

        self._raise_if_missing_required_documents()
        
        # Validate Performance Guarantee requirement before FIRST submission only
        # (Resubmissions are handled above)
        for request in self:
            if request.request_status == 'new' and request.approver_ids:
                # Check if this is a first submission (not all approvers approved yet)
                all_approvers_approved = all(
                    approver.status == 'approved' 
                    for approver in request.approver_ids 
                    if approver.required
                )
                # Only validate guarantee for first submissions
                if all_approvers_approved:
                    if request._requires_performance_guarantee():
                        if not request._has_performance_guarantee():
                            threshold_info = request._get_guarantee_threshold_info()
                            threshold_text = threshold_info if threshold_info else 'the configured threshold'
                            raise ValidationError(
                                _("Performance Guarantee document is required for amounts exceeding %s.\n\n"
                                  "Please attach the Performance Guarantee document in the Checklist section before submitting.") % threshold_text
                            )

        # Sync digital signatures: copy users' sign_signature (Sign app) to public signature
        def sync_user_signature(user_rec):
            if not user_rec:
                return
            try:
                # Use sudo to bypass read restriction on sign_signature
                user_rec.sudo().sign_signature
            except Exception as e:
                # Log error but don't fail the confirmation
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Failed to sync signature for user {user_rec.name}: {str(e)}")

        for request in self:
            # Requester
            requester = getattr(request, 'request_owner_id', False) or request.create_uid
            sync_user_signature(requester)

            # Reviewer: Department manager user, fallback to employee's parent manager
            dept_manager_user = False
            try:
                emp = hasattr(requester, 'employee_id') and requester.employee_id or False
                dept = emp and hasattr(emp, 'department_id') and emp.department_id or False
                manager = dept and hasattr(dept, 'manager_id') and dept.manager_id or False
                dept_manager_user = manager and hasattr(manager, 'user_id') and manager.user_id or False
            except Exception:
                dept_manager_user = False
            parent_manager_user = False
            try:
                parent = emp and hasattr(emp, 'parent_id') and emp.parent_id or False
                parent_manager_user = parent and hasattr(parent, 'user_id') and parent.user_id or False
            except Exception:
                parent_manager_user = False
            reviewer = parent_manager_user or dept_manager_user
            sync_user_signature(reviewer)

            # Approvers on the request
            for approver_line in getattr(request, 'approver_ids', self.env['approval.approver']):
                sync_user_signature(getattr(approver_line, 'user_id', False))

        # Call super().action_confirm() - wrap in try/except to handle email configuration errors and access errors
        try:
            result = super().action_confirm()
        except ValidationError as e:
            # Re-raise validation errors immediately (these are business logic errors)
            raise
        except (UserError, AccessError, Exception) as e:
            error_msg = str(e).lower()
            # Check if it's an email-related error (UserError or any exception)
            is_email_error = ('email' in error_msg or 'sender' in error_msg or 
                             'unable to send message' in error_msg or
                             'configure the sender' in error_msg)
            
            # Check if it's an access error for approver records
            is_approver_access_error = (isinstance(e, AccessError) and 
                                       ('approver' in error_msg or 'write' in error_msg))
            
            if is_email_error:
                # Email configuration error - log it but don't fail the submission
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Email notification failed during submission (email not configured): {str(e)}")
                # Try to continue without email notification
                # Manually set status if needed (base action_confirm might have failed)
                for request in self.sudo():
                    if request.request_status == 'new':
                        # Base action_confirm might not have completed, try to proceed
                        # Set approvers to pending if they exist
                        if request.approver_ids:
                            request.approver_ids.write({'status': 'pending'})
                        request.write({'request_status': 'pending'})
                result = True
            elif is_approver_access_error:
                # Access error when trying to write to approver records
                # This can happen if base action_confirm tries to write without sudo
                # Use sudo to complete the submission
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Access error during submission, using sudo to complete: {str(e)}")
                # Complete the submission with sudo
                for request in self.sudo():
                    if request.request_status == 'new':
                        # Set approvers to pending if they exist
                        if request.approver_ids:
                            request.approver_ids.write({'status': 'pending'})
                        request.write({'request_status': 'pending'})
                result = True
            else:
                # Re-raise if it's not an email-related or approver access error
                raise
        
        # Ensure optional approvers don't block the first required approver
        for request in self.filtered('category_approver_sequence'):
            request._activate_waiting_batch_approvers()
        
        return result

    @api.depends('approver_ids.status')
    def action_cancel(self):
        """Override to prevent cancel after at least one approval if configured"""
        for request in self:
            # Check if category prevents withdrawal after approval
            if not (
                request.category_id
                and hasattr(request.category_id, 'prevent_withdrawal_after_approval')
                and request.category_id.prevent_withdrawal_after_approval
            ):
                return super().action_cancel()
            status_lst = request.mapped('approver_ids.status')
            if status_lst.count('approved') >= 1:
                raise UserError(_("This request cannot be canceled as it has been approved. "
                                "Please contact your administrator if you need to cancel this request."))
        

    def action_withdraw(self, approver=None):
        """
        Restrict "withdraw approval" when configured on the category.

        Rule requested: an approver can withdraw their approval only if the next approver(s)
        in the list have NOT already approved.
        """
        # Keep signature compatible with enterprise `approvals` (action_withdraw(self, approver=None)).
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(lambda a: a.user_id == self.env.user)

        for request in self:
            if not (
                request.category_id
                and hasattr(request.category_id, 'prevent_withdrawal_after_approval')
                and request.category_id.prevent_withdrawal_after_approval
            ):
                continue

            current_approvers = request.approver_ids & approver
            if not current_approvers:
                continue

            # Block withdraw if any later approver is already approved.
            for cur in current_approvers:
                later_approved = request.approver_ids.filtered(
                    lambda a: a.status == 'approved' and (
                        (hasattr(a, 'sequence') and hasattr(cur, 'sequence') and (
                            a.sequence > cur.sequence or (a.sequence == cur.sequence and a.id > cur.id)
                        )) or (
                            # Defensive fallback if `sequence` is missing for any reason.
                            (not hasattr(a, 'sequence') or not hasattr(cur, 'sequence')) and a.id > cur.id
                        )
                    )
                )
                if later_approved:
                    raise UserError(_(
                        "You cannot withdraw your approval because a next approver has already approved.\n\n"
                        "Please contact your administrator if you need to revert this approval."
                    ))

        return super().action_withdraw(approver=approver)

    def action_resubmit(self):
        """Allow requester to resubmit a rejected request"""
        for request in self:
            # Check if request is in refused status
            if request.request_status not in ['refused', 'canceled']:
                raise UserError(_("Only rejected or canceled requests can be resubmitted."))
            
            # Check if current user is the requester
            current_user = self.env.user
            requester = request.request_owner_id or request.create_uid
            if current_user != requester:
                raise UserError(_("Only the requester can resubmit a rejected or canceled request."))
            
            # Reset request status to 'new' so requester can edit and resubmit
            request.sudo().write({'request_status': 'new'})
            
            # Reset all approver statuses to 'new' to clear previous approvals
            if request.approver_ids:
                request.approver_ids.sudo().write({'status': 'new'})
            
            # Post message in chatter
            message_body = _('%s has reopened this request for resubmission.') % current_user.name
            request.message_post(
                body=message_body,
                subject=_('Request Reopened for Resubmission'),
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )

    def action_approve(self, approver=None):
        """Override to send notifications when fully approved and handle delegations"""
        # Prevent approval when digital signature is not set for the approving user
        approving_user = None
        current_user = self.env.user
        
        try:
            # Check if current user is a delegate for any approver on this request
            delegation_model = self.env['approval.delegation']
            delegation_record = False
            approving_user = current_user  # Default to current user (delegate uses their own signature)
            
            # If approver is explicitly passed, check if current user is delegate for that approver
            if approver and hasattr(approver, 'user_id') and approver.user_id:
                if approver.user_id != current_user:
                    # Current user is trying to approve for someone else - check if they're a delegate
                    delegation_record = delegation_model.get_active_delegation(
                        approver.user_id.id,
                        self.category_id.id if self.category_id else None
                    )
                    if delegation_record:
                        # Current user is a delegate - they use their own signature
                        approving_user = current_user
                    else:
                        # Not a delegate, use the approver's signature (normal case)
                        approving_user = approver.user_id
            else:
                # Check if current user is a delegate for any pending approver on this request
                approver_lines = self.approver_ids.filtered(
                    lambda a: a.status == 'pending' and a.user_id != current_user
                )
                for approver_line in approver_lines:
                    delegation_record = delegation_model.get_active_delegation(
                        approver_line.user_id.id,
                        self.category_id.id if self.category_id else None
                    )
                    if delegation_record:
                        # Current user is a delegate for this approver
                        approver = approver_line
                        approving_user = current_user  # Delegate uses their own signature
                        break
                # If no delegation found and no approver passed, check if current user is a direct approver
                if not delegation_record and not approver:
                    direct_approver = self.approver_ids.filtered(
                        lambda a: a.status == 'pending' and a.user_id == current_user
                    )[:1]
                    if direct_approver:
                        approver = direct_approver
                        approving_user = current_user
            
            # If delegation found, record it on the approver line
            if delegation_record and approver:
                approver.delegated_by_id = delegation_record.delegator_id
            
            # Access with sudo to bypass potential read restrictions on sign_signature
            has_signature = bool(approving_user.sudo().sign_signature)
        except Exception:
            has_signature = False

        if not has_signature:
            raise UserError(_("You must configure your digital signature before approving."))
        
        # Check sequential approval requirement if enabled
        if self.category_approver_sequence:
            # Ensure we have the approver object
            if not approver:
                # Find the approver for current user
                approver = self.approver_ids.filtered(
                    lambda a: a.status == 'pending' and a.user_id == current_user
                )[:1]
            
            if approver:
                # Get all approvers sorted by sequence
                all_approvers = self.approver_ids.sorted('sequence')
                current_approver_index = None
                
                # Find the current approver's position
                for idx, appr in enumerate(all_approvers):
                    if appr.id == approver.id:
                        current_approver_index = idx
                        break
                
                # If we found the approver, check if previous approvers have approved
                if current_approver_index is not None and current_approver_index > 0:
                    previous_approvers = all_approvers[:current_approver_index]
                    # Filter to only required approvers
                    required_previous = previous_approvers.filtered(lambda a: a.required)
                    
                    # Check if all required previous approvers have approved
                    for prev_appr in required_previous:
                        if prev_appr.status != 'approved':
                            raise UserError(
                                _("Approvers must approve in sequence. Please wait for %s to approve first.") % 
                                prev_appr.user_id.name
                            )

        result = super().action_approve(approver=approver)
        
        # After base approval, activate all approvers with the same sequence (batch non-required approvers)
        for request in self:
            request._activate_waiting_batch_approvers()
        
        # Notify requester about the approval
        for request in self:
            if approver and approver.status == 'approved':
                request._notify_requester_of_approval(approver)
        
        # Check if request is now fully approved
        for request in self:
            # First, verify that all required approvers have approved
            # The base module may set status to 'approved' based on approval_minimum,
            # but we need to ensure all required approvers have approved
            required_approvers = request.approver_ids.filtered(lambda a: a.required)
            if required_approvers:
                all_required_approved = all(
                    approver.status == 'approved' 
                    for approver in required_approvers
                )
                # If base module set it to approved but not all required approvers have approved,
                # set it back to pending
                if request.request_status == 'approved' and not all_required_approved:
                    request.sudo().write({'request_status': 'pending'})
                    continue
            
            # Only proceed if request is truly approved (all required approvers approved)
            if request.request_status == 'approved':
                # Check if Performance Guarantee is required (>20M) and attached
                if request._requires_performance_guarantee():
                    if not request._has_performance_guarantee():
                        # Return request to requester to attach Performance Guarantee
                        request._return_to_requester_for_guarantee()
                        continue  # Skip notification, request is not fully approved yet
                
                # Request is fully approved with guarantee (if required), send notifications
                request._send_approval_notifications()
        
        return result
    
    def _notify_requester_of_approval(self, approver):
        """Notify the requester when an approver approves their request"""
        self.ensure_one()
        
        requester = self.request_owner_id or self.create_uid
        if not requester:
            return
        
        # Determine who approved (could be delegate or delegator)
        approver_name = self.env.user.name
        approver_role = approver.approval_role if approver.approval_role else 'Approver'
        
        # Post message in chatter (plain text; avoid raw HTML tags).
        # This single notification email (generated from the chatter message)
        # is the only email that should go to the requester at each approval step.
        message_body = _('%s has approved your request "%s".') % (approver_name, self.name)

        # Add pending approvers info if any (use newlines instead of <br/>)
        pending_approvers = self.approver_ids.filtered(lambda a: a.status in ['pending', 'waiting'])
        if pending_approvers and self.request_status != 'approved':
            pending_names = ', '.join(pending_approvers.mapped('user_id.name'))
            message_body += '\n\n' + _('Pending approvers: %s') % pending_names
        
        self.message_post(
            body=message_body,
            subject=_('Approval Update: %s') % approver_role,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
            partner_ids=[requester.partner_id.id] if requester.partner_id else []
        )
    
    def _activate_waiting_batch_approvers(self):
        """
        After an approval, activate all approvers with the same sequence as any newly pending approvers.
        This ensures non-required approvers are batched together.
        """
        self.ensure_one()
        
        # Get all pending approvers
        pending_approvers = self.approver_ids.filtered(lambda a: a.status == 'pending')
        
        if not pending_approvers:
            return
        
        # Get the sequences of all pending approvers
        pending_sequences = set(pending_approvers.mapped('sequence'))
        
        # Get all waiting approvers
        waiting_approvers = self.approver_ids.filtered(lambda a: a.status == 'waiting')
        
        # Find waiting approvers that have the same sequence as any pending approver
        batch_approvers = waiting_approvers.filtered(lambda a: a.sequence in pending_sequences)
        
        # Activate all of them
        if batch_approvers:
            batch_approvers.sudo().write({'status': 'pending'})
    
    def _requires_performance_guarantee(self):
        """Check if request requires checklist items that must be completed after approval"""
        self.ensure_one()
        
        if not self.category_id:
            return False
        
        # Find checklist templates that require completion after approval
        after_approval_templates = self.category_id.checklist_template_ids.filtered(
            lambda t: t.require_after_approval
        )
        
        if not after_approval_templates:
            return False
        
        # Check if request amount matches any template's threshold
        request_amount = self.amount or 0.0
        for template in after_approval_templates:
            if not template.po_amount:
                # Template exists but no amount threshold - consider it always required
                return True
            
            threshold = template.po_amount
            operator = template.po_amount_operator or 'ge'
            
            # Check if amount matches the threshold condition
            if operator == 'gt' and request_amount > threshold:
                return True
            elif operator == 'ge' and request_amount >= threshold:
                return True
            elif operator == 'lt' and request_amount < threshold:
                return True
            elif operator == 'le' and request_amount <= threshold:
                return True
            elif operator == 'eq' and request_amount == threshold:
                return True
        
        return False
    
    def _has_performance_guarantee(self):
        """Check if required after-approval checklist items have documents attached"""
        self.ensure_one()
        
        if not self.category_id:
            return False
        
        # Find checklist templates that require completion after approval
        after_approval_templates = self.category_id.checklist_template_ids.filtered(
            lambda t: t.require_after_approval
        )
        
        if not after_approval_templates:
            return True  # No after-approval requirements, consider it satisfied
        
        # Get template names to match with checklist lines
        template_names = after_approval_templates.mapped('name')
        
        # Find matching checklist lines
        after_approval_lines = self.checklist_line_ids.filtered(
            lambda l: l.name in template_names
        )
        
        if not after_approval_lines:
            return False
        
        # Check if all required after-approval lines have documents attached
        for line in after_approval_lines:
            if not line.document_ids:
                return False
        
        return True
    
    def _return_to_requester_for_guarantee(self):
        """Return request to requester to attach Performance Guarantee"""
        self.ensure_one()
        
        # Get the threshold amount from the template for the message
        threshold_info = self._get_guarantee_threshold_info()
        threshold_text = threshold_info if threshold_info else 'the configured threshold'
        
        # Set request status back to 'new' so requester can attach guarantee and resubmit
        # Note: We keep approvers as approved so they don't need to re-approve
        # The system will check again when resubmitted
        self.write({'request_status': 'new'})
        
        # Get requester
        requester = self.request_owner_id or self.create_uid
        
        # Post a message on the request (visible in chatter)
        message_body = _('Request returned to requester: Performance Guarantee document is required for amounts exceeding %s. '
                        'Please attach the document in the Checklist section and resubmit.') % threshold_text
        
        self.message_post(
            body=message_body,
            subject=_('Performance Guarantee Required'),
            message_type='notification',
            subtype_xmlid='mail.mt_comment'
        )
        
        # Create an activity for the requester
        if requester:
            try:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=requester.id,
                    summary=_('Action Required: Performance Guarantee Required'),
                    # Use newlines instead of <br/> to avoid raw HTML tags in the UI
                    note=_(
                        'The approval request "%s" has been approved, but requires a Performance Guarantee document '
                        'because the amount exceeds %s.\n\n'
                        'Please attach the Performance Guarantee document in the Checklist section and resubmit the request.'
                    ) % (self.name, threshold_text),
                )
            except Exception:
                pass  # Don't block workflow if activity creation fails
            
            # Send email notification
            if requester.partner_id and requester.partner_id.email:
                try:
                    template_values = {
                        'subject': _('Action Required: Performance Guarantee Required - %s') % self.name,
                        'body_html': _(
                            '<p>Dear %s,</p>'
                            '<p>The approval request <strong>"%s"</strong> has been approved, but requires a Performance Guarantee document '
                            'because the amount exceeds %s.</p>'
                            '<p><strong>Action Required:</strong></p>'
                            '<ul>'
                            '<li>Attach the Performance Guarantee document in the Checklist section</li>'
                            '<li>Resubmit the request</li>'
                            '</ul>'
                            '<p>Please complete this as soon as possible.</p>'
                            '<p>Best regards,<br/>Approval System</p>'
                        ) % (requester.name, self.name, threshold_text),
                        'email_to': requester.partner_id.email,
                        'email_from': self.env.company.email or self.env.user.email,
                        'auto_delete': False,
                    }
                    
                    mail = self.env['mail.mail'].sudo().create(template_values)
                    mail.send()
                except Exception:
                    pass  # Don't block workflow if email sending fails
    
    def _get_guarantee_threshold_info(self):
        """Get formatted threshold information from after-approval checklist template"""
        self.ensure_one()
        
        if not self.category_id:
            return None
        
        # Find checklist templates that require completion after approval and have a threshold
        after_approval_templates = self.category_id.checklist_template_ids.filtered(
            lambda t: t.require_after_approval and t.po_amount
        )
        
        if not after_approval_templates:
            return None
        
        # Get the first matching template with threshold
        template = after_approval_templates[0]
        threshold = template.po_amount
        operator = template.po_amount_operator or 'ge'
        
        # Format the threshold with currency
        currency = template.company_currency_id or self.company_id.currency_id
        if currency:
            # Format amount with currency symbol
            formatted_amount = f"{threshold:,.0f} {currency.symbol}"
        else:
            formatted_amount = f"{threshold:,.0f}"
        
        # Map operator to text
        operator_map = {
            'gt': '>',
            'ge': '≥',
            'lt': '<',
            'le': '≤',
            'eq': '='
        }
        operator_text = operator_map.get(operator, '≥')
        
        return f'{operator_text} {formatted_amount}'
    
    def _send_approval_notifications(self):
        """Send notifications to configured users when request is approved"""
        self.ensure_one()
        
        if not self.category_id or not hasattr(self.category_id, 'notification_user_ids'):
            return
            
        notification_users = self.category_id.notification_user_ids
        if not notification_users:
            return
        
        # Get partner IDs, filtering out those without email if email is required
        partner_ids = notification_users.mapped('partner_id').filtered(lambda p: p.email).ids
        if not partner_ids:
            # If no partners have email, just post a message instead
            # Plain-text body for chatter; avoid HTML tags
            self.message_post(
                body=_(
                    'The approval request "%(name)s" has been fully approved.\n'
                    'Category: %(category)s\n'
                    'Requester: %(requester)s\n'
                    'Amount: %(amount)s'
                ) % {
                    'name': self.name,
                    'category': self.category_id.name,
                    'requester': self.request_owner_id.name or self.create_uid.name,
                    'amount': self.amount or 0,
                },
                subject=_('Approval Request Approved: %s') % self.name,
            )
            return
        
        # Try to send notification email with HTML body, fallback to message_post
        email_body = _(
            '<p>The approval request <strong>"%s"</strong> has been fully approved.</p>'
            '<p><strong>Category:</strong> %s<br/>'
            '<strong>Requester:</strong> %s<br/>'
            '<strong>Amount:</strong> %s</p>'
        ) % (
            self.name,
            self.category_id.name,
            self.request_owner_id.name or self.create_uid.name,
            self.amount or 0
        )
        try:
            mail_values = {
                'subject': _('Approval Request Approved: %s') % self.name,
                'body_html': email_body,
                'recipient_ids': [(6, 0, partner_ids)],
                'email_from': self.env.company.email or self.env.user.email,
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
        except Exception:
            # Fallback to a plain-text message in chatter if email sending fails
            fallback_body = _(
                'The approval request "%(name)s" has been fully approved.\n'
                'Category: %(category)s\n'
                'Requester: %(requester)s\n'
                'Amount: %(amount)s'
            ) % {
                'name': self.name,
                'category': self.category_id.name,
                'requester': self.request_owner_id.name or self.create_uid.name,
                'amount': self.amount or 0,
            }
            self.message_post(
                body=fallback_body,
                subject=_('Approval Request Approved: %s') % self.name,
            )
        
        # Create activities for notification users so they can act on the approved request
        self._schedule_notification_user_activities(notification_users)

    def _schedule_notification_user_activities(self, notification_users):
        """Create activities for users configured to be notified after approval."""
        self.ensure_one()
        if not notification_users:
            return
        activity_xmlid = 'approvals.mail_activity_data_approval'
        activity_type = self.env.ref(activity_xmlid, raise_if_not_found=False)
        if not activity_type:
            activity_xmlid = 'mail.mail_activity_data_todo'
            activity_type = self.env.ref(activity_xmlid, raise_if_not_found=False)
        if not activity_type:
            return
        Activity = self.env['mail.activity'].sudo()
        for user in notification_users:
            if not user:
                continue
            existing = Activity.search([
                ('res_model', '=', 'approval.request'),
                ('res_id', '=', self.id),
                ('user_id', '=', user.id),
                ('activity_type_id', '=', activity_type.id),
            ], limit=1)
            if existing:
                continue
            # Use category-specific deadline when configured, otherwise default to 1 day
            days = getattr(self.category_id, 'approval_deadline_days', 0) or 0
            deadline = fields.Date.today() + timedelta(days=days)
            self.activity_schedule(
                activity_xmlid,
                user_id=user.id,
                summary=_('Approved request requires your attention'),
                date_deadline=deadline,
            )

    def _build_default_approver_commands(self):
        """Return a list of Command.create(...) to set on approver_ids based on templates and context."""
        # Defensive: only proceed if target field exists and structure is compatible
        if 'approver_ids' not in self._fields:
            return []
        approver_field = self._fields['approver_ids']
        line_model = approver_field.comodel_name
        line_model_fields = self.env[line_model].fields_get()

        def approver_line(user, sequence=1, required=True, category_id=None):
            """
            Create approver line values, checking for active delegations.
            If user has an active delegate, use the delegate instead.
            """
            vals = {}
            
            # Check for active delegation
            delegation = self.env['approval.delegation'].sudo().get_active_delegation(
                delegator_id=user.id,
                category_id=category_id,
                check_date=True
            )
            
            if delegation and 'delegated_by_id' in line_model_fields:
                # Use delegate instead of delegator
                if 'user_id' in line_model_fields:
                    vals['user_id'] = delegation.delegate_id.id
                vals['delegated_by_id'] = user.id  # Store original delegator
            else:
                # No delegation, use original user
                if 'user_id' in line_model_fields:
                    vals['user_id'] = user.id
            
            if 'required' in line_model_fields:
                vals['required'] = required
            if 'sequence' in line_model_fields:
                vals['sequence'] = sequence
            return vals

        for request in self:
            commands = []
            seq = 1
            added_user_ids = set()
            category_id = request.category_id.id if request.category_id else None

            # Prepared by: the request owner (no approver line needed typically)
            requester = getattr(request, 'request_owner_id', False) or request.create_uid
            if not requester:
                continue

            # Get company CFO, Senior Approver, and CEO
            # These will be added at the end in order: CFO, Senior Approver, CEO
            cfo = request.company_id.cfo_id if hasattr(request.company_id, 'cfo_id') else False
            senior_approver = request.company_id.senior_approver_id if hasattr(request.company_id, 'senior_approver_id') else False
            ceo = request.company_id.ceo_id if hasattr(request.company_id, 'ceo_id') else False
            
            # Track executive users to ensure they're added at the end
            executive_users = []
            if cfo:
                executive_users.append(('cfo', cfo))
            if senior_approver:
                executive_users.append(('senior', senior_approver))
            if ceo:
                executive_users.append(('ceo', ceo))
            executive_user_ids = {u.id for _, u in executive_users}
            # Track required status for executive users from their original configuration
            executive_required_status = {}

            # Determine reviewer: Department manager user, fallback to employee's parent manager
            dept_manager_user = False
            try:
                emp = hasattr(requester, 'employee_id') and requester.employee_id or False
                dept = emp and hasattr(emp, 'department_id') and emp.department_id or False
                manager = dept and hasattr(dept, 'manager_id') and dept.manager_id or False
                dept_manager_user = manager and hasattr(manager, 'user_id') and manager.user_id or False
            except Exception:
                dept_manager_user = False
            parent_manager_user = False
            try:
                parent = emp and hasattr(emp, 'parent_id') and emp.parent_id or False
                parent_manager_user = parent and hasattr(parent, 'user_id') and parent.user_id or False
            except Exception:
                parent_manager_user = False
            reviewer = parent_manager_user or dept_manager_user
            is_specialist = not reviewer  # Specialist = no reviewer

            # If category has configured approver templates, use them
            if request.category_id and hasattr(request.category_id, 'approver_template_ids') and request.category_id.approver_template_ids:
                # Always inject reviewers group first (manager + optional approvers)
                reviewer_users = []
                # Add optional approvers first
                if request.optional_approver_ids:
                    for opt in sorted(request.optional_approver_ids, key=lambda r: r.sequence or 0):
                        user_rec_opt = getattr(opt, 'user_id', False)
                        if user_rec_opt:
                            is_required = getattr(opt, 'required', False)
                            reviewer_users.append((user_rec_opt, is_required))
                # Add manager based on manager_approval setting
                if not is_specialist and reviewer and request.category_id.manager_approval:
                    manager_required = request.category_id.manager_approval == 'required'
                    reviewer_users.append((reviewer, manager_required))
                for user_rec_opt, is_required in reviewer_users:
                    if user_rec_opt and user_rec_opt.id not in added_user_ids:
                        # Skip executive users here - they'll be added at the end
                        if user_rec_opt.id in executive_user_ids:
                            continue
                        vals_r = approver_line(user_rec_opt, seq, required=is_required, category_id=category_id)
                        if vals_r and vals_r.get('user_id'):
                            commands.append(fields.Command.create(vals_r))
                            added_user_ids.add(user_rec_opt.id)
                            # Only increment sequence if this is a required approver
                            if is_required:
                                seq += 1
                
                # Add category's direct approver_ids (after manager, before templates)
                if hasattr(request.category_id, 'approver_ids') and request.category_id.approver_ids:
                    for cat_approver in request.category_id.approver_ids.sorted(lambda r: getattr(r, 'sequence', 0) or 0):
                        cat_user = getattr(cat_approver, 'user_id', False)
                        if cat_user and cat_user.id not in added_user_ids:
                            # Skip executive users here - they'll be added at the end
                            if cat_user.id in executive_user_ids:
                                # Store their required status for later
                                cat_required = getattr(cat_approver, 'required', True)
                                executive_required_status[cat_user.id] = cat_required
                                continue
                            cat_required = getattr(cat_approver, 'required', True)
                            vals_cat = approver_line(cat_user, seq, required=cat_required, category_id=category_id)
                            if vals_cat and vals_cat.get('user_id'):
                                commands.append(fields.Command.create(vals_cat))
                                added_user_ids.add(cat_user.id)
                                # Only increment sequence if this is a required approver
                                if cat_required:
                                    seq += 1
                
                for tmpl in request.category_id.approver_template_ids.sorted(lambda r: r.sequence):
                    # Conditional inclusion based on template filters
                    if tmpl.type_option_ids and request.type_option_id and request.type_option_id not in tmpl.type_option_ids:
                        continue
                    if getattr(tmpl, 'po_amount', 0):
                        amt = request.amount or 0.0
                        thr = tmpl.po_amount
                        op = tmpl.po_amount_operator or 'ge'
                        if op == 'gt' and not (amt > thr):
                            continue
                        if op == 'ge' and not (amt >= thr):
                            continue
                        if op == 'lt' and not (amt < thr):
                            continue
                        if op == 'le' and not (amt <= thr):
                            continue
                        if op == 'eq' and not (amt == thr):
                            continue
                    # Use user_ids from template instead of role mapping
                    if tmpl.user_ids:
                        for user_rec in tmpl.user_ids:
                            if user_rec.id in added_user_ids:
                                continue
                            # Skip executive users here - they'll be added at the end
                            if user_rec.id in executive_user_ids:
                                # Store their required status for later
                                executive_required_status[user_rec.id] = tmpl.required
                                continue
                            vals = approver_line(user_rec, seq, required=tmpl.required, category_id=category_id)
                            if vals and vals.get('user_id'):
                                commands.append(fields.Command.create(vals))
                                added_user_ids.add(user_rec.id)
                                # Only increment sequence if this is a required approver
                                if tmpl.required:
                                    seq += 1
                    # Fallback to role-based mapping for backward compatibility
                    elif tmpl.role:
                        role_to_user = {
                            'reviewer': reviewer,
                            'cfo': cfo,
                            'senior': senior_approver,
                            'ceo': ceo,
                        }
                        # Skip reviewer role here because we already injected reviewers (incl. optional ones)
                        if tmpl.role == 'reviewer':
                            continue
                        user_rec = role_to_user.get(tmpl.role)
                        if not user_rec or user_rec.id in added_user_ids:
                            continue
                        # Skip executive users here - they'll be added at the end
                        if user_rec.id in executive_user_ids:
                            # Store their required status for later
                            executive_required_status[user_rec.id] = tmpl.required
                            continue
                        vals = approver_line(user_rec, seq, required=tmpl.required, category_id=category_id)
                        if vals and vals.get('user_id'):
                            commands.append(fields.Command.create(vals))
                            added_user_ids.add(user_rec.id)
                            # Only increment sequence if this is a required approver
                            if tmpl.required:
                                seq += 1
                
                # Remove any executive users that were added earlier (from templates or category approvers)
                commands = [cmd for cmd in commands if not (isinstance(cmd, (list, tuple)) and len(cmd) > 2 and isinstance(cmd[2], dict) and cmd[2].get('user_id') in executive_user_ids)]
                # Also remove them from added_user_ids so they can be re-added at the end
                added_user_ids -= executive_user_ids
                
                # Add executive users at the end in order: CFO, Senior Approver, CEO
                for role_name, exec_user in executive_users:
                    if exec_user and exec_user.id not in added_user_ids:
                        # Use stored required status, default to True if not found
                        exec_required = executive_required_status.get(exec_user.id, True)
                        vals = approver_line(exec_user, seq, required=exec_required, category_id=category_id)
                        if vals and vals.get('user_id'):
                            commands.append(fields.Command.create(vals))
                            added_user_ids.add(exec_user.id)
                            # Only increment sequence if this is a required approver
                            if exec_required:
                                seq += 1
                
                if commands:
                    return [fields.Command.clear()] + commands
                return []

            # Step 1: Add Reviewers group (optional approvers first, then manager)
            reviewer_users = []
            # Add optional approvers first
            if request.optional_approver_ids:
                for opt in sorted(request.optional_approver_ids, key=lambda r: r.sequence or 0):
                    user_rec = getattr(opt, 'user_id', False)
                    if user_rec:
                        is_required = getattr(opt, 'required', False)
                        reviewer_users.append((user_rec, is_required))
            # Add manager based on manager_approval setting (after optional approvers)
            if not is_specialist and reviewer and request.category_id.manager_approval:
                manager_required = request.category_id.manager_approval == 'required'
                reviewer_users.append((reviewer, manager_required))

            for user_rec, is_required in reviewer_users:
                if not user_rec or user_rec.id in added_user_ids:
                    continue
                # Skip executive users here - they'll be added at the end
                if user_rec.id in executive_user_ids:
                    continue
                lm_vals = approver_line(user_rec, seq, required=is_required, category_id=category_id)
                if lm_vals and lm_vals.get('user_id'):
                    commands.append(fields.Command.create(lm_vals))
                    added_user_ids.add(user_rec.id)
                    # Only increment sequence if this is a required approver
                    if is_required:
                        seq += 1

            # Step 2: Add category's direct approver_ids (after manager, before templates)
            if request.category_id and hasattr(request.category_id, 'approver_ids') and request.category_id.approver_ids:
                for cat_approver in request.category_id.approver_ids.sorted(lambda r: getattr(r, 'sequence', 0) or 0):
                    cat_user = getattr(cat_approver, 'user_id', False)
                    if cat_user and cat_user.id not in added_user_ids:
                        # Skip executive users here - they'll be added at the end
                        if cat_user.id in executive_user_ids:
                            # Store their required status for later
                            cat_required = getattr(cat_approver, 'required', True)
                            executive_required_status[cat_user.id] = cat_required
                            continue
                        cat_required = getattr(cat_approver, 'required', True)
                        vals_cat = approver_line(cat_user, seq, required=cat_required, category_id=category_id)
                        if vals_cat and vals_cat.get('user_id'):
                            commands.append(fields.Command.create(vals_cat))
                            added_user_ids.add(cat_user.id)
                            # Only increment sequence if this is a required approver
                            if cat_required:
                                seq += 1

            # Remove any executive users that were added earlier
            commands = [cmd for cmd in commands if not (isinstance(cmd, (list, tuple)) and len(cmd) > 2 and isinstance(cmd[2], dict) and cmd[2].get('user_id') in executive_user_ids)]
            # Also remove them from added_user_ids so they can be re-added at the end
            added_user_ids -= executive_user_ids
            
            # Add executive users at the end in order: CFO, Senior Approver, CEO
            for role_name, exec_user in executive_users:
                if exec_user and exec_user.id not in added_user_ids:
                    # Use stored required status, default to True if not found
                    exec_required = executive_required_status.get(exec_user.id, True)
                    vals = approver_line(exec_user, seq, required=exec_required, category_id=category_id)
                    if vals and vals.get('user_id'):
                        commands.append(fields.Command.create(vals))
                        added_user_ids.add(exec_user.id)
                        # Only increment sequence if this is a required approver
                        if exec_required:
                            seq += 1

            if commands:
                return [fields.Command.clear()] + commands
            return []

    def _initialize_default_approvers(self):
        """Set default approvers only when empty (used on create/default_get)."""
        for rec in self:
            if not rec.approver_ids:
                cmds = rec._build_default_approver_commands()
                if cmds:
                    rec.sudo().write({'approver_ids': cmds})
                    # Recompute approval_minimum after approvers are initialized
                    rec._compute_approval_minimum()

    def _recompute_approvers(self):
        """Always recompute and overwrite approvers (used on onchange)."""
        for rec in self:
            cmds = rec._build_default_approver_commands()
            if cmds is not None:
                rec.sudo().write({'approver_ids': cmds})
                # Recompute approval_minimum after approvers are updated
                rec._compute_approval_minimum()


class ApprovalApprover(models.Model):
    _inherit = 'approval.approver'
    
    approval_role = fields.Char(
        string='Role',
        compute='_compute_approval_role',
        store=False,
        help='Shows the approval role (CFO, CEO, or Reviewer)'
    )
    delegated_by_id = fields.Many2one(
        'res.users',
        string='Delegated By',
        help='If this approval was made via delegation, shows who delegated the authority'
    )

    def _create_activity(self):
        """Create approval activities with a deadline based on category configuration."""
        activity_xmlid = 'approvals.mail_activity_data_approval'
        for approver in self:
            if not approver.user_id or not approver.request_id:
                continue
            # Use the category's configured deadline when available, fallback to 2 days
            category = approver.request_id.category_id
            days = getattr(category, 'approval_deadline_days', 0) or 0
            deadline = fields.Date.today() + timedelta(days=days)
            approver.request_id.activity_schedule(
                activity_xmlid,
                user_id=approver.user_id.id,
                date_deadline=deadline,
            )
    
    def write(self, vals):
        """Override to manage activities for both delegate and delegator"""
        result = super().write(vals)
        
        # When status changes to 'pending', create activities for both delegate and delegator
        if 'status' in vals and vals['status'] == 'pending':
            for approver in self:
                approver._create_delegation_activities()
        
        return result
    
    def _create_delegation_activities(self):
        """Create activities for both delegate and delegator when approver becomes pending"""
        self.ensure_one()

        # If there is no delegator, rely on the core approvals logic
        # to create the standard activity for the approver.
        # This avoids creating duplicate activities for the same user.
        if not self.delegated_by_id:
            return

        # Get list of users to create activities for.
        # We only create an extra activity for the delegator so they can
        # track the delegated approval, while the delegate keeps the core one.
        users_to_notify = {self.delegated_by_id.id}

        # Create activities for all unique users (currently just the delegator)
        for user_id in users_to_notify:
            # Check if activity already exists for this user
            existing_activity = self.env['mail.activity'].search([
                ('res_id', '=', self.request_id.id),
                ('res_model', '=', 'approval.request'),
                ('user_id', '=', user_id),
                ('activity_type_id', '=', self.env.ref('approvals.mail_activity_data_approval').id)
            ], limit=1)
            
            if not existing_activity:
                # Create activity with a deadline based on category configuration
                days = getattr(self.request_id.category_id, 'approval_deadline_days', 0) or 0
                deadline = fields.Date.today() + timedelta(days=days)
                self.request_id.activity_schedule(
                    'approvals.mail_activity_data_approval',
                    user_id=user_id,
                    summary=_('Approval Request'),
                    date_deadline=deadline,
                )

        # Additionally, send an assignment email to the active approver (delegate/assigned user)
        if self.user_id and self.user_id.partner_id:
            partner = self.user_id.partner_id
            request = self.request_id
            # Use a chatter message targeted only to this partner so they get
            # the standard "View Approval Request" style email once.
            request.message_post(
                body=_('You have been assigned to approve the request "%s".') % (request.name,),
                subject=_('Approval Request Assigned: %s') % (request.name,),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
                partner_ids=[partner.id],
            )
    
    def action_approve(self, approver=None):
        """Override to clear activities for both delegate and delegator and handle batching"""
        # Before approving, collect all users whose activities should be cleared
        users_to_clear = set()
        
        for approver_rec in self:
            # Add the assigned user (delegate)
            if approver_rec.user_id:
                users_to_clear.add(approver_rec.user_id.id)
            
            # Add the delegator
            if approver_rec.delegated_by_id:
                users_to_clear.add(approver_rec.delegated_by_id.id)
            
            # If current user is approving, also clear activities for any other approvers
            # they are delegating for (they might be delegate for multiple people in same request)
            current_user = self.env.user
            delegation_model = self.env['approval.delegation']
            category_id = approver_rec.request_id.category_id if approver_rec.request_id.category_id else None
            
            # Find all approvers in this request where current user is either the delegate or delegator
            for other_approver in approver_rec.request_id.approver_ids:
                # If current user is the assigned user (delegate) for this approver
                if other_approver.user_id == current_user and other_approver.status in ['pending', 'waiting']:
                    if other_approver.user_id:
                        users_to_clear.add(other_approver.user_id.id)
                    if other_approver.delegated_by_id:
                        users_to_clear.add(other_approver.delegated_by_id.id)
                
                # If current user is the delegator for this approver
                if other_approver.delegated_by_id == current_user and other_approver.status in ['pending', 'waiting']:
                    if other_approver.user_id:
                        users_to_clear.add(other_approver.user_id.id)
                    if other_approver.delegated_by_id:
                        users_to_clear.add(other_approver.delegated_by_id.id)
        
        # Call parent action_approve
        result = super().action_approve(approver=approver)
        
        # After approval, activate all non-required approvers with the same sequence as the next approver
        for approver_rec in self:
            if approver_rec.status == 'approved':
                approver_rec._activate_batch_approvers()
        
        # Clear activities for all identified users
        for approver_rec in self:
            for user_id in users_to_clear:
                activities = self.env['mail.activity'].search([
                    ('res_id', '=', approver_rec.request_id.id),
                    ('res_model', '=', 'approval.request'),
                    ('user_id', '=', user_id),
                    ('activity_type_id', '=', self.env.ref('approvals.mail_activity_data_approval').id)
                ])
                activities.action_done()
        
        return result
    
    def _activate_batch_approvers(self):
        """Activate all approvers with the same sequence (batch non-required approvers)"""
        self.ensure_one()
        
        # Get all waiting approvers for this request, sorted by sequence
        waiting_approvers = self.request_id.approver_ids.filtered(
            lambda a: a.status == 'waiting'
        ).sorted('sequence')
        
        if not waiting_approvers:
            return
        
        # Get the next sequence (sequence of first waiting approver)
        next_sequence = waiting_approvers[0].sequence
        
        # Get all approvers with this sequence
        batch_approvers = waiting_approvers.filtered(lambda a: a.sequence == next_sequence)
        
        # Activate all of them at once
        if batch_approvers:
            batch_approvers.write({'status': 'pending'})
    
    def _can_approve(self):
        """Override to check if current user can approve (directly, as delegator, or via delegation)"""
        self.ensure_one()
        current_user = self.env.user
        
        # Check if current user is the assigned approver
        if self.user_id == current_user:
            return True
        
        # Check if current user is the delegator (original approver)
        if self.status == 'pending' and self.delegated_by_id == current_user:
            return True
        
        # Check if current user is a delegate for this approver
        if self.status == 'pending' and self.user_id:
            delegation_model = self.env['approval.delegation']
            category_id = self.request_id.category_id.id if self.request_id.category_id else None
            delegation = delegation_model.get_active_delegation(
                self.user_id.id,
                category_id
            )
            if delegation:
                return True
        
        return False
    
    @api.depends('user_id', 'request_id', 'request_id.company_id.cfo_id', 'request_id.company_id.senior_approver_id', 'request_id.company_id.ceo_id', 'delegated_by_id')
    def _compute_approval_role(self):
        """Determine if this approver is CFO, Senior Approver, CEO, or Reviewer"""
        for approver in self:
            role = ''
            if not approver.request_id or not approver.user_id:
                approver.approval_role = role
                continue
                
            request = approver.request_id
            user = approver.user_id
            
            # Determine the actual role holder (either current user or the delegator)
            role_user = approver.delegated_by_id if approver.delegated_by_id else user
            
            # Check if role_user is CFO
            if hasattr(request.company_id, 'cfo_id') and request.company_id.cfo_id and role_user.id == request.company_id.cfo_id.id:
                role = 'CFO (Approved by)'
            # Check if role_user is Senior Approver
            elif hasattr(request.company_id, 'senior_approver_id') and request.company_id.senior_approver_id and role_user.id == request.company_id.senior_approver_id.id:
                role = 'CEO Office (Pre-authorization)'
            # Check if role_user is CEO
            elif hasattr(request.company_id, 'ceo_id') and request.company_id.ceo_id and role_user.id == request.company_id.ceo_id.id:
                role = 'CEO (Authorized by)'
            # Treat optional approvers as Reviewers
            elif hasattr(request, 'optional_approver_ids') and request.optional_approver_ids and role_user.id in request.optional_approver_ids.mapped('user_id').ids:
                role = 'Reviewer (Reviewed by)'
            else:
                # Check if role_user is reviewer (department manager or employee's parent manager)
                requester = request.request_owner_id or request.create_uid
                if requester:
                    dept_manager_user = False
                    try:
                        emp = requester.employee_id if hasattr(requester, 'employee_id') else False
                        dept = emp.department_id if emp and hasattr(emp, 'department_id') else False
                        manager = dept.manager_id if dept and hasattr(dept, 'manager_id') else False
                        dept_manager_user = manager.user_id if manager and hasattr(manager, 'user_id') else False
                    except Exception:
                        dept_manager_user = False
                    
                    parent_manager_user = False
                    try:
                        emp = requester.employee_id if hasattr(requester, 'employee_id') else False
                        parent = emp.parent_id if emp and hasattr(emp, 'parent_id') else False
                        parent_manager_user = parent.user_id if parent and hasattr(parent, 'user_id') else False
                    except Exception:
                        parent_manager_user = False
                    reviewer = parent_manager_user or dept_manager_user
                    if reviewer and role_user.id == reviewer.id:
                        role = 'Reviewer (Reviewed by)'
            
            # Add "For [Delegator]" suffix if this is a delegation
            if approver.delegated_by_id:
                role = f"{role} - For {approver.delegated_by_id.name}"
            
            approver.approval_role = role


class ApprovalChecklistLine(models.Model):
    _name = 'approval.checklist.line'
    _description = 'Approval Checklist Line'

    request_id = fields.Many2one('approval.request', string='Approval Request', ondelete='cascade', required=True)
    name = fields.Char(string='Item', required=True)
    is_required = fields.Boolean(string='Required', default=True)
    document_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='approval_checklist_line_attachment_rel',
        column1='line_id',
        column2='attachment_id',
        string='Attachments',
        help='Upload supporting documents for this checklist item.'
    )

    def _link_attachments_to_request(self):
        for line in self:
            if line.request_id and line.document_ids:
                line.document_ids.sudo().write({
                    'res_model': 'approval.request',
                    'res_id': line.request_id.id,
                })

    def write(self, vals):
        res = super().write(vals)
        if 'document_ids' in vals or 'request_id' in vals:
            self._link_attachments_to_request()
        return res

class ApprovalOptionalApprover(models.Model):
    _name = 'approval.optional.approver'
    _description = 'Approval Optional Approver'
    _order = 'sequence asc, id asc'

    request_id = fields.Many2one('approval.request', string='Request', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    required = fields.Boolean(string='Required', default=True, help='If checked, this approver must approve before the request can be approved')


class ApprovalContractPriceLine(models.Model):
    _name = 'approval.contract.price.line'
    _description = 'Approval Contract Price Line'
    _order = 'id'

    request_id = fields.Many2one('approval.request', string='Approval Request', required=True, ondelete='cascade')
    serial_number_per_contract = fields.Char(string='S/N Per Contract')
    item_name_per_contract = fields.Char(string='Item Name Per Contract', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, digits=(16, 2))
    unit_price_vat_exclusive = fields.Float(string='Unit Price (VAT Exclusive)', digits=(16, 2), required=True)
    tax_rate = fields.Selection(
        selection=[
            ('0', '0%'),
            ('18', '18%'),
        ],
        string='Tax',
        required=True,
        help='Select the applicable tax rate for this item'
    )
    unit_price_vat_inclusive = fields.Float(
        string='Unit Price (VAT Inclusive)', 
        compute='_compute_vat_inclusive_prices',
        store=True,
        digits=(16, 2)
    )
    total_price_vat_exclusive = fields.Float(
        string='Total Price (VAT Exclusive)',
        compute='_compute_total_prices',
        store=True,
        digits=(16, 2)
    )
    total_price_vat_inclusive = fields.Float(
        string='Total Price (VAT Inclusive)',
        compute='_compute_total_prices',
        store=True,
        digits=(16, 2)
    )

    @api.depends('unit_price_vat_exclusive', 'tax_rate')
    def _compute_vat_inclusive_prices(self):
        """Calculate VAT inclusive prices based on VAT exclusive and selected tax rate"""
        for line in self:
            if line.unit_price_vat_exclusive and line.tax_rate:
                tax_multiplier = 1.0 + (float(line.tax_rate) / 100.0)
                line.unit_price_vat_inclusive = line.unit_price_vat_exclusive * tax_multiplier
            else:
                line.unit_price_vat_inclusive = line.unit_price_vat_exclusive or 0.0
    
    @api.depends('quantity', 'unit_price_vat_exclusive', 'unit_price_vat_inclusive')
    def _compute_total_prices(self):
        """Calculate total prices from unit prices and quantity"""
        for line in self:
            line.total_price_vat_exclusive = line.quantity * (line.unit_price_vat_exclusive or 0.0)
            line.total_price_vat_inclusive = line.quantity * (line.unit_price_vat_inclusive or 0.0)

