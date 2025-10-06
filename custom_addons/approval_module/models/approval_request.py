# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApprovalRequest(models.Model):

    _inherit = "approval.request"
    
    # Display fields to show approval roles clearly
    cfo_approver_id = fields.Many2one(
        'approval.approver', 
        string='CFO Approval',
        compute='_compute_role_approvers',
        help='Chief Finance Officer approval status'
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
    
    @api.depends('approver_ids', 'approver_ids.user_id', 'approver_ids.status')
    def _compute_role_approvers(self):
        """Compute which approver corresponds to which role (CFO, CEO, Reviewer)"""
        for request in self:
            cfo = request.company_id.cfo_id if hasattr(request.company_id, 'cfo_id') else False
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
            request.ceo_approver_id = request.approver_ids.filtered(lambda a: ceo and a.user_id.id == ceo.id)[:1] if ceo else False
            request.reviewer_approver_id = request.approver_ids.filtered(lambda a: reviewer and a.user_id.id == reviewer.id)[:1] if reviewer else False
    
    # Storage field (kept for logic/validation)
    payment_type = fields.Selection([
        ("services", "Payment for Services"),
        ("goods", "Payment for Goods"),
        ("works", "Payment for Works"),
        ("disbursement", "Support/Transfer to Project (Disbursement)"),
        ("mission", "Mission Allowance and Air Ticket"),
        ("board_allowance", "Board Sitting Allowance and Communication"),
        ("refund", "Payment of Refund"),
        ("other", "Other Payment"),
    ], string="Payment Type")

    # UI helper fields to display only allowed choices per kind
    invoice_payment_type = fields.Selection([
        ("services", "Payment for Services"),
        ("goods", "Payment for Goods"),
        ("works", "Payment for Works"),
    ], string="Payment Type (Invoice)")

    other_payment_type = fields.Selection([
        ("disbursement", "Support/Transfer to Project (Disbursement)"),
        ("mission", "Mission Allowance and Air Ticket"),
        ("board_allowance", "Board Sitting Allowance and Communication"),
        ("refund", "Payment of Refund"),
        ("other", "Other Payment"),
    ], string="Payment Type (Other)")

    purchase_type = fields.Selection([
        ("services", "Purchase for Services"),
        ("goods", "Purchase for Goods"),
        ("works", "Purchase for Works"),
    ], string="Purchase Type")

    po_exceeds_10m = fields.Boolean(string='PO exceeds 10 million')
    po_exceeds_20m = fields.Boolean(string='PO exceeds 20 million (Guarantee Required)')


    checklist_line_ids = fields.One2many(
        comodel_name="approval.checklist.line",
        inverse_name="request_id",
        string="Checklist Items",
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

    @api.onchange('category_id')
    def _onchange_category_id(self):
        # Reset dependent fields and approvers
        for rec in self:
            if rec.category_type == 'purchase_order':
                rec.payment_type = False
                rec.invoice_payment_type = False
                rec.other_payment_type = False
            else:
                rec.purchase_type = False

        # Auto-populate approvers depending on category and requester
        self._populate_default_approvers()

    @api.onchange('invoice_payment_type')
    def _onchange_invoice_payment_type(self):
        if self.category_type == 'invoice_payment':
            self.payment_type = self.invoice_payment_type
            self._onchange_payment_type_populate_checklist()

    @api.onchange('other_payment_type')
    def _onchange_other_payment_type(self):
        if self.category_type == 'other_payment':
            self.payment_type = self.other_payment_type
            self._onchange_payment_type_populate_checklist()

    @api.onchange('amount')
    def _onchange_amount(self):
        """Trigger approver population when amount changes"""
        if self.category_type == 'invoice_payment':
            self._populate_default_approvers()
    
    @api.onchange('po_exceeds_10m')
    def _onchange_po_exceeds_10m(self):
        """For Purchase Orders, toggle CEO approver based on this checkbox"""
        if self.category_type == 'purchase_order':
            self._populate_default_approvers()

    @api.onchange('payment_type', 'purchase_type', 'po_exceeds_20m', 'amount')
    def _onchange_payment_type_populate_checklist(self):
        if self.category_type == 'purchase_order':
            # Populate purchase order checklist based on purchase_type
            self.checklist_line_ids = [fields.Command.clear()]
            if not self.purchase_type:
                return
            items_common = [
                'Contract',
                'Contract negotiation minutes',
            ]
            items = list(items_common)
            if self.po_exceeds_20m:
                items.append('Performance guarantee (threshold exceeds 20 million)')
            self.checklist_line_ids = [fields.Command.create({'name': name, 'is_required': True}) for name in items]
            return

        # When category type is invoice/other payment, ensure selected payment_type is allowed
        allowed_map = {
            'invoice_payment': {'services', 'goods', 'works'},
            'other_payment': {'disbursement', 'mission', 'board_allowance', 'refund', 'other'},
        }

        if not self.payment_type:
            self.checklist_line_ids = [fields.Command.clear()]
            return

        if self.category_type in allowed_map and self.payment_type not in allowed_map[self.category_type]:
            # Reset invalid choice and clear checklist
            self.payment_type = False
            self.checklist_line_ids = [fields.Command.clear()]
            return

        def lines(item_names):
            return [fields.Command.create({
                'name': item_name,
                'is_required': True,
            }) for item_name in item_names]

        checklist_map = {
            'services': [
                'EBM invoice (local contractor/supplier/consultant)',
                'Purchase Order',
                'RRA Tax declaration previous period (CIT/PIT)',
                'Attendance list for participants',
                'Approved list of project beneficiaries (grants to local population)',
                'Report (consultancy service)',
                'Feuille de route / Mission order / Request & PO (transport service)',
                'Approved driver report by logistics (transport service for staff in Kigali)',
                'Quitus Fiscal (when applicable)'
            ],
            'goods': [
                'EBM invoice (local contractor/supplier/consultant)',
                'Purchase Order',
                'Delivery note signed (Supplier & Reception committee) / Consultancy approved report',
                'Goods received note (Approved by Reception Committee)',
                'RRA Tax declaration previous period (CIT/PIT)',
                'Quitus Fiscal (when applicable)'
            ],
            'works': [
                'EBM invoice (local contractor)',
                'Work Order',
                'Approved progress report of work done',
                'Supervision Report (contracts above 50 million)',
                'Final handover / Certificate of completion',
                'RRA Tax declaration previous period (CIT/PIT)',
                'Quitus Fiscal (when applicable)'
            ],
            'disbursement': [
                'Add a disbursement request',
                'Next workplan',
                'Spot check report (if second request)',
                'Financial statement report (Budget execution, bank reconciliation, bank statement, cash book)',
                'Financing Agreement',
                'Any other document explaining the disbursement request'
            ],
            'mission': [
                'Signed Mission order (Domestic or International)',
                'Approved Concept paper / Invitation',
                'Rwandair Proforma invoice (payment of Air Ticket)',
                'Copy of air ticket',
                'Mission report (as per law)'
            ],
            'board_allowance': [
                'Attendance list of board meetings',
                'Approved payment request / pay list from HR',
                'List of board members to benefit from monthly communication from HR'
            ],
            'refund': [
                'Proof of receipt of payment'
            ],
            'other': [],
        }

        base_items = checklist_map.get(self.payment_type, [])
        items = list(base_items)
        
        # Add performance guarantee for Invoice Payment over 20M
        if self.category_type == 'invoice_payment' and self.amount and self.amount > 20000000:
            items.append('Performance guarantee (threshold exceeds 20 million)')

        self.checklist_line_ids = [fields.Command.clear()] + lines(items)

    @api.constrains('category_type', 'payment_type', 'purchase_type')
    def _check_kind_type_alignment(self):
        for rec in self:
            # Require specific type fields per category
            if rec.category_type == 'invoice_payment' and not rec.invoice_payment_type:
                raise ValidationError(_("Payment Type (Invoice) is required for Invoice Payment category."))
            if rec.category_type == 'other_payment' and not rec.other_payment_type:
                raise ValidationError(_("Payment Type (Other) is required for Other Payment category."))
            if rec.category_type == 'purchase_order' and not rec.purchase_type:
                raise ValidationError(_("Purchase Type is required for Purchase Order category."))

            if rec.category_type in ('invoice_payment', 'other_payment') and rec.purchase_type:
                raise ValidationError(_("Purchase Type is only for Purchase Order categories."))
            if rec.category_type == 'purchase_order' and rec.payment_type:
                raise ValidationError(_("Payment Type is only for Invoice/Other Payment categories."))

            # Enforce allowed payment types per category type
            if rec.category_type == 'invoice_payment' and rec.payment_type and rec.payment_type not in {'services', 'goods', 'works'}:
                raise ValidationError(_("For Invoice Payment categories, Payment Type must be Services, Goods or Works."))
            if rec.category_type == 'other_payment' and rec.payment_type and rec.payment_type not in {'disbursement', 'mission', 'board_allowance', 'refund', 'other'}:
                raise ValidationError(_("For Other Payment categories, Payment Type must be Disbursement, Mission, Board_allowance, Refund or Other."))

    def _raise_if_missing_required_documents(self):
        for request in self:
            missing_lines = request.checklist_line_ids.filtered(lambda l: l.is_required and not l.document_ids)
            if missing_lines:
                names = ", ".join(missing_lines.mapped('name'))
                raise ValidationError(_(f"You must upload documents for required items: {names}"))

    def action_confirm(self):
        self._raise_if_missing_required_documents()

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

        return super().action_confirm()

    def _populate_default_approvers(self):
        """
        Populate approvers based on request kind, user type, and amount.
        
        Rules:
        - Normal User: Prepared by → Reviewed by (Line Manager) → Approved by (CFO) → Authorized by (CEO)
        - Specialist (no line manager): Prepared by → Approved by (CFO) → Authorized by (CEO)
        
        Request Kind Rules:
        - Purchase Order: CFO → CEO
        - Invoice Payment (≤10M): CFO only
        - Invoice Payment (>10M): CFO → CEO
        - Other Payment: CFO → CEO
        """
        # Defensive: only proceed if target field exists and structure is compatible
        if 'approver_ids' not in self._fields:
            return
        approver_field = self._fields['approver_ids']
        line_model = approver_field.comodel_name
        line_model_fields = self.env[line_model].fields_get()

        def approver_line(user, sequence=1):
            vals = {}
            if 'user_id' in line_model_fields:
                vals['user_id'] = user.id
            if 'required' in line_model_fields:
                vals['required'] = True
            if 'sequence' in line_model_fields:
                vals['sequence'] = sequence
            return vals

        for request in self:
            commands = []
            seq = 1
            added_user_ids = set()

            # Prepared by: the request owner (no approver line needed typically)
            requester = getattr(request, 'request_owner_id', False) or request.create_uid
            if not requester:
                continue

            # Get company CFO and CEO
            cfo = request.company_id.cfo_id if hasattr(request.company_id, 'cfo_id') else False
            ceo = request.company_id.ceo_id if hasattr(request.company_id, 'ceo_id') else False

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

            # Step 1: Add Reviewer if not a specialist and not already added
            if not is_specialist and reviewer and reviewer.id not in added_user_ids:
                lm_vals = approver_line(reviewer, seq)
                if lm_vals and lm_vals.get('user_id'):
                    commands.append(fields.Command.create(lm_vals))
                    added_user_ids.add(reviewer.id)
                    seq += 1

            # Step 2: Determine approval flow based on category type and amount
            needs_ceo = True  # Default: needs CEO authorization
            
            if request.category_type == 'invoice_payment':
                # Check amount for invoice payments
                amount = request.amount or 0
                if amount <= 10000000:  # 10M or less
                    needs_ceo = False
                # else: amount > 10M, needs CEO (default True)
            elif request.category_type == 'purchase_order':
                needs_ceo = bool(request.po_exceeds_10m)  # Always needs CEO
            elif request.category_type == 'other_payment':
                needs_ceo = True  # Always needs CEO
            else:
                # If no category_type set yet, default to needing CEO
                needs_ceo = True

            # Step 3: Add CFO (Approved by) if not already added
            if cfo and cfo.id not in added_user_ids:
                cfo_vals = approver_line(cfo, seq)
                if cfo_vals and cfo_vals.get('user_id'):
                    commands.append(fields.Command.create(cfo_vals))
                    added_user_ids.add(cfo.id)
                    seq += 1

            # Step 4: Add CEO (Authorized by) if needed and not already added
            if needs_ceo and ceo and ceo.id not in added_user_ids:
                ceo_vals = approver_line(ceo, seq)
                if ceo_vals and ceo_vals.get('user_id'):
                    commands.append(fields.Command.create(ceo_vals))
                    added_user_ids.add(ceo.id)
                    seq += 1

            if commands:
                request.approver_ids = [fields.Command.clear()] + commands


class ApprovalApprover(models.Model):
    _inherit = 'approval.approver'
    
    approval_role = fields.Char(
        string='Role',
        compute='_compute_approval_role',
        store=False,
        help='Shows the approval role (CFO, CEO, or Reviewer)'
    )
    
    @api.depends('user_id', 'request_id', 'request_id.company_id.cfo_id', 'request_id.company_id.ceo_id')
    def _compute_approval_role(self):
        """Determine if this approver is CFO, CEO, or Reviewer"""
        for approver in self:
            role = ''
            if not approver.request_id or not approver.user_id:
                approver.approval_role = role
                continue
                
            request = approver.request_id
            user = approver.user_id
            
            # Check if user is CFO
            if hasattr(request.company_id, 'cfo_id') and request.company_id.cfo_id and user.id == request.company_id.cfo_id.id:
                role = 'CFO (Approved by)'
            # Check if user is CEO
            elif hasattr(request.company_id, 'ceo_id') and request.company_id.ceo_id and user.id == request.company_id.ceo_id.id:
                role = 'CEO (Authorized by)'
            else:
                # Check if user is reviewer (department manager or employee's parent manager)
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
                    if reviewer and user.id == reviewer.id:
                        role = 'Reviewer (Reviewed by)'
            
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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._link_attachments_to_request()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'document_ids' in vals or 'request_id' in vals:
            self._link_attachments_to_request()
        return res