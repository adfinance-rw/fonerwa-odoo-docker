# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, datetime as dt


class ContractDeliverable(models.Model):
    _name = 'contract.deliverable'
    _description = 'Contract Deliverable'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc, deliverable_date asc'

    # Basic Information
    name = fields.Char(
        string='Deliverable Name',
        required=True,
        help='Short description of the deliverable (e.g., "Phase 1 Completion")'
    )

    description = fields.Text(
        string='Description',
        help='Detailed explanation of the deliverable'
    )

    contract_id = fields.Many2one(
        'contract.management',
        string='Linked Contract',
        required=True,
        ondelete='cascade',
        help='Reference to the parent contract'
    )

    # Dates and Status
    issue_date = fields.Date(
        string='Issue Date',
        required=True,
        default=fields.Date.today,
        help='Date when the deliverable was issued/created'
    )
    
    deliverable_date = fields.Date(
        string='Due Date',
        required=True,
        help='Deadline for deliverable completion'
    )

    status = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending')

    # Deliverables and Responsibilities
    deliverable = fields.Text(
        string='Deliverable',
        help='Description of what needs to be delivered'
    )

    # Payment Information
    payment_amount = fields.Monetary(
        string='Payment Amount',
        currency_field='currency_id',
        help='Amount to be released upon deliverable completion'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        domain=[('name', 'in', ['RWF', 'USD', 'EUR'])],
        default=lambda self: self._get_default_currency(),
        help='Select the currency for the payment amount (RWF, USD, or EUR)'
    )
    
    @api.model
    def _get_default_currency(self):
        """Get default currency from contract if available"""
        if self.env.context.get('default_contract_id'):
            contract = self.env['contract.management'].browse(
                self.env.context['default_contract_id'])
            return contract.currency_id.id if contract.currency_id else False
        return False

    # Alert Configuration
    alert_days_before = fields.Integer(
        string='Alert Days Before',
        default=30,
        help='Number of days before deliverable due date to start sending '
             'daily email alerts. Emails will be sent daily until the '
             'deliverable is completed or overdue.'
    )

    alert_sent = fields.Boolean(
        string='Alert Sent',
        default=False,
        help='Indicates if alert notification email has been sent'
    )

    last_alert_date = fields.Datetime(
        string='Last Alert Date',
        help='Date and time when the last reminder email was sent'
    )

    # Completion Tracking
    completion_date = fields.Date(
        string='Completion Date',
        help='Actual date when deliverable was completed'
    )

    completion_notes = fields.Text(
        string='Completion Notes',
        help='Notes about deliverable completion'
    )

    proof_of_completion = fields.Binary(
        string='Proof of Completion',
        help='Upload proof/documentation of deliverable completion'
    )

    proof_of_completion_filename = fields.Char(
        string='Proof of Completion Filename'
    )

    # Computed Fields
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        store=True
    )

    days_until_due = fields.Integer(
        string='Days Until Due',
        compute='_compute_days_until_due'
    )

    # Contract Information (for easy access)
    contract_number = fields.Char(
        string='Contract Number',
        related='contract_id.contract_number',
        store=True
    )

    contract_name = fields.Char(
        string='Contract Name',
        related='contract_id.name',
        store=True
    )

    contract_manager_id = fields.Many2one(
        'res.users',
        string='Contract Manager',
        related='contract_id.contract_manager_id',
        store=True
    )

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        """Set default currency when contract is selected"""
        if self.contract_id and self.contract_id.currency_id:
            self.currency_id = self.contract_id.currency_id

    @api.depends('deliverable_date', 'status')
    def _compute_is_overdue(self):
        """Compute if deliverable is overdue"""
        today = fields.Date.today()
        for deliverable in self:
            if (deliverable.deliverable_date and
                    isinstance(deliverable.deliverable_date, date)):
                deliverable.is_overdue = (
                    deliverable.status == 'pending' and
                    deliverable.deliverable_date < today
                )
            else:
                deliverable.is_overdue = False

    @api.constrains('deliverable_date', 'issue_date', 'contract_id')
    def _check_deliverable_date_range(self):
        """Validate that deliverable date falls within contract date range and is after issue date"""
        for deliverable in self:
            # Validate issue_date is before deliverable_date
            if deliverable.issue_date and deliverable.deliverable_date:
                if deliverable.deliverable_date < deliverable.issue_date:
                    raise UserError(
                        _('Deliverable due date (%s) cannot be before the issue date (%s).') % (
                            deliverable.deliverable_date,
                            deliverable.issue_date
                        ))
            
            # Validate deliverable date falls within contract date range
            if deliverable.contract_id and deliverable.deliverable_date:
                contract = deliverable.contract_id
                if not contract.effective_date or not contract.expiry_date:
                    continue  # Skip validation if contract dates not set
                if (deliverable.deliverable_date < contract.effective_date or
                        deliverable.deliverable_date > contract.expiry_date):
                    raise UserError(
                        _('Deliverable due date (%s) must fall within the '
                          'contract date range (%s to %s).') % (
                            deliverable.deliverable_date,
                            contract.effective_date,
                            contract.expiry_date
                        ))

    @api.depends('deliverable_date')
    def _compute_days_until_due(self):
        """Compute days until deliverable is due"""
        today = fields.Date.today()
        for deliverable in self:
            if (deliverable.deliverable_date and
                    isinstance(deliverable.deliverable_date, date)):
                delta = deliverable.deliverable_date - today
                deliverable.days_until_due = delta.days
            else:
                deliverable.days_until_due = 0

    # Action Methods
    def action_mark_completed(self):
        """Mark deliverable as completed"""
        self.ensure_one()
        self.write({
            'status': 'completed',
            'completion_date': fields.Date.today()
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deliverable Completed'),
                'message': _(
                    'Deliverable "%s" has been marked as completed.') % (
                    self.name),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_mark_cancelled(self):
        """Mark deliverable as cancelled"""
        self.write({'status': 'cancelled'})

    def action_send_alert(self):
        """Send deliverable alert (UR-05)"""
        now = fields.Datetime.now()
        self.write({
            'alert_sent': True,
            'last_alert_date': now
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Deliverable Alert Sent',
                'message': (
                    f'Alert sent for deliverable "{self.name}" '
                    f'due on {self.deliverable_date}.'
                ),
                'type': 'success',
            }
        }

    def action_view_contract(self):
        """View the linked contract"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Contract {self.contract_number}',
            'res_model': 'contract.management',
            'res_id': self.contract_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _validate_deliverable_amounts(self, vals):
        """Validate deliverable amounts stay within the contract value"""
        for deliverable in self:
            contract = deliverable.contract_id
            if not contract:
                continue
            
            # Get the payment amount from vals or existing deliverable
            payment_amount = (
                vals.get('payment_amount', deliverable.payment_amount) or 0)
            
            # Skip validation if payment_amount is zero or not set
            if not payment_amount or payment_amount <= 0:
                continue
            
            # Validate individual deliverable amount doesn't exceed contract
            # value
            if contract.contract_value and payment_amount > contract.contract_value:
                raise UserError(
                    _('Deliverable amount (%.2f) cannot exceed the contract '
                      'value (%.2f). Please adjust the amount.')
                    % (payment_amount, contract.contract_value))
            
            # Validate total of all deliverable amounts doesn't exceed contract
            # value
            if contract.contract_value:
                # Calculate sum of all deliverable amounts for this contract
                all_deliverables = contract.deliverable_ids
                
                # Sum all deliverable amounts (excluding current deliverable if
                # updating)
                total_deliverable_amount = sum(
                    d.payment_amount or 0
                    for d in all_deliverables
                    if d.id != deliverable.id
                )
                
                # Add the new/updated deliverable amount
                total_deliverable_amount += payment_amount
                
                # Check if total exceeds contract value
                if total_deliverable_amount > contract.contract_value:
                    raise UserError(
                        _('The total of all deliverable amounts (%.2f) cannot '
                          'exceed the contract value (%.2f). Please adjust '
                          'the amounts.')
                        % (total_deliverable_amount, contract.contract_value))

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to validate deliverable amounts and contract state"""
        # Set default issue_date if not provided
        for vals in vals_list:
            if 'issue_date' not in vals:
                vals['issue_date'] = fields.Date.today()
        
        # Check if contract is in draft state and validate date range
        for vals in vals_list:
            if 'contract_id' in vals:
                contract = self.env['contract.management'].browse(
                    vals['contract_id'])
                if contract.state == 'draft':
                    raise UserError(
                        _('Cannot add deliverables to a contract in draft '
                          'state. Please activate the contract first.'))
                # Validate deliverable date is within contract date range
                if 'deliverable_date' in vals and contract.effective_date and \
                        contract.expiry_date:
                    deliverable_date = vals['deliverable_date']
                    # Convert string to date if needed
                    if deliverable_date:
                        if isinstance(deliverable_date, str):
                            # Parse string date (format: YYYY-MM-DD)
                            try:
                                deliverable_date = dt.strptime(
                                    deliverable_date, '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                # If parsing fails, skip validation
                                deliverable_date = None
                        elif not isinstance(deliverable_date, date):
                            # Try to convert if it's a datetime
                            if hasattr(deliverable_date, 'date'):
                                deliverable_date = deliverable_date.date()
                            else:
                                deliverable_date = None
                        # Now compare dates
                        if deliverable_date and isinstance(deliverable_date, date):
                            if (deliverable_date < contract.effective_date or
                                    deliverable_date > contract.expiry_date):
                                raise UserError(
                                    _('Deliverable due date (%s) must fall '
                                      'within the contract date range (%s to '
                                      '%s).') % (
                                        deliverable_date,
                                        contract.effective_date,
                                        contract.expiry_date
                                    ))
        
        # Validate payment amounts before creation
        # Group by contract_id to handle batch creation properly
        contracts_totals = {}
        for vals in vals_list:
            if 'contract_id' in vals:
                contract_id = vals['contract_id']
                contract = self.env['contract.management'].browse(contract_id)
                payment_amount = vals.get('payment_amount', 0) or 0
                
                # Validate individual amount doesn't exceed contract value
                if payment_amount > 0:
                    if contract.contract_value and \
                            payment_amount > contract.contract_value:
                        raise UserError(
                            _('Deliverable amount (%.2f) cannot exceed the '
                              'contract value (%.2f). Please adjust the '
                              'amount.')
                            % (payment_amount, contract.contract_value))
                    
                    # Track totals per contract for batch validation
                    if contract_id not in contracts_totals:
                        # Get all existing deliverables for this contract
                        existing_deliverables = contract.deliverable_ids
                        total_existing = sum(
                            d.payment_amount or 0
                            for d in existing_deliverables
                        )
                        contracts_totals[contract_id] = {
                            'contract': contract,
                            'total_existing': total_existing,
                            'total_new': 0
                        }
                    
                    contracts_totals[contract_id]['total_new'] += \
                        payment_amount
        
        # Validate totals for each contract
        for contract_id, totals_info in contracts_totals.items():
            contract = totals_info['contract']
            total_existing = totals_info['total_existing']
            total_new = totals_info['total_new']
            total_with_new = total_existing + total_new
            
            if contract.contract_value and total_with_new > contract.contract_value:
                raise UserError(
                    _('The total of all deliverable amounts (%.2f) cannot '
                      'exceed the contract value (%.2f). Current total: %.2f. '
                      'Please adjust the amounts.')
                    % (total_with_new, contract.contract_value,
                       total_existing))
        
        deliverables = super().create(vals_list)
        
        for deliverable in deliverables:
            # Double check contract state after creation
            if deliverable.contract_id.state == 'draft':
                raise UserError(
                    _('Cannot add deliverables to a contract in draft state. '
                      'Please activate the contract first.'))
            # Validate amounts after creation (in case payment_amount wasn't
            # in vals)
            deliverable._validate_deliverable_amounts({})
        
        return deliverables

    def write(self, vals):
        """Override write to validate deliverable amounts and date range"""
        # Validate deliverable date is within contract date range if being updated
        if 'deliverable_date' in vals or 'contract_id' in vals:
            for deliverable in self:
                # Get contract - use new one if contract_id is being changed
                contract = self.env['contract.management'].browse(
                    vals.get('contract_id', deliverable.contract_id.id))
                # Get deliverable date - use new one if deliverable_date is being changed
                deliverable_date = vals.get(
                    'deliverable_date', deliverable.deliverable_date)
                
                # Convert string to date if needed
                if deliverable_date:
                    if isinstance(deliverable_date, str):
                        # Parse string date (format: YYYY-MM-DD)
                        try:
                            deliverable_date = dt.strptime(
                                deliverable_date, '%Y-%m-%d').date()
                        except (ValueError, TypeError):
                            # If parsing fails, skip validation
                            deliverable_date = None
                    elif not isinstance(deliverable_date, date):
                        # Try to convert if it's a datetime
                        if hasattr(deliverable_date, 'date'):
                            deliverable_date = deliverable_date.date()
                        else:
                            deliverable_date = None
                
                if contract and deliverable_date and \
                        contract.effective_date and contract.expiry_date:
                    if isinstance(deliverable_date, date):
                        if (deliverable_date < contract.effective_date or
                                deliverable_date > contract.expiry_date):
                            raise UserError(
                                _('Deliverable due date (%s) must fall within '
                                  'the contract date range (%s to %s).') % (
                                    deliverable_date,
                                    contract.effective_date,
                                    contract.expiry_date
                                ))
        # Validate payment amount if it's being changed
        if 'payment_amount' in vals:
            self._validate_deliverable_amounts(vals)
        
        return super().write(vals)

    def send_deliverable_expiration_notification(self, force_send=True):
        """Send email notification when deliverable is about to expire"""
        self.ensure_one()
        import logging
        _logger = logging.getLogger(__name__)
        
        # Get the responsible user (contract manager)
        assigned_user = (
            self.contract_manager_id
            or self.contract_id.contract_manager_id
        )
        
        if not assigned_user:
            _logger.warning(
                'Deliverable %s: No contract manager assigned',
                self.name or 'N/A'
            )
            return False
        
        if not assigned_user.email:
            _logger.warning(
                'Deliverable %s: Contract manager %s has no email address',
                self.name or 'N/A',
                assigned_user.name
            )
            return False
        
        _logger.info(
            'Deliverable %s: Attempting to send notification to %s',
            self.name or 'N/A',
            assigned_user.email
        )
        
        # Get email template
        template = self.env.ref(
            'contract_management.email_template_deliverable_expiration', False)
        if not template:
            _logger.warning(
                'Deliverable %s: Email template not found, using fallback',
                self.name or 'N/A'
            )
            # Fallback: send email manually if template doesn't exist
            result = self._send_deliverable_email_manual(assigned_user)
        else:
            _logger.info(
                'Deliverable %s: Using email template %s',
                self.name or 'N/A',
                template.name
            )
            # Use email template
            try:
                template.send_mail(self.id, force_send=force_send)
                result = True
                _logger.info(
                    'Deliverable %s: Email sent via template',
                    self.name or 'N/A'
                )
            except Exception as e:
                _logger.error(
                    'Deliverable %s: Failed to send email via template: %s',
                    self.name or 'N/A',
                    str(e),
                    exc_info=True
                )
                result = False
        
        if result:
            # Mark alert as sent and update last alert date
            self.write({
                'alert_sent': True,
                'last_alert_date': fields.Datetime.now()
            })
            _logger.info(
                'Deliverable %s: Notification marked as sent',
                self.name or 'N/A'
            )
        
        return result

    def _send_deliverable_email_manual(self, assigned_user):
        """Send deliverable expiration email manually if template is not available"""
        self.ensure_one()

        if not assigned_user or not assigned_user.email:
            return False

        # Prepare email content
        subject = _('Deliverable Expiration Notice: %s') % self.name
        deliverable_date_str = (
            self.deliverable_date.strftime('%Y-%m-%d')
            if self.deliverable_date else 'N/A'
        )
        contract_name = (
            self.contract_id.name if self.contract_id else 'N/A'
        )
        contract_number = (
            self.contract_id.contract_number if self.contract_id else 'N/A'
        )
        currency_name = (
            self.currency_id.name if self.currency_id else ''
        )
        
        body_html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2 style="color: #875A7B;">Deliverable Expiration Notice</h2>
            <p>Dear {assigned_user.name},</p>
            <p>This is to notify you that the following deliverable is
            expiring soon:</p>
            <table style="border-collapse: collapse; width: 100%;
            margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Deliverable Name:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {self.name or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Contract Number:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {contract_number}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Contract Title:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {contract_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Due Date:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    color: #d9534f; font-weight: bold;">
                    {deliverable_date_str}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Days Until Due:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    color: #d9534f; font-weight: bold;">
                    {self.days_until_due} days</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Payment Amount:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {self.payment_amount or 0.0} {currency_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Deliverable:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {self.deliverable or 'N/A'}</td>
                </tr>
            </table>
            <p style="color: #d9534f; font-weight: bold;">Please take
            necessary action to complete this deliverable before it
            expires.</p>
            <p>Best regards,<br/>Contract Management System</p>
        </div>
        """
        
        # Create and send mail
        mail_values = {
            'subject': subject,
            'body_html': body_html,
            'email_to': assigned_user.email,
            'email_from': self.env.user.email or self.env.company.email,
            'model': self._name,
            'res_id': self.id,
        }
        
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()
        
        return True

    def action_test_send_deliverable_email(self):
        """Manually test sending deliverable expiration email (for testing purposes)"""
        self.ensure_one()
        
        # Get the responsible user
        assigned_user = (
            self.contract_manager_id
            or self.contract_id.contract_manager_id
        )
        
        if not assigned_user:
            raise UserError(_('No contract manager assigned to this deliverable.'))
        
        if not assigned_user.email:
            raise UserError(_('Contract manager %s has no email address.') % assigned_user.name)
        
        # For testing: Clear last_alert_date to allow sending even if sent today
        # This allows testing without waiting for the next day
        if self.last_alert_date:
            self.write({
                'last_alert_date': False,
                'alert_sent': False
            })
        
        # Send the email
        result = self.send_deliverable_expiration_notification()
        
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email Sent Successfully'),
                    'message': _('Deliverable expiration notification email has been sent to %s') % assigned_user.email,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_('Failed to send deliverable expiration notification email. Please check the logs for details.'))





    def action_reset_alert_date(self):
        """Reset alert date for testing purposes"""
        self.ensure_one()
        self.write({
            'last_alert_date': False,
            'alert_sent': False
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Alert Date Reset'),
                'message': _('Alert date has been reset. You can now test sending emails again.'),
                'type': 'success',
                'sticky': False,
            }
        }

