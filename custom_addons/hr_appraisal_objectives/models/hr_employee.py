from odoo import models, fields, api
from odoo.exceptions import AccessError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    appraisal_goal_ids = fields.One2many(
        comodel_name='hr.appraisal.goal',
        inverse_name='employee_id',
        string='Goals'
    )

    kpi_task_ids = fields.Many2many(
        "project.task",
        string="KPI Tasks",
        compute="_compute_kpi_task_ids",
        store=False,
    )
    
    # Objective status tracking
    objective_status = fields.Selection([
        ('awaiting_hr', 'Awaiting HR'),
        ('awaiting_manager', 'Awaiting Manager'),
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
    ], string="Objective Status", compute="_compute_objective_status", store=True, compute_sudo=True, search='_search_objective_status')
    
    objective_status_color = fields.Char(
        string="Status Color",
        compute="_compute_objective_status",
        store=True,
        compute_sudo=True,
    )
    
    objective_draft_count = fields.Integer(
        string="Draft Objectives",
        compute="_compute_objective_counts",
        store=False
    )
    objective_submitted_count = fields.Integer(
        string="Submitted Objectives",
        compute="_compute_objective_counts",
        store=False
    )
    objective_first_approved_count = fields.Integer(
        string="First Approved Objectives",
        compute="_compute_objective_counts",
        store=False
    )
    objective_progress_count = fields.Integer(
        string="Active Objectives",
        compute="_compute_objective_counts",
        store=False
    )
    objective_total_count = fields.Integer(
        string="Total Objectives",
        compute="_compute_objective_counts",
        store=False
    )

    def _compute_kpi_task_ids(self):
        for emp in self:
            kpis = self.env["hr.appraisal.goal.kpi"].search([
                ("appraisal_goal_id.employee_id", "=", emp.id)
            ])
            emp.kpi_task_ids = kpis.mapped("task_ids")
    
    def _compute_objective_counts(self):
        """Compute objective counts by state"""
        Goal = self.env['hr.appraisal.goal']
        for emp in self:
            goals = Goal.search([('employee_id', '=', emp.id)])
            emp.objective_total_count = len(goals)
            emp.objective_draft_count = len(goals.filtered(lambda g: g.state == 'draft'))
            emp.objective_submitted_count = len(goals.filtered(lambda g: g.state == 'submitted'))
            emp.objective_first_approved_count = len(goals.filtered(lambda g: g.state == 'first_approved'))
            emp.objective_progress_count = len(goals.filtered(lambda g: g.state in ['progress', 'progress_done']))
    
    @api.depends('appraisal_goal_ids.state')
    def _compute_objective_status(self):
        """
        Compute overall objective status for employee:
        - not_started: No objectives (red - #dc3545 muted)
        - in_progress: Has draft objectives (orange - #fd7e14 muted)
        - awaiting_manager: Has submitted objectives (blue - #0d6efd muted)
        - awaiting_hr: Has first_approved objectives (purple - #6f42c1 muted)
        - approved: All objectives are in progress/done (green - #198754 muted)
        """
        for emp in self:
            goals = emp.appraisal_goal_ids
            
            if not goals:
                emp.objective_status = 'not_started'
                emp.objective_status_color = '#dc3545'  # Danger red (muted)
            elif any(g.state == 'first_approved' for g in goals):
                emp.objective_status = 'awaiting_hr'
                emp.objective_status_color = '#6f42c1'  # Purple (muted)
            elif any(g.state == 'submitted' for g in goals):
                emp.objective_status = 'awaiting_manager'
                emp.objective_status_color = '#0d6efd'  # Primary blue (muted)
            elif any(g.state == 'draft' for g in goals):
                emp.objective_status = 'in_progress'
                emp.objective_status_color = '#fd7e14'  # Orange (muted)
            elif all(g.state in ['progress', 'progress_done'] for g in goals):
                emp.objective_status = 'approved'
                emp.objective_status_color = '#198754'  # Success green (muted)
            else:
                # Mixed states - default to in progress
                emp.objective_status = 'in_progress'
                emp.objective_status_color = '#fd7e14'
    
    def _search_objective_status(self, operator, value):
        """Search method for objective_status computed field"""
        Goal = self.env['hr.appraisal.goal']
        
        if operator not in ['=', '!=', 'in', 'not in']:
            return []
        
        # Get all employees with their objective statuses
        all_employees = self.search([])
        matching_employees = self.browse()
        
        for emp in all_employees:
            goals = Goal.search([('employee_id', '=', emp.id)])
            
            # Determine status
            if not goals:
                status = 'not_started'
            elif any(g.state == 'first_approved' for g in goals):
                status = 'awaiting_hr'
            elif any(g.state == 'submitted' for g in goals):
                status = 'awaiting_manager'
            elif any(g.state == 'draft' for g in goals):
                status = 'in_progress'
            elif all(g.state in ['progress', 'progress_done'] for g in goals):
                status = 'approved'
            else:
                status = 'in_progress'
            
            # Check if matches search criteria
            if operator == '=' and status == value:
                matching_employees |= emp
            elif operator == '!=' and status != value:
                matching_employees |= emp
            elif operator == 'in' and status in value:
                matching_employees |= emp
            elif operator == 'not in' and status not in value:
                matching_employees |= emp
        
        return [('id', 'in', matching_employees.ids)]
    
    def action_view_employee_objectives(self):
        """Open employee's objectives for review and batch approval"""
        self.ensure_one()
        # Get the base action (or create a new one)
        action = {
            'name': f"{self.name}'s Objectives",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.appraisal.goal',
            'view_mode': 'kanban,list,form',
            # No domain - use visible filter instead
            'domain': [],
            'context': {
                'default_employee_id': self.id,
                'employee_objective_view': True,
                # Set employee_id in context for the filter to use
                'filter_employee_id': self.id,
                # Auto-apply both employee and fiscal year filters
                'search_default_filter_employee': 1,
                'search_default_filter_current_fy': 1,
            },
            'target': 'current',
        }
        return action
    
    def action_create_appraisal_for_employee(self):
        """Create a new appraisal for this employee (HR only)"""
        self.ensure_one()
        
        # Verify user is HR manager
        # if not self.env.user.has_group('hr_appraisal_objectives.group_hr_appraisal'):
        #     raise AccessError("Only HR managers can create appraisals.")
        
        # Get managers for this employee
        manager_ids = []
        if self.parent_id:
            manager_ids.append((4, self.parent_id.id))
        elif self.department_id and self.department_id.manager_id:
            manager_ids.append((4, self.department_id.manager_id.id))
        
        # Create and return form view for new appraisal
        return {
            'name': f'New Appraisal - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.appraisal',
            'view_mode': 'form',
            'context': {
                'default_employee_id': self.id,
                'default_manager_ids': manager_ids,
                'default_department_id': self.department_id.id if self.department_id else False,
            },
            'target': 'current',
        }
    
    def action_view_employee_appraisals(self):
        """Open appraisals for this employee with employee filter visible and applied"""
        self.ensure_one()
        action = self.env.ref('hr_appraisal.open_view_hr_appraisal_tree').sudo().read()[0]
        # No domain - use visible filter instead
        action['domain'] = []
        # Set context to show employee filter
        ctx = action.get('context', {})
        if isinstance(ctx, str):
            try:
                ctx = eval(ctx)
            except:
                ctx = {}
        if not isinstance(ctx, dict):
            ctx = {}
        ctx['default_employee_id'] = self.id
        # Set employee_id in context for the filter to use
        ctx['filter_employee_id'] = self.id
        # Auto-apply both employee and fiscal year filters
        ctx['search_default_filter_employee'] = 1
        ctx['search_default_filter_current_fy'] = 1
        action['context'] = ctx
        return action

class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    objective_status = fields.Selection(
        selection=[
            ('awaiting_hr', 'Awaiting HR'),
            ('awaiting_manager', 'Awaiting Manager'),
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('approved', 'Approved'),
        ],
        compute='_compute_objective_status_public',
        store=True,
        compute_sudo=True,
        string="Objective Status",
    )

    def _compute_objective_status_public(self):
        for rec in self:
            employee = self.env['hr.employee'].sudo().search([('id', '=', rec.id)], limit=1)
            rec.objective_status = employee.objective_status
