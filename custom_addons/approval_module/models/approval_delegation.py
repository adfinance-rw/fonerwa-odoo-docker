# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class ApprovalDelegation(models.Model):
    """Allow approvers to delegate their approval authority to another user"""
    _name = 'approval.delegation'
    _description = 'Approval Delegation'
    _order = 'start_date desc, id desc'

    delegator_id = fields.Many2one(
        'res.users',
        string='Delegator',
        required=True,
        default=lambda self: self.env.user,
        help='The user who is delegating their approval authority'
    )
    delegate_id = fields.Many2one(
        'res.users',
        string='Delegate',
        required=True,
        help='The user who will approve on behalf of the delegator'
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        help='Date when delegation becomes active'
    )
    end_date = fields.Date(
        string='End Date',
        help='Date when delegation expires (leave empty for ongoing delegation)'
    )
    category_ids = fields.Many2many(
        'approval.category',
        'approval_delegation_category_rel',
        'delegation_id',
        'category_id',
        string='Categories',
        help='Limit delegation to specific approval categories (leave empty for all categories)'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to temporarily disable this delegation'
    )
    
    is_approval_manager = fields.Boolean(
        string='Is Approval Manager',
        compute='_compute_is_approval_manager',
        store=False,
        help='Technical field to check if current user is an approval manager'
    )
    
    @api.depends('create_uid')
    def _compute_is_approval_manager(self):
        """Compute if current user is an approval manager"""
        # Check if current user has the approval manager group
        # We depend on 'create_uid' to ensure it computes when the record is loaded
        # The actual value depends on the current user's groups (self.env.user), not on record data
        # This will compute for both new and existing records
        current_user = self.env.user
        is_manager = current_user.has_group('approvals.group_approval_manager')
        for rec in self:
            rec.is_approval_manager = is_manager

    @api.constrains('delegator_id', 'delegate_id')
    def _check_delegator_not_delegate(self):
        """Prevent users from delegating to themselves"""
        for rec in self:
            if rec.delegator_id == rec.delegate_id:
                raise ValidationError(_("You cannot delegate approval authority to yourself."))
    
    @api.constrains('delegator_id')
    def _check_delegator_permission(self):
        """Ensure regular users can only delegate for themselves"""
        for rec in self:
            # Only approval managers can set delegator to someone other than themselves
            if not self.env.user.has_group('approvals.group_approval_manager'):
                if rec.delegator_id != self.env.user:
                    raise ValidationError(_("You can only create delegations for yourself. Only Approval Managers can create delegations for other users."))

    @api.constrains('start_date', 'end_date')
    def _check_date_range(self):
        """Ensure end_date is after start_date"""
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End date must be after start date."))

    @api.model_create_multi
    def create(self, vals_list):
        """Override create - delegations work automatically through _can_approve() logic"""
        delegations = super().create(vals_list)
        return delegations

    def write(self, vals):
        """Override write - delegations work automatically through _can_approve() logic"""
        result = super().write(vals)
        return result

    def _update_pending_approvers(self):
        """
        Update pending approver records to apply or remove delegation
        - If delegation is active and within date range: Replace delegator with delegate
        - If delegation is inactive or outside date range: Restore delegator
        """
        approver_model = self.env['approval.approver'].sudo()

        for delegation in self:
            today = date.today()
            
            # Check if delegation should be active
            is_currently_active = (
                delegation.active and
                delegation.start_date <= today and
                (not delegation.end_date or delegation.end_date >= today)
            )

            def _filter_by_category(records):
                if delegation.category_ids:
                    return records.filtered(lambda a: a.request_id.category_id in delegation.category_ids)
                return records

            # Always restore any existing delegated approvers for this delegator
            restore_domain = [
                ('delegated_by_id', '=', delegation.delegator_id.id),
                ('status', 'in', ['pending', 'waiting']),
            ]
            delegated_records = approver_model.search(restore_domain)
            delegated_records = _filter_by_category(delegated_records)
            if delegated_records:
                delegated_records.write({
                    'user_id': delegation.delegator_id.id,
                    'delegated_by_id': False
                })

            if not is_currently_active:
                continue
            
            # APPLY DELEGATION: Find pending approvers assigned to delegator and replace with delegate
            domain = [
                ('user_id', '=', delegation.delegator_id.id),
                ('status', 'in', ['pending', 'waiting']),
            ]
            
            pending_approvers = approver_model.search(domain)
            pending_approvers = _filter_by_category(pending_approvers)
            
            if pending_approvers:
                pending_approvers.write({
                    'user_id': delegation.delegate_id.id,
                    'delegated_by_id': delegation.delegator_id.id
                })

    def unlink(self):
        """Override unlink - delegations automatically stop working when deleted"""
        return super().unlink()

    def action_update_pending_approvers(self):
        """
        Manual action to update pending approvers for this delegation.
        Applies delegation if active, removes delegation if inactive.
        """
        self._update_pending_approvers()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Pending approvers have been updated based on delegation status.'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def get_active_delegation(self, delegator_id, category_id=None, check_date=True):
        """
        Get active delegation for a delegator, optionally filtered by category
        
        :param delegator_id: ID of the user who delegated
        :param category_id: Optional category to filter by
        :param check_date: Whether to check if delegation is within date range
        :return: approval.delegation record or False
        """
        today = date.today()
        domain = [
            ('delegator_id', '=', delegator_id),
            ('active', '=', True)
        ]
        
        if check_date:
            domain.extend([
                ('start_date', '<=', today),
                '|',
                ('end_date', '=', False),
                ('end_date', '>=', today)
            ])
        
        delegations = self.sudo().search(domain)
        
        # If category is specified, filter by category (or no category restriction)
        if category_id:
            delegations = delegations.filtered(
                lambda d: not d.category_ids or category_id in d.category_ids
            )
        
        # Return the most recent active delegation
        return delegations[:1] if delegations else False

    def name_get(self):
        """Display name for delegation records"""
        result = []
        for rec in self:
            name = _("%s → %s") % (rec.delegator_id.name, rec.delegate_id.name)
            if rec.start_date or rec.end_date:
                date_range = ""
                if rec.start_date:
                    date_range = rec.start_date.strftime('%Y-%m-%d')
                if rec.end_date:
                    date_range += " to " + rec.end_date.strftime('%Y-%m-%d')
                else:
                    date_range += " (ongoing)"
                name += " [%s]" % date_range
            result.append((rec.id, name))
        return result

