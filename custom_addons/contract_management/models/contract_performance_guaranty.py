# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta


class ContractPerformanceGuaranty(models.Model):
    _name = 'contract.performance.guaranty'
    _description = 'Contract Performance Guaranty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc, expiry_date desc'

    # Basic Information
    name = fields.Char(
        string='Performance Guaranty Name/Reference',
        required=True,
        tracking=True,
        help='Name or reference for this performance guaranty'
    )

    contract_id = fields.Many2one(
        'contract.management',
        string='Linked Contract',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Reference to the parent contract'
    )

    # Performance Guaranty Details
    performance_guaranty_type = fields.Selection([
        ('bank_guarantee', 'Bank Guarantee'),
        ('insurance_bond', 'Insurance Bond'),
        ('cash_deposit', 'Cash Deposit'),
        ('performance_bond', 'Performance Bond'),
        ('advance_payment_guarantee', 'Advance Payment Guarantee'),
        ('retention_bond', 'Retention Bond'),
        ('other', 'Other')
    ], string='Performance Guaranty Type', required=True, tracking=True)
    
    performance_guaranty_provider = fields.Char(
        string='Provider',
        required=True,
        tracking=True,
        help='Name of the bank, insurance company, or institution providing the guaranty'
    )

    performance_guaranty_amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Amount of performance guaranty/bond'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        domain=[('name', 'in', ['RWF', 'USD', 'EUR'])],
        default=lambda self: self._get_default_currency(),
        help='Select the currency for the performance guaranty amount (RWF, USD, or EUR)'
    )
    
    @api.model
    def _get_default_currency(self):
        """Get default currency from contract if available"""
        if self.env.context.get('default_contract_id'):
            contract = self.env['contract.management'].browse(
                self.env.context['default_contract_id'])
            return contract.currency_id.id if contract.currency_id else False
        return False
    
    # Dates
    issue_date = fields.Date(
        string='Issue Date',
        required=True,
        tracking=True,
        help='Date when the performance guaranty was issued'
    )
    
    expiry_date = fields.Date(
        string='Expiry Date',
        tracking=True,
        help='Date when the performance guaranty expires'
    )
    
    # Document Management
    performance_guaranty_document = fields.Binary(
        string='Performance Guaranty Document',
        tracking=True,
        help='Upload the performance guaranty document/certificate'
    )
    
    performance_guaranty_document_name = fields.Char(
        string='Document Name'
    )
    
    # Status and Notes
    status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('released', 'Released'),
        ('claimed', 'Claimed')
    ], string='Status', compute='_compute_status', store=True, tracking=True)
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the performance guaranty'
    )

    # Alert Configuration
    alert_days_before = fields.Integer(
        string='Alert Days Before',
        default=30,
        help='Number of days before performance guaranty expiry date to start sending '
             'daily email alerts. Emails will be sent daily until the '
             'performance guaranty expires or is released/claimed.'
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

    # Computed Fields
    days_to_expiry = fields.Integer(
        string='Days to Expiry',
        compute='_compute_days_to_expiry',
        search='_search_days_to_expiry'
    )

    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_status',
        store=True
    )

    @api.depends('expiry_date', 'status')
    def _compute_status(self):
        """Compute performance guaranty status based on expiry date"""
        today = fields.Date.today()
        for guaranty in self:
            if guaranty.status in ('released', 'claimed'):
                # Don't change status if already released or claimed
                continue
            elif not guaranty.expiry_date:
                guaranty.status = 'active'
                guaranty.is_expired = False
            elif guaranty.expiry_date < today:
                guaranty.status = 'expired'
                guaranty.is_expired = True
            else:
                guaranty.status = 'active'
                guaranty.is_expired = False

    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        """Compute days until performance guaranty expires"""
        today = fields.Date.today()
        for guaranty in self:
            if guaranty.expiry_date:
                delta = guaranty.expiry_date - today
                guaranty.days_to_expiry = delta.days
            else:
                guaranty.days_to_expiry = 0

    def _search_days_to_expiry(self, operator, value):
        """Search method for days_to_expiry computed field"""
        today = fields.Date.today()
        if operator == '<':
            # Find guaranties expiring in less than value days
            target_date = today + timedelta(days=value)
            return [('expiry_date', '<', target_date)]
        elif operator == '>':
            # Find guaranties expiring in more than value days
            target_date = today + timedelta(days=value)
            return [('expiry_date', '>', target_date)]
        elif operator in ['<=', '>=']:
            # Handle <= and >= operators
            target_date = today + timedelta(days=value)
            op = '<=' if operator == '<=' else '>='
            return [('expiry_date', op, target_date)]
        elif operator == '=':
            # Find guaranties expiring on exactly value days from now
            target_date = today + timedelta(days=value)
            return [('expiry_date', '=', target_date)]
        else:
            return [('id', 'in', [])]

    @api.constrains('expiry_date', 'issue_date')
    def _check_dates(self):
        """Validate that expiry date is after issue date"""
        for guaranty in self:
            if guaranty.issue_date and guaranty.expiry_date:
                if guaranty.expiry_date < guaranty.issue_date:
                    raise ValidationError(
                        _('Performance Guaranty expiry date cannot be before the issue date.')
                    )

    @api.constrains('contract_id')
    def _check_contract_state(self):
        """Validate that contract is not in draft state"""
        for guaranty in self:
            if guaranty.contract_id and guaranty.contract_id.state == 'draft':
                raise ValidationError(
                    _('Cannot add performance guaranty to a contract in draft state. '
                      'Please activate the contract first.')
                )

    def action_mark_released(self):
        """Mark performance guaranty as released"""
        self.ensure_one()
        self.write({'status': 'released'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Performance Guaranty Released'),
                'message': _('Performance Guaranty "%s" has been marked as released.') % self.name,
                'type': 'success',
            }
        }

    def action_mark_claimed(self):
        """Mark performance guaranty as claimed"""
        self.ensure_one()
        self.write({'status': 'claimed'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Performance Guaranty Claimed'),
                'message': _('Performance Guaranty "%s" has been marked as claimed.') % self.name,
                'type': 'warning',
            }
        }

    def action_download_document(self):
        """Download performance guaranty document"""
        if not self.performance_guaranty_document:
            raise UserError(_('No performance guaranty document available for download.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=contract.performance.guaranty&id={self.id}&field=performance_guaranty_document&filename_field=performance_guaranty_document_name&download=true',
            'target': 'self',
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

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to validate contract state"""
        for vals in vals_list:
            if 'contract_id' in vals:
                contract = self.env['contract.management'].browse(vals['contract_id'])
                if contract.state == 'draft':
                    raise UserError(
                        _('Cannot add performance guaranty to a contract in draft state. '
                          'Please activate the contract first.')
                    )
        return super().create(vals_list)

    def write(self, vals):
        """Override write to validate contract state"""
        if 'contract_id' in vals:
            for guaranty in self:
                contract = self.env['contract.management'].browse(vals['contract_id'])
                if contract.state == 'draft':
                    raise UserError(
                        _('Cannot move performance guaranty to a contract in draft state. '
                          'Please activate the contract first.')
                    )
        return super().write(vals)

    def send_performance_guaranty_expiration_notification(self, force_send=True):
        """Send email notification when performance guaranty is about to expire"""
        self.ensure_one()
        import logging
        _logger = logging.getLogger(__name__)
        
        # Get the responsible user (contract manager)
        assigned_user = self.contract_manager_id
        
        if not assigned_user:
            _logger.warning(
                'Performance Guaranty %s: No contract manager assigned',
                self.name or 'N/A'
            )
            return False
        
        if not assigned_user.email:
            _logger.warning(
                'Performance Guaranty %s: Contract manager %s has no email address',
                self.name or 'N/A',
                assigned_user.name
            )
            return False
        
        _logger.info(
            'Performance Guaranty %s: Attempting to send notification to %s',
            self.name or 'N/A',
            assigned_user.email
        )
        
        # Prepare email content
        subject = _('Performance Guaranty Expiration Notice: %s') % self.name
        expiry_date_str = (
            self.expiry_date.strftime('%Y-%m-%d')
            if self.expiry_date else 'N/A'
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
            <h2 style="color: #875A7B;">Performance Guaranty Expiration Notice</h2>
            <p>Dear {assigned_user.name},</p>
            <p>This is to notify you that the following performance guaranty is
            expiring soon:</p>
            <table style="border-collapse: collapse; width: 100%;
            margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Performance Guaranty Name:</td>
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
                    font-weight: bold;">Type:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {dict(self._fields['performance_guaranty_type'].selection).get(self.performance_guaranty_type, 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Provider:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {self.performance_guaranty_provider or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;
                    font-weight: bold;">Amount:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                    {self.performance_guaranty_amount or 0.0} {currency_name}</td>
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
            </table>
            <p style="color: #d9534f; font-weight: bold;">Please take
            necessary action to renew or extend this performance guaranty before it
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
        if force_send:
            mail.send()
        
        # Mark alert as sent and update last alert date
        self.write({
            'alert_sent': True,
            'last_alert_date': fields.Datetime.now()
        })
        _logger.info(
            'Performance Guaranty %s: Notification marked as sent',
            self.name or 'N/A'
        )
        
        return True

