from odoo import models, fields, api
from odoo.exceptions import AccessError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    kpi_task_ids = fields.Many2many(
        "project.task",
        string="KPI Tasks",
        compute="_compute_kpi_task_ids",
        store=False,
    )
    
    # Objective status tracking
    objective_status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('awaiting_manager', 'Awaiting Manager'),
        ('awaiting_hr', 'Awaiting HR'),
        ('approved', 'Approved'),
    ], string="Objective Status", compute="_compute_objective_status", search='_search_objective_status')

    objective_status_order = fields.Integer(
        string="Objective Status Order",
        store=True,
        compute="_compute_objective_status_order"
    )

    @api.depends('objective_status')
    def _compute_objective_status_order(self):
        """Map textual status to a numeric rank for ordering."""
        order_map = {
            'not_started': 3,
            'in_progress': 4,
            'awaiting_manager': 1,
            'awaiting_hr': 2,
            'approved': 5,
        }
        for rec in self:
            rec.objective_status_order = order_map.get(rec.objective_status, 0)
    
    objective_status_color = fields.Char(
        string="Status Color",
        compute="_compute_objective_status",
        store=False
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
    
    def _compute_objective_status(self):
        """
        Compute overall objective status for employee:
        - not_started: No objectives (red - #dc3545 muted)
        - in_progress: Has draft objectives (orange - #fd7e14 muted)
        - awaiting_manager: Has submitted objectives (blue - #0d6efd muted)
        - awaiting_hr: Has first_approved objectives (purple - #6f42c1 muted)
        - approved: All objectives are in progress/done (green - #198754 muted)
        """
        Goal = self.env['hr.appraisal.goal']
        for emp in self:
            goals = Goal.search([('employee_id', '=', emp.id)])
            
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
        return {
            'name': f"{self.name}'s Objectives",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.appraisal.goal',
            'view_mode': 'kanban,list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
                'employee_objective_view': True,
            },
            'target': 'current',
        }
    
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

class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    objective_status = fields.Selection(
        selection=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('awaiting_manager', 'Awaiting Manager'),
            ('awaiting_hr', 'Awaiting HR'),
            ('approved', 'Approved'),
        ],
        compute='_compute_objective_status_public',
        string="Objective Status",
    )

    objective_status_order = fields.Integer(
        string="Objective Status Order",
        store=True,
        compute="_compute_objective_status_order"
    )

    @api.depends('objective_status')
    def _compute_objective_status_order(self):
        """Map textual status to a numeric rank for ordering."""
        order_map = {
            'not_started': 3,
            'in_progress': 4,
            'awaiting_manager': 1,
            'awaiting_hr': 2,
            'approved': 5,
        }
        for rec in self:
            rec.objective_status_order = order_map.get(rec.objective_status, 0)

    def _compute_objective_status_public(self):
        for rec in self:
            employee = self.env['hr.employee'].sudo().search([('id', '=', rec.id)], limit=1)
            rec.objective_status = employee.objective_status
