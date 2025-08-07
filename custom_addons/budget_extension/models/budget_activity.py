# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BudgetActivity(models.Model):
    _name = 'budget.activity'
    _description = 'Budgetary Activity'
    _order = 'code, name'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Activity Name',
        required=True,
        help="Name of the budgetary activity"
    )
    code = fields.Char(
        string='Activity Code',
        required=True,
        help="Unique code for the budgetary activity"
    )
    description = fields.Text(
        string='Description',
        help="Detailed description of the budgetary activity"
    )
    parent_id = fields.Many2one(
        'budget.activity',
        string='Parent Activity',
        help="Parent budgetary activity for hierarchical structure"
    )
    child_ids = fields.One2many(
        'budget.activity',
        'parent_id',
        string='Sub-Activities'
    )
    active = fields.Boolean(
        default=True,
        help="Set to false to hide this activity without deleting it"
    )
    color = fields.Integer(
        string='Color',
        help="Color for display purposes"
    )
    sequence = fields.Integer(
        default=10,
        help="Used to order activities"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Company this activity belongs to"
    )
    budget_line_ids = fields.One2many(
        'budget.line',
        'budget_activity_id',
        string='Budget Lines',
        readonly=True
    )
    budget_line_count = fields.Integer(
        compute='_compute_budget_line_count',
        string='Budget Lines Count'
    )
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'The activity code must be unique per company!'),
    ]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        """Compute display name as [code] name"""
        for activity in self:
            if activity.code and activity.name:
                activity.display_name = f"[{activity.code}] {activity.name}"
            else:
                activity.display_name = activity.name or activity.code or ''

    @api.depends('budget_line_ids')
    def _compute_budget_line_count(self):
        """Compute the number of budget lines using this activity"""
        for activity in self:
            activity.budget_line_count = len(activity.budget_line_ids)

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        """Check that parent_id is not creating a recursion"""
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive budgetary activities.'))

    @api.constrains('code')
    def _check_code_format(self):
        """Validate the code format"""
        for activity in self:
            if activity.code and not activity.code.replace('-', '').replace('_', '').isalnum():
                raise ValidationError(_(
                    'Activity code can only contain letters, numbers, hyphens and underscores.'
                ))

    def name_get(self):
        """Override name_get to show code and name"""
        result = []
        for activity in self:
            if activity.code:
                name = f"[{activity.code}] {activity.name}"
            else:
                name = activity.name
            result.append((activity.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Search by code or name"""
        if domain is None:
            domain = []
        
        if name:
            # Search by code or name
            search_domain = [
                '|',
                ('code', operator, name),
                ('name', operator, name)
            ]
            domain = domain + search_domain
        
        return self._search(domain, limit=limit, order=order)

    def action_view_budget_lines(self):
        """Action to view budget lines using this activity"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account_budget.budget_line_action")
        action['domain'] = [('budget_activity_id', '=', self.id)]
        action['context'] = {
            'default_budget_activity_id': self.id,
            'search_default_budget_activity_id': self.id,
        }
        action['display_name'] = _('Budget Lines for %s') % self.display_name
        return action 