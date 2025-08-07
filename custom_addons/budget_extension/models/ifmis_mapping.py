# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class IFMISMapping(models.Model):
    _name = 'ifmis.mapping'
    _description = 'IFMIS Budget Mapping'
    _order = 'ifmis_code, name'
    _rec_name = 'display_name'

    name = fields.Char(
        string='IFMIS Item Name',
        required=True,
        help="Name of the IFMIS budget item"
    )
    ifmis_code = fields.Char(
        string='IFMIS Code',
        required=True,
        help="Unique IFMIS code for budget item mapping"
    )
    ifmis_category = fields.Selection([
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
        ('capital', 'Capital Expenditure'),
        ('transfer', 'Transfer'),
        ('other', 'Other'),
    ], string='IFMIS Category',
       required=True,
       default='expense',
       help="Category of the IFMIS budget item"
    )
    description = fields.Text(
        string='Description',
        help="Detailed description of the IFMIS mapping"
    )
    active = fields.Boolean(
        default=True,
        help="Set to false to hide this mapping without deleting it"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Company this mapping belongs to"
    )
    budget_line_ids = fields.One2many(
        'budget.line',
        'ifmis_mapping_id',
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
    # Additional fields for IFMIS integration
    ifmis_parent_code = fields.Char(
        string='Parent IFMIS Code',
        help="Parent code in IFMIS hierarchy"
    )
    ifmis_level = fields.Integer(
        string='IFMIS Level',
        default=1,
        help="Level in IFMIS hierarchy"
    )
    external_system_id = fields.Char(
        string='External System ID',
        help="ID used in external IFMIS system"
    )
    sync_status = fields.Selection([
        ('not_synced', 'Not Synced'),
        ('synced', 'Synced'),
        ('error', 'Error'),
        ('pending', 'Pending Sync'),
    ], string='Sync Status',
       default='not_synced',
       help="Synchronization status with IFMIS system"
    )
    last_sync_date = fields.Datetime(
        string='Last Sync Date',
        readonly=True,
        help="Last synchronization date with IFMIS"
    )
    sync_error_message = fields.Text(
        string='Sync Error Message',
        readonly=True,
        help="Error message from last sync attempt"
    )

    _sql_constraints = [
        ('ifmis_code_company_uniq', 'unique(ifmis_code, company_id)',
         'The IFMIS code must be unique per company!'),
    ]

    @api.depends('ifmis_code', 'name')
    def _compute_display_name(self):
        """Compute display name as [ifmis_code] name"""
        for mapping in self:
            if mapping.ifmis_code and mapping.name:
                mapping.display_name = f"[{mapping.ifmis_code}] {mapping.name}"
            else:
                mapping.display_name = mapping.name or mapping.ifmis_code or ''

    @api.depends('budget_line_ids')
    def _compute_budget_line_count(self):
        """Compute the number of budget lines using this mapping"""
        for mapping in self:
            mapping.budget_line_count = len(mapping.budget_line_ids)

    @api.constrains('ifmis_code')
    def _check_ifmis_code_format(self):
        """Validate the IFMIS code format"""
        for mapping in self:
            if mapping.ifmis_code and not mapping.ifmis_code.replace('-', '').replace('_', '').replace('.', '').isalnum():
                raise ValidationError(_(
                    'IFMIS code can only contain letters, numbers, hyphens, underscores and dots.'
                ))

    @api.constrains('ifmis_level')
    def _check_ifmis_level(self):
        """Validate IFMIS level"""
        for mapping in self:
            if mapping.ifmis_level < 1 or mapping.ifmis_level > 10:
                raise ValidationError(_('IFMIS level must be between 1 and 10.'))

    def name_get(self):
        """Override name_get to show IFMIS code and name"""
        result = []
        for mapping in self:
            if mapping.ifmis_code:
                name = f"[{mapping.ifmis_code}] {mapping.name}"
            else:
                name = mapping.name
            result.append((mapping.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Search by IFMIS code or name"""
        if domain is None:
            domain = []
        
        if name:
            # Search by IFMIS code or name
            search_domain = [
                '|',
                ('ifmis_code', operator, name),
                ('name', operator, name)
            ]
            domain = domain + search_domain
        
        return self._search(domain, limit=limit, order=order)

    def action_view_budget_lines(self):
        """Action to view budget lines using this IFMIS mapping"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account_budget.budget_line_action")
        action['domain'] = [('ifmis_mapping_id', '=', self.id)]
        action['context'] = {
            'default_ifmis_mapping_id': self.id,
            'search_default_ifmis_mapping_id': self.id,
        }
        action['display_name'] = _('Budget Lines for %s') % self.display_name
        return action

    def action_sync_with_ifmis(self):
        """Action to sync with IFMIS system (placeholder for integration)"""
        self.ensure_one()
        # This is a placeholder for actual IFMIS integration
        # In a real implementation, this would call IFMIS API
        self.write({
            'sync_status': 'pending',
            'sync_error_message': False,
        })
        
        # Simulate sync process (replace with actual API call)
        try:
            # Placeholder for IFMIS API integration
            self.write({
                'sync_status': 'synced',
                'last_sync_date': fields.Datetime.now(),
                'sync_error_message': False,
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Successfully synced with IFMIS system.'),
                    'sticky': False,
                    'type': 'success'
                }
            }
        except Exception as e:
            self.write({
                'sync_status': 'error',
                'sync_error_message': str(e),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Failed to sync with IFMIS: %s') % str(e),
                    'sticky': True,
                    'type': 'danger'
                }
            } 