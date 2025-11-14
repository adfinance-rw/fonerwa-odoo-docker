from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrAppraisal(models.Model):

    _inherit = "hr.appraisal"
    
    _sql_constraints = [
        ('unique_employee_fiscal_year', 
         'UNIQUE(employee_id, fiscal_year_id)', 
         'An appraisal already exists for this employee in the selected fiscal year. Please use the existing appraisal or choose a different fiscal year.')
    ]

    objectives_progress = fields.Float(
        "Objectives Progress",
        compute="_compute_objectives_progress",
        aggregator="avg",
    )
    objectives_count = fields.Integer(
        "Objectives Count",
        compute="_compute_objectives_count",
    )
    institutional_objective_id = fields.Many2one(
        "hr.institutional.objective",
        string="Institutional Objective",
        domain="[('state', '=', 'completed')]",
        # required=True,
    )
    fiscal_year_id = fields.Many2one(
        "hr.fiscal.year",
        string="Fiscal Year",
        default=lambda self: self.env['hr.fiscal.year'].get_current_fiscal_year(),
        required=True,
        help="Fiscal year for this appraisal"
    )
    is_current_fy = fields.Boolean(
        string="Is Current Fiscal Year",
        compute="_compute_is_current_fy",
        store=True,
        help="Indicates whether this appraisal belongs to the current fiscal year"
    )
    employee_goal_ids = fields.One2many(
        "hr.appraisal.goal",
        "appraisal_id",
        string="Employee Goals",
        readonly=True,
        store=True,
    )

    # Dashboard analytics fields
    department_performance_trend = fields.Float(
        "Department Performance Trend", compute="_compute_performance_trends"
    )
    employee_performance_rank = fields.Integer(
        "Employee Performance Rank", compute="_compute_performance_rank"
    )
    completion_rate = fields.Float(
        "Completion Rate (%)", compute="_compute_completion_rate"
    )
    avg_progress = fields.Float("Average Progress (%)", compute="_compute_avg_progress")

    # --- Comments per person (scoring is done per individual objective) ---
    self_overall_notes = fields.Text(string="Employee Overall Comment", help="Employee's overall comments for all objectives")
    self_overall_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_appraisal_self_attachment_rel",
        "appraisal_id",
        "attachment_id",
        string="Employee Overall Documents",
    )

    manager_overall_notes = fields.Text(string="Manager Overall Comment", help="Manager's overall comments for all objectives")
    manager_overall_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_appraisal_manager_attachment_rel",
        "appraisal_id",
        "attachment_id",
        string="Manager Overall Documents",
    )

    hr_overall_notes = fields.Text(string="HR Overall Comment", help="HR's overall comments for all objectives")
    hr_overall_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_appraisal_hr_attachment_rel",
        "appraisal_id",
        "attachment_id",
        string="HR Overall Documents",
    )

    final_overall_score = fields.Float(
        string="Final Overall Score", 
        compute="_compute_final_overall_score", 
        store=True,
        help="40% Employee + 60% (Average of HR & Manager)"
    )
    # Bootstrap color class to render the rating nicely in views
    final_rating_style = fields.Char(
        string="Final Rating Style",
        compute="_compute_final_rating_style",
        store=True
    )
    rating_scale_id = fields.Many2one(
        'hr.appraisal.rating.scale',
        string="Performance Rating",
        compute="_compute_rating_scale",
        store=True
    )
    rating_color = fields.Char(
        string="Rating Color",
        related="rating_scale_id.color",
        store=True
    )

    employee_goal_total_weight = fields.Integer(string="Total Weight", compute="_compute_employee_goal_total_weight")
    current_uid_int = fields.Integer(
        string="Current User ID", compute="_compute_current_uid", store=False
    )
    
    # Enhanced state field with additional states for scoring workflow
    state = fields.Selection(selection_add=[
        ('self_scored', 'Self Assessment Done'),
        ('manager_scored', 'Manager Assessment Done'),
        ('hr_scored', 'HR Assessment Done'),
    ], ondelete={'self_scored': 'cascade', 'manager_scored': 'cascade', 'hr_scored': 'cascade'})
    
    # Helper fields for access control
    employee_user_id = fields.Many2one(related='employee_id.user_id', store=True, readonly=True)
    is_manager = fields.Boolean(compute="_compute_is_manager", store=False)
    is_hr_user = fields.Boolean(compute="_compute_is_hr_user", store=False)
    
    # HR editing fields
    hr_change_reason = fields.Text(string="Reason for Change", help="Reason provided by HR for reverting to draft")
    hr_change_date = fields.Datetime(string="Last HR Change Date", readonly=True)

    rating_color_class = fields.Char(compute='_compute_rating_color_class', store=False)

    @api.depends('rating_color')
    def _compute_rating_color_class(self):
        for record in self:
            if record.rating_color:
                record.rating_color_class = f"color-style-{record.rating_color}"
            else:
                record.rating_color_class = "color-style-default"

    @api.depends("create_uid")
    def _compute_current_uid(self):
        for rec in self:
            rec.current_uid_int = self.env.uid
    
    @api.depends("manager_ids")
    def _compute_is_manager(self):
        for rec in self:
            # Check if current user is one of the managers
            manager_user_ids = rec.manager_ids.mapped('user_id.id')
            rec.is_manager = self.env.uid in manager_user_ids
    
    def _compute_is_hr_user(self):
        for rec in self:
            rec.is_hr_user = self.env.user.has_group('hr_appraisal_objectives.group_hr_appraisal')
    
    @api.depends('fiscal_year_id')
    def _compute_is_current_fy(self):
        """Flag appraisals that belong to the current fiscal year.
        Uses hr.fiscal.year.get_current_fiscal_year() instead of any boolean field.
        """
        current_fy = self.env['hr.fiscal.year'].get_current_fiscal_year()
        current_id = current_fy.id if current_fy else False
        for rec in self:
            rec.is_current_fy = bool(rec.fiscal_year_id and rec.fiscal_year_id.id == current_id)
    
    # Workflow methods
    def action_start_appraisal(self):
        """Start the appraisal process"""
        for rec in self:
            rec.state = 'pending'
        return True
    
    def action_submit_self_assessment(self):
        """Submit self assessment"""
        for rec in self:
            # Check if at least one individual objective has been scored by employee
            employee_not_scored_goals = rec.employee_goal_ids.filtered(lambda g: g.self_score == 0)
            if employee_not_scored_goals:
                raise ValidationError("Please score the individual objectives before submitting self feedback.")
            
            # Check if employee feedback is completed (using standard Odoo appraisal feedback)
            if not rec.employee_feedback_published:
                raise ValidationError("Please complete and publish your Employee Feedback in the Appraisal tab before submitting your self assessment.")
            
            # Check if employee feedback has content (not just template)
            if not rec.accessible_employee_feedback or rec.accessible_employee_feedback.strip() == '':
                raise ValidationError("Please fill out the Employee Feedback template in the Appraisal tab before submitting your self assessment.")
            
            rec.state = 'self_scored'
            
            # Create activity for line manager(s) to review
            for manager in rec.manager_ids:
                if manager.user_id:
                    rec._create_appraisal_activity(
                        user_id=manager.user_id.id,
                        summary=f"Manager Assessment Required: {rec.employee_id.name}",
                        note=f"""<p><strong>Employee:</strong> {rec.employee_id.name}</p>
                              <p><strong>Department:</strong> {rec.department_id.name if rec.department_id else 'N/A'}</p>
                              <p><strong>Fiscal Year:</strong> {rec.fiscal_year_id.name if rec.fiscal_year_id else 'N/A'}</p>
                              <p><strong>Status:</strong> Employee has completed self-assessment</p>
                              <p><strong>Action Required:</strong> Please complete Manager Assessment</p>
                              <p>The employee has submitted their self-assessment. Please review and provide your manager feedback.</p>"""
                    )
        return True
    
    def action_submit_manager_assessment(self):
        """Submit manager assessment"""
        for rec in self:
            # Check if at least one individual objective has been scored by manager
            manager_not_scored_goals = rec.employee_goal_ids.filtered(lambda g: g.manager_score == 0 and g.is_common == False)
            if manager_not_scored_goals:
                raise ValidationError("Please score the individual objectives before submitting manager feedback.")
            
            # Check if manager feedback is completed (using standard Odoo appraisal feedback)
            if not rec.manager_feedback_published:
                raise ValidationError("Please complete and publish your Manager Feedback in the Appraisal tab before submitting the manager assessment.")
            
            # Check if manager feedback has content (not just template)
            if not rec.accessible_manager_feedback or rec.accessible_manager_feedback.strip() == '':
                raise ValidationError("Please fill out the Manager Feedback template in the Appraisal tab before submitting the manager assessment.")
            
            rec.state = 'manager_scored'
            
            # Create activity for HR managers to review
            hr_group = self.env.ref('hr_appraisal_objectives.group_hr_appraisal', raise_if_not_found=False)
            if hr_group:
                for hr_user in hr_group.users:
                    rec._create_appraisal_activity(
                        user_id=hr_user.id,
                        summary=f"HR Assessment Required: {rec.employee_id.name}",
                        note=f"""<p><strong>Employee:</strong> {rec.employee_id.name}</p>
                              <p><strong>Department:</strong> {rec.department_id.name if rec.department_id else 'N/A'}</p>
                              <p><strong>Fiscal Year:</strong> {rec.fiscal_year_id.name if rec.fiscal_year_id else 'N/A'}</p>
                              <p><strong>Status:</strong> Manager assessment completed</p>
                              <p><strong>Action Required:</strong> Please complete HR/Supervisor Assessment</p>
                              <p>The manager has completed their assessment. Please review and provide final HR feedback.</p>"""
                    )
        return True
    
    def action_complete_appraisal(self):
        """Complete the appraisal"""
        for rec in self:
            # Check if at least one individual objective has been scored by HR
            hr_not_scored_goals = rec.employee_goal_ids.filtered(lambda g: g.supervisor_score == 0)
            if hr_not_scored_goals:
                raise ValidationError("Please score the individual objectives before completing the appraisal.")
            rec.state = 'done'
        return True
    
    def action_cancel_appraisal(self):
        """Cancel the appraisal"""
        for rec in self:
            rec.state = 'cancel'
        return True
    
    def action_reset_to_pending(self):
        """Reset to pending state"""
        for rec in self:
            rec.state = 'pending'
        return True
    
    def action_hr_revert_to_draft(self):
        """HR can revert appraisal to draft at any stage"""
        self.ensure_one()
        if not self.env.user.has_group('hr_appraisal_objectives.group_hr_appraisal'):
            raise ValidationError("Only HR users can revert appraisals to draft.")
        
        return {
            "type": "ir.actions.act_window",
            "name": "Revert Appraisal to Draft",
            "res_model": "hr.appraisal.revert.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_appraisal_id": self.id,
            },
        }


    @api.model
    def create(self, vals_list):
        """Override create to add activity notification when appraisal is created"""
        # Call parent's create which handles the base functionality
        appraisals = super().create(vals_list)
        
        # Create activity for employee to start self-assessment
        for appraisal in appraisals:
            if appraisal.employee_id and appraisal.employee_id.user_id:
                appraisal._create_appraisal_activity(
                    user_id=appraisal.employee_id.user_id.id,
                    summary=f"New Appraisal: Complete Self-Assessment",
                    note=f"""<p><strong>Appraisal Created</strong></p>
                          <p><strong>Fiscal Year:</strong> {appraisal.fiscal_year_id.name if appraisal.fiscal_year_id else 'N/A'}</p>
                          <p><strong>Department:</strong> {appraisal.department_id.name if appraisal.department_id else 'N/A'}</p>
                          <p><strong>Action Required:</strong> Complete Self-Assessment</p>
                          <p>A new appraisal has been created for you. Please complete your self-assessment and submit your feedback.</p>"""
                )
        
        return appraisals
    
    def _create_appraisal_activity(self, user_id, summary, note):
        """Helper method to create activities for appraisals"""
        self.ensure_one()
        try:
            # Get or create activity type for approvals
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if not activity_type:
                activity_type = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)
            
            if activity_type:
                self.activity_schedule(
                    activity_type_xml_id='mail.mail_activity_data_todo',
                    date_deadline=fields.Date.today(),
                    user_id=user_id,
                    summary=summary,
                    note=note,
                )
                _logger.info(f"Created appraisal activity for user {user_id}: {summary}")
        except Exception as e:
            _logger.warning(f"Failed to create appraisal activity: {str(e)}")
            # Never block workflow on activity creation failure
            pass

    @api.constrains("institutional_objective_id")
    def _check_institutional_objective_completed(self):
        for record in self:
            if (
                record.institutional_objective_id
                and record.institutional_objective_id.state not in ['completed', 'active']
            ):
                raise ValidationError(
                    "You can only select an Institutional Objective in 'Completed' or 'Active' state."
                )
    
    @api.constrains("employee_id", "fiscal_year_id")
    def _check_unique_employee_fiscal_year(self):
        """Ensure only one appraisal per employee per fiscal year"""
        for record in self:
            if record.employee_id and record.fiscal_year_id:
                duplicate = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('fiscal_year_id', '=', record.fiscal_year_id.id),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicate:
                    # Get state label
                    state_label = dict(self._fields['state'].selection).get(duplicate.state, duplicate.state)
                    
                    raise ValidationError(
                        f"An appraisal already exists for {record.employee_id.name} "
                        f"in fiscal year {record.fiscal_year_id.name}.\n\n"
                        f"Existing appraisal ID: #{duplicate.id} (State: {state_label})\n\n"
                        f"Please use the existing appraisal or choose a different fiscal year."
                    )

    @api.depends("employee_goal_ids.kpi_total_weight")
    def _compute_employee_goal_total_weight(self):
        for record in self:
            record.employee_goal_total_weight = sum(goal.kpi_total_weight for goal in record.employee_goal_ids)
    
    @api.depends("employee_goal_ids.final_score", "employee_goal_ids.kpi_total_weight")
    def _compute_final_overall_score(self):
        """Compute final overall score as weighted average of goal.final_score.

        Each goal.final_score is already 40% self + 60% avg(HR & Manager).
        Here we simply aggregate using the KPI weight per goal.
        """
        for record in self:
            goals = record.employee_goal_ids.filtered(lambda g: g.final_score > 0)
            if goals:
                total_weighted_score = sum(
                    (goal.final_score or 0.0) * (getattr(goal, 'kpi_total_weight', 0.0) or 0.0)
                    for goal in goals
                )
                total_weight = sum((getattr(goal, 'kpi_total_weight', 0.0) or 0.0) for goal in goals)
                record.final_overall_score = (total_weighted_score / total_weight) if total_weight > 0 else 0.0
            else:
                record.final_overall_score = 0.0

            # Auto-suggest assessment_note if not manually set
            # Keep it editable: only set when empty to avoid overriding manual changes
            if record.final_overall_score:
                if record.final_overall_score >= 86:
                    note = self._find_or_create_assessment_note("Exceptional Performer")
                elif record.final_overall_score >= 76:
                    note = self._find_or_create_assessment_note("Out Performer")
                elif record.final_overall_score >= 66:
                    note = self._find_or_create_assessment_note("Solid Performer")
                elif record.final_overall_score >= 51:
                    note = self._find_or_create_assessment_note("Developing Performer")
                else:
                    note = self._find_or_create_assessment_note("Under Performer")
                record.assessment_note = note.id if note else False
    
    @api.depends("final_overall_score")
    def _compute_rating_scale(self):
        """Compute the rating scale based on final score"""
        for record in self:
            if record.final_overall_score > 0:
                rating = self.env['hr.appraisal.rating.scale'].get_rating_for_score(record.final_overall_score)
                record.rating_scale_id = rating.id if rating else False
            else:
                record.rating_scale_id = False

    @api.depends("final_overall_score")
    def _compute_final_rating_style(self):
        """Map final_overall_score into a Bootstrap color class.

        Bands:
        - 86-100: success
        - 76-85: info
        - 66-75: pink (custom)
        - 51-65: warning
        - 1-50: danger
        """
        for record in self:
            score = record.final_overall_score or 0.0
            if score >= 86:
                record.final_rating_style = "text-bg-success"
            elif score >= 76:
                record.final_rating_style = "text-bg-info"
            elif score >= 66:
                record.final_rating_style = "text-bg-pink"
            elif score >= 51:
                record.final_rating_style = "text-bg-warning"
            elif score > 0:
                record.final_rating_style = "text-bg-danger"
            else:
                record.final_rating_style = False

    def _find_or_create_assessment_note(self, name):
        note = self.env['hr.appraisal.note'].search([
            ('name', '=', name),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not note:
            note = self.env['hr.appraisal.note'].create({
                'name': name,
                'company_id': self.env.company.id,
            })
        return note

    @api.model
    def create_appraisals_for_top_performers(self, score_threshold=4.0):
        """Create appraisals for employees with final scores above threshold"""
        top_performers = self.env["hr.appraisal.goal"].search(
            [("state", "=", "final"), ("final_score", ">=", score_threshold)]
        )
        created_appraisals = []
        for goal in top_performers:
            existing_appraisal = self.search(
                [
                    ("employee_id", "=", goal.employee_id.id),
                    ("state", "in", ["new", "pending"]),
                ],
                limit=1,
            )
            if not existing_appraisal:
                manager_ids = (
                    [(4, goal.department_objective_id.department_id.manager_id.id)]
                    if goal.department_objective_id.department_id.manager_id
                    else []
                )
                appraisal = self.create(
                    {
                        "employee_id": goal.employee_id.id,
                        "manager_ids": manager_ids,
                        "date_close": goal.end_date or fields.Date.today(),
                    }
                )
                created_appraisals.append(appraisal)
        return created_appraisals

    @api.depends("employee_goal_ids.progression")
    def _compute_objectives_progress(self):
        for record in self:
            if record.employee_goal_ids:
                record.objectives_progress = sum(
                    goal.progression for goal in record.employee_goal_ids
                ) / len(record.employee_goal_ids)
            else:
                record.objectives_progress = 0

    @api.depends("employee_goal_ids")
    def _compute_objectives_count(self):
        for record in self:
            record.objectives_count = len(record.employee_goal_ids)

    @api.depends("employee_goal_ids.progression")
    def _compute_avg_progress(self):
        for record in self:
            if record.employee_goal_ids:
                record.avg_progress = sum(
                    goal.progression for goal in record.employee_goal_ids
                ) / len(record.employee_goal_ids)
            else:
                record.avg_progress = 0

    @api.depends("employee_goal_ids.state")
    def _compute_completion_rate(self):
        for record in self:
            if record.employee_goal_ids:
                completed = len(
                    record.employee_goal_ids.filtered(lambda g: g.state == "final")
                )
                record.completion_rate = completed / len(record.employee_goal_ids)
            else:
                record.completion_rate = 0

    @api.depends("employee_goal_ids.final_score")
    def _compute_performance_rank(self):
        for record in self:
            if record.employee_id:
                # Get all employees in the same department
                dept_employees = (
                    self.env["hr.appraisal.goal"]
                    .search(
                        [
                            ("department_id", "=", record.employee_id.department_id.id),
                            ("state", "=", "final"),
                            ("final_score", ">", 0),
                        ]
                    )
                    .mapped("employee_id")
                )

                if dept_employees:
                    # Calculate average scores for ranking
                    employee_scores = []
                    for emp in dept_employees:
                        emp_goals = self.env["hr.appraisal.goal"].search(
                            [
                                ("employee_id", "=", emp.id),
                                ("state", "=", "final"),
                                ("final_score", ">", 0),
                            ]
                        )
                        if emp_goals:
                            avg_score = sum(
                                goal.final_score for goal in emp_goals
                            ) / len(emp_goals)
                            employee_scores.append((emp, avg_score))

                    # Sort by score and find rank
                    employee_scores.sort(key=lambda x: x[1], reverse=True)
                    for i, (emp, score) in enumerate(employee_scores, 1):
                        if emp.id == record.employee_id.id:
                            record.employee_performance_rank = i
                            break
                else:
                    record.employee_performance_rank = 0
            else:
                record.employee_performance_rank = 0

    @api.depends("employee_goal_ids.progression", "employee_goal_ids.create_date")
    def _compute_performance_trends(self):
        for record in self:
            if record.employee_goal_ids:
                # Calculate trend based on progress over time
                goals_with_dates = record.employee_goal_ids.filtered(
                    lambda g: g.create_date
                )
                if len(goals_with_dates) >= 2:
                    # Simple trend calculation based on progress
                    recent_goals = goals_with_dates.sorted("create_date", reverse=True)[
                        :3
                    ]
                    older_goals = goals_with_dates.sorted("create_date")[:3]

                    recent_avg = sum(g.progression for g in recent_goals) / len(
                        recent_goals
                    )
                    older_avg = sum(g.progression for g in older_goals) / len(
                        older_goals
                    )

                    record.department_performance_trend = recent_avg - older_avg
                else:
                    record.department_performance_trend = 0
            else:
                record.department_performance_trend = 0

    @api.onchange("institutional_objective_id", "employee_id")
    def _onchange_institutional_objective(self):
        if not self.institutional_objective_id or not self.employee_id:
            self.employee_goal_ids = [(6, 0, [])]
            return
        dep_objs = self.institutional_objective_id.department_objective_ids
        goals = self.env["hr.appraisal.goal"].search(
            [
                ("department_objective_id", "in", dep_objs.ids),
                ("employee_id", "=", self.employee_id.id),
            ]
        )
        self.employee_goal_ids = [(6, 0, goals.ids)]

    @api.model
    def get_dashboard_data(self):
        """Get dashboard data for HR analytics"""
        try:
            # Department performance
            dept_data = []
            departments = self.env["hr.department"].search([])

            for dept in departments:
                goals = self.env["hr.appraisal.goal"].search(
                    [("department_id", "=", dept.id)]
                )
                if goals:
                    dept_data.append(
                        {
                            "name": dept.name,
                            "total_employees": len(dept.employee_ids),
                            "total_objectives": len(goals),
                            "completed_objectives": len(
                                goals.filtered(lambda g: g.state == "final")
                            ),
                            "avg_score": self._get_dept_avg_score(dept.id),
                            "avg_progress": self._get_dept_avg_progress(dept.id),
                        }
                    )

            # Employee performance ranking
            employee_ranking = self._get_employee_ranking()

            # Progress trends over time
            progress_trends = self._get_progress_trends()

            # Performance alerts
            performance_alerts = self._get_performance_alerts()

            return {
                "department_data": dept_data,
                "employee_ranking": employee_ranking,
                "progress_trends": progress_trends,
                "performance_alerts": performance_alerts,
            }
        except Exception:
            # Return empty data if there's an error
            return {
                "department_data": [],
                "employee_ranking": [],
                "progress_trends": [],
                "performance_alerts": [],
            }

    def _get_dept_avg_score(self, dept_id):
        """Get average score for department"""
        try:
            goals = self.env["hr.appraisal.goal"].search(
                [
                    ("department_id", "=", dept_id),
                    ("state", "=", "final"),
                    ("final_score", ">", 0),
                ]
            )
            return sum(goal.final_score for goal in goals) / len(goals) if goals else 0
        except Exception:
            return 0

    def _get_dept_avg_progress(self, dept_id):
        """Get average progress for department"""
        try:
            goals = self.env["hr.appraisal.goal"].search(
                [("department_id", "=", dept_id), ("progression", ">", 0)]
            )
            return sum(goal.progression for goal in goals) / len(goals) if goals else 0
        except Exception:
            return 0

    def _get_employee_ranking(self):
        """Get employee performance ranking"""
        try:
            employees = self.env["hr.employee"].search([])
            ranking = []

            for emp in employees:
                goals = self.env["hr.appraisal.goal"].search(
                    [
                        ("employee_id", "=", emp.id),
                        ("state", "=", "final"),
                        ("final_score", ">", 0),
                    ]
                )

                if goals:
                    avg_score = sum(goal.final_score for goal in goals) / len(goals)
                    ranking.append(
                        {
                            "employee": emp.name,
                            "department": (
                                emp.department_id.name if emp.department_id else ""
                            ),
                            "avg_score": avg_score,
                            "completed_goals": len(goals),
                        }
                    )

            return sorted(ranking, key=lambda x: x["avg_score"], reverse=True)[:10]
        except Exception:
            return []

    def _get_progress_trends(self):
        """Get progress trends over time"""
        try:
            # Get last 6 months of data
            from datetime import datetime, timedelta

            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)

            trends = []
            current_date = start_date

            while current_date <= end_date:
                month_start = current_date.replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(
                    day=1
                ) - timedelta(days=1)

                goals = self.env["hr.appraisal.goal"].search(
                    [
                        ("create_date", ">=", month_start),
                        ("create_date", "<=", month_end),
                        ("progression", ">", 0),
                    ]
                )

                avg_progress = (
                    sum(goal.progression for goal in goals) / len(goals) if goals else 0
                )

                trends.append(
                    {
                        "month": current_date.strftime("%B %Y"),
                        "avg_progress": avg_progress,
                        "objectives_count": len(goals),
                    }
                )

                current_date = (current_date + timedelta(days=32)).replace(day=1)

            return trends
        except Exception:
            return []

    def _get_performance_alerts(self):
        """Get performance alerts for HR attention"""
        try:
            alerts = []

            # Low progress objectives
            low_progress_goals = self.env["hr.appraisal.goal"].search(
                [
                    ("progression", "<", 30),
                    ("deadline_days", "<", 14),
                    ("state", "in", ["progress"]),
                ]
            )

            for goal in low_progress_goals:
                alerts.append(
                    {
                        "type": "low_progress",
                        "message": f"Low progress alert: {goal.employee_id.name} - {goal.name}",
                        "progress": goal.progression,
                        "days_left": goal.deadline_days,
                    }
                )

            # Overdue objectives
            overdue_goals = self.env["hr.appraisal.goal"].search(
                [("deadline_days", "<", 0), ("state", "in", ["progress"])]
            )

            for goal in overdue_goals:
                alerts.append(
                    {
                        "type": "overdue",
                        "message": f"Overdue objective: {goal.employee_id.name} - {goal.name}",
                        "days_overdue": abs(goal.deadline_days),
                    }
                )

            return alerts
        except Exception:
            return []

    def action_view_my_appraisals(self):
        """Open employee's own appraisals"""
        self.ensure_one()
        return {
            'name': 'My Appraisals',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.appraisal',
            'view_mode': 'list,form',
            'domain': [('employee_id.user_id', '=', self.env.user.id)],
            'context': {'create': False},
        }

    def action_view_my_evaluation(self):
        """Open employee's evaluation dashboard for this appraisal"""
        self.ensure_one()
        return {
            'name': 'My Evaluation',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.appraisal',
            'view_mode': 'form',
            'view_id': self.env.ref('hr_appraisal_objectives.view_hr_appraisal_evaluation_form').id,
            'res_id': self.id,
            'target': 'new',
        }

    def action_view_employee_appraisals(self):
        """Open employee appraisals summary view for supervisors"""
        return {
            'name': 'Employee Appraisals',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.appraisal.summary',
            'view_mode': 'kanban,list',
            'context': {},
            'help': '''
                <p class="o_view_nocontent_smiling_face">
                    Manage Employee Appraisals
                </p>
                <p>
                    This view provides a summary of appraisals for each employee, including current and previous fiscal years.
                </p>
            ''',
        }
    
    def action_view_objectives(self):
        """Open individual objectives for this appraisal"""
        self.ensure_one()
        return {
            'name': f'Objectives - {self.employee_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.appraisal.goal',
            'view_mode': 'list,form',
            'domain': [('appraisal_id', '=', self.id)],
            'context': {'default_appraisal_id': self.id},
        }
    
    # Override base method to allow manager feedback template during self_scored state
    @api.depends('department_id', 'appraisal_template_id')
    def _compute_manager_feedback(self):
        for appraisal in self.filtered(lambda a: a.state in ['new', 'pending', 'self_scored']):
            manager_template = appraisal._get_appraisal_template('manager')
            if appraisal.state == 'new':
                appraisal.manager_feedback = manager_template
            else:
                appraisal.manager_feedback = appraisal.manager_feedback or manager_template
