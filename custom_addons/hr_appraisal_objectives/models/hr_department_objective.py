from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrDepartmentObjective(models.Model):
    _name = "hr.department.objective"
    _description = "Department Objective"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    reference = fields.Char(
        string="Reference", readonly=True, copy=False, default="New"
    )
    name = fields.Char(required=True)
    institutional_objective_id = fields.Many2one(
        "hr.institutional.objective", ondelete="cascade"
    )
    department_id = fields.Many2one(
        "hr.department",
        required=True,
        default=lambda self: self._get_default_department(),
    )
    
    def _get_default_department(self):
        """Get default department based on user role"""
        # For line managers, get the department they manage
        # Check if user is a line manager (but NOT HR manager, as HR can select any dept)
        is_line_manager = self.env.user.has_group('hr_appraisal_objectives.group_appraisal_line_manager')
        is_hr_manager = self.env.user.has_group('hr_appraisal_objectives.group_hr_appraisal')
        
        if is_line_manager and not is_hr_manager:
            # Search for department where current user's employee is the manager
            current_employee = self.env.user.employee_id
            if current_employee:
                managed_dept = self.env['hr.department'].search([
                    ('manager_id', '=', current_employee.id)
                ], limit=1)
                if managed_dept:
                    _logger.info(f"Line manager {self.env.user.name} auto-assigned to department: {managed_dept.name}")
                    return managed_dept.id
        
        # For regular users or if no managed department found, get their employee department
        if self.env.user.employee_id and self.env.user.employee_id.department_id:
            return self.env.user.employee_id.department_id.id
        
        return False
    description = fields.Html()
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date(required=True)
    deadline_days = fields.Integer(
        string="Days to Deadline", compute="_compute_deadline_days", store=True
    )
    appraisal_goal_ids = fields.One2many(
        "hr.appraisal.goal", "department_objective_id", string="Individual Objectives"
    )
    draft_count = fields.Integer(
        compute="_compute_goal_counts", store=True, string="Draft Count"
    )
    submitted_count = fields.Integer(
        compute="_compute_goal_counts", store=True, string="Submitted Count"
    )
    first_approved_count = fields.Integer(
        compute="_compute_goal_counts", store=True, string="First Approved Count"
    )
    approved_count = fields.Integer(
        compute="_compute_goal_counts", store=True, string="Approved Count"
    )
    progress_count = fields.Integer(
        compute="_compute_goal_counts", store=True, string="Progress Count"
    )
    self_scored_count = fields.Integer(
        compute="_compute_goal_counts", store=True, string="Self Scored Count"
    )
    scored_count = fields.Integer(
        compute="_compute_goal_counts", store=True, string="Scored Count"
    )
    final_count = fields.Integer(
        compute="_compute_goal_counts", store=True, string="Final Count"
    )
    progress = fields.Float(
        string="Progress (%)",
        compute="_compute_progress",
        store=True,
        aggregator="avg",
    )
    individual_objective_count = fields.Integer(
        compute="_compute_individual_objective_count",
        string="Individual Count",
        store=True,
    )
    avg_score = fields.Float(
        string="Average Score",
        compute="_compute_avg_score",
        store=True,
        aggregator="avg",
    )

    # Fiscal year follows institutional objective
    fiscal_year_id = fields.Many2one(
        "hr.fiscal.year",
        string="Fiscal Year",
        compute="_compute_fiscal_year",
        store=True,
        readonly=False,
    )
    create_uid = fields.Many2one(
        "res.users", "Created by", readonly=True, default=lambda self: self.env.uid
    )
    current_uid_int = fields.Integer(
        string="Current User ID", compute="_compute_current_uid", store=False
    )
    current_user_department_id = fields.Many2one(
        "hr.department",
        string="Current User Department",
        compute="_compute_current_user_department",
        search="_search_current_user_department",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        string="Status",
        tracking=True,
    )

    def unlink(self):
        for record in self:
            linked_goals = self.env["hr.appraisal.goal"].search(
                [("department_objective_id", "=", record.id), ("state", "!=", "draft")]
            )
            if linked_goals:
                raise ValidationError(
                    _(
                        "Cannot delete Department Objective '%s' because it is linked to appraisal goals that are not in draft state."
                    )
                    % record.name
                )
        return super(HrDepartmentObjective, self).unlink()

    @api.constrains("department_id")
    def _check_department_manager(self):
        """Ensure line managers can only create objectives for their own department"""
        for record in self:
            # Skip check for HR managers
            if self.env.user.has_group('hr_appraisal_objectives.group_hr_appraisal'):
                continue
            
            # For line managers, check they manage this department
            if self.env.user.has_group('hr_appraisal_objectives.group_appraisal_line_manager'):
                if record.department_id:
                    current_employee = self.env.user.employee_id
                    if not current_employee:
                        raise ValidationError(
                            _("Your user account is not linked to an employee record. "
                              "Please contact your administrator.")
                        )
                    
                    # Check if the current employee is the manager of the selected department
                    is_manager = self.env['hr.department'].search_count([
                        ('id', '=', record.department_id.id),
                        ('manager_id', '=', current_employee.id)
                    ])
                    if not is_manager:
                        raise ValidationError(
                            _("You can only create department objectives for departments you manage. "
                              "You are not the manager of '%s' department.") % record.department_id.name
                        )

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date >= record.end_date:
                    raise ValidationError("Opening date must be before closing date.")
                elif record.start_date < fields.Date.today():
                    raise ValidationError("Opening date cannot be in the past.")

    @api.depends("start_date", "end_date")
    def _compute_fiscal_year(self):
        FiscalYear = self.env["hr.fiscal.year"].sudo()
        for rec in self:
            fy = False
            if rec.start_date:
                # Prefer a fiscal year covering the full window; fallback to one covering the start date
                fy = FiscalYear.search([
                    ("date_from", "<=", rec.start_date),
                    ("date_to", ">=", rec.end_date or rec.start_date),
                ], limit=1)
                if not fy:
                    fy = FiscalYear.search([
                        ("date_from", "<=", rec.start_date),
                        ("date_to", ">=", rec.start_date),
                    ], limit=1)
            rec.fiscal_year_id = fy.id if fy else False

    @api.onchange("fiscal_year_id")
    def _onchange_fiscal_year_id_set_end_date(self):
        for rec in self:
            if rec.fiscal_year_id:
                fy_end = rec.fiscal_year_id.date_to
                if fy_end and (not rec.end_date or rec.end_date > fy_end):
                    rec.end_date = fy_end

    @api.constrains("end_date", "fiscal_year_id")
    def _check_end_date_within_fiscal_year(self):
        for record in self:
            if record.fiscal_year_id and record.end_date:
                fy_end = record.fiscal_year_id.date_to
                if fy_end and record.end_date > fy_end:
                    raise ValidationError("End date cannot be after the fiscal year's end date.")

    @api.depends("end_date")
    def _compute_deadline_days(self):
        for record in self:
            if record.end_date:
                today = fields.Date.today()
                delta = record.end_date - today
                record.deadline_days = delta.days
            else:
                record.deadline_days = 0

    @api.depends("progress")
    def _compute_progress_display(self):
        for record in self:
            progress_value = min(max(record.progress or 0, 0), 100)
            color_class = (
                "bg-success"
                if progress_value >= 70
                else "bg-warning" if progress_value >= 40 else "bg-danger"
            )

            record.progress_bar_html = f"""
                <div class="progress" style="height: 25px;">
                    <div class="progress-bar {color_class}" 
                        role="progressbar" 
                        style="width: {progress_value}%;"
                        aria-valuenow="{progress_value}"
                        aria-valuemin="0" 
                        aria-valuemax="100">
                    </div>
                </div>
            """

    progress_bar_html = fields.Html(compute="_compute_progress_display", store=False)

    @api.model
    def create(self, vals):
        if vals.get("reference", "New") == "New":
            vals["reference"] = (
                self.env["ir.sequence"].next_by_code("hr.department.objective") or "/"
            )
        return super().create(vals)

    @api.depends("appraisal_goal_ids")
    def _compute_individual_objective_count(self):
        for rec in self:
            rec.individual_objective_count = len(rec.appraisal_goal_ids)

    @api.depends("appraisal_goal_ids.progression")
    def _compute_progress(self):
        for record in self:
            goals = record.appraisal_goal_ids
            vals = [
                float(g.progression or 0) for g in goals if g.progression is not None
            ]
            if vals:
                record.progress = sum(vals) / len(vals)
            else:
                record.progress = 0

    def _recompute_progress_safe(self):
        """Safely recompute progress without causing access errors"""
        try:
            # Use sudo to bypass access rights for computation
            self.sudo()._compute_progress()
        except Exception as e:
            # Log the error but don't fail the operation
            _logger.warning(f"Could not recompute department progress: {e}")
            pass

    def _schedule_progress_recomputation(self):
        """Schedule progress recomputation for later to avoid blocking user operations"""
        try:
            # Use a simple approach: just trigger the computation in a separate transaction
            self.env.cr.commit()  # Commit current transaction
            self.sudo()._compute_progress()
        except Exception as e:
            _logger.warning(f"Could not schedule progress recomputation: {e}")
            pass

    @api.depends("appraisal_goal_ids.state")
    def _compute_goal_counts(self):
        for rec in self:
            goals = rec.appraisal_goal_ids
            rec.draft_count = len(goals.filtered(lambda g: g.state == "draft"))
            rec.submitted_count = len(goals.filtered(lambda g: g.state == "submitted"))
            rec.first_approved_count = len(
                goals.filtered(lambda g: g.state == "first_approved")
            )
            rec.approved_count = len(goals.filtered(lambda g: g.state == "progress"))
            rec.progress_count = len(goals.filtered(lambda g: g.state == "progress"))
            rec.self_scored_count = len(
                goals.filtered(lambda g: g.state == "self_scored")
            )
            rec.scored_count = len(goals.filtered(lambda g: g.state == "scored"))
            rec.final_count = len(goals.filtered(lambda g: g.state == "final"))

    @api.depends("appraisal_goal_ids.final_score")
    def _compute_avg_score(self):
        for record in self:
            goals = record.appraisal_goal_ids
            scores = [g.final_score for g in goals if g.final_score > 0]
            if scores:
                record.avg_score = sum(scores) / len(scores)
            else:
                record.avg_score = 0

    def _compute_current_uid(self):
        for rec in self:
            rec.current_uid_int = self.env.uid

    def _compute_current_user_department(self):
        for record in self:
            if self.env.user.employee_id and self.env.user.employee_id.department_id:
                record.current_user_department_id = (
                    self.env.user.employee_id.department_id
                )
            else:
                record.current_user_department_id = False

    def _search_current_user_department(self, operator, value):
        if self.env.user.employee_id and self.env.user.employee_id.department_id:
            user_dept_id = self.env.user.employee_id.department_id.id
            return [("department_id", operator, user_dept_id)]
        return [("id", "=", 0)]  # Return no records if user has no department

    def action_start(self):
        """Start the department objective"""
        self.write({"state": "active"})

    def action_complete(self):
        """Mark as completed"""
        self.write({"state": "completed"})

    def action_cancel(self):
        """Cancel the objective"""
        self.write({"state": "cancelled"})

    def action_view_draft_objectives(self):
        """View draft individual objectives for this department"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Draft Objectives - {self.name}",
            "res_model": "hr.appraisal.goal",
            "view_mode": "kanban,list,form",
            "domain": [
                ("department_objective_id", "=", self.id),
                ("state", "=", "draft"),
            ],
            "context": {
                "default_department_objective_id": self.id,
                "default_state": "draft",
            },
        }

    def action_view_submitted_objectives(self):
        """View submitted individual objectives for this department"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Submitted Objectives - {self.name}",
            "res_model": "hr.appraisal.goal",
            "view_mode": "kanban,list,form",
            "domain": [
                ("department_objective_id", "=", self.id),
                ("state", "=", "submitted"),
            ],
            "context": {
                "default_department_objective_id": self.id,
            },
        }

    def action_view_approved_objectives(self):
        """View approved individual objectives for this department"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Approved Objectives - {self.name}",
            "res_model": "hr.appraisal.goal",
            "view_mode": "kanban,list,form",
            "domain": [
                ("department_objective_id", "=", self.id),
                ("state", "=", "progress"),
            ],
            "context": {
                "default_department_objective_id": self.id,
            },
        }

    def action_view_scored_objectives(self):
        """View scored individual objectives for this department"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Scored Objectives - {self.name}",
            "res_model": "hr.appraisal.goal",
            "view_mode": "kanban,list,form",
            "domain": [
                ("department_objective_id", "=", self.id),
                ("state", "=", "scored"),
            ],
            "context": {
                "default_department_objective_id": self.id,
            },
        }

    def action_view_final_objectives(self):
        """View final individual objectives for this department"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Final Objectives - {self.name}",
            "res_model": "hr.appraisal.goal",
            "view_mode": "kanban,list,form",
            "domain": [
                ("department_objective_id", "=", self.id),
                ("state", "=", "final"),
            ],
            "context": {
                "default_department_objective_id": self.id,
                "default_state": "final",
            },
        }
