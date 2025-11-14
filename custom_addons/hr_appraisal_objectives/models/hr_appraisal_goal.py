from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrAppraisalGoal(models.Model):
    _inherit = "hr.appraisal.goal"

    reference = fields.Char(
        string="Reference", readonly=True, copy=False, default="New"
    )
    name_short = fields.Char("Short Name", compute="_compute_name_short")
    appraisal_id = fields.Many2one(
        "hr.appraisal", string="Appraisal", ondelete="cascade"
    )
    department_objective_id = fields.Many2one(
        "hr.department.objective", string="Department Objective", ondelete="cascade"
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        related="department_objective_id.department_id",
        store=True,
        readonly=True,
    )
    institutional_objective_id = fields.Many2one(
        "hr.institutional.objective",
        string="Institutional Objective",
        ondelete="cascade",
    )
    # Fiscal year follows the institutional/department objective
    fiscal_year_id = fields.Many2one(
        'hr.fiscal.year',
        string='Fiscal Year',
        compute='_compute_fiscal_year',
        store=True,
        readonly=True,
    )
    # Mark goals belonging to the current fiscal year (for search filters)
    is_current_fy = fields.Boolean(
        string="Is Current Fiscal Year",
        compute="_compute_is_current_fy",
        store=True,
        index=True,
    )
    # Common objective flags
    is_common = fields.Boolean(string="Common Objective", default=False, help="Objective published from a common objective and not tied to a specific department objective")
    common_origin_id = fields.Many2one(
        "hr.common.objective",
        string="Common Objective",
        help="Source common objective if this goal was auto-generated",
        readonly=True,
        copy=False,
    )
    kpi_line_ids = fields.One2many(
        "hr.appraisal.goal.kpi", "appraisal_goal_id", string="KPIs"
    )
    target = fields.Char()
    measurement_method = fields.Char()
    weight = fields.Integer(default=1)
    self_score = fields.Float("Score", help="Score (0-100)")
    manager_score = fields.Float("Manager Score", help="Line manager's score (0-100)")
    supervisor_score = fields.Float(
        "HR Score", help="HR's score (0-100)"
    )
    final_score = fields.Float(
        "Final Score", compute="_compute_final_score", store=True
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

    # Scoring notes
    self_notes = fields.Text("Comment", help="Comments during scoring")
    manager_notes = fields.Text(
        "Manager Comment", help="Comments from manager during scoring"
    )
    supervisor_notes = fields.Text(
        "HR Comment", help="Comments from HR supervisor during scoring"
    )
    review_summary = fields.Html(
        "Review Summary", compute="_compute_review_summary", store=True
    )

    # Debug/Display helper: surface the parent appraisal's state on the goal
    appraisal_state = fields.Selection(
        related="appraisal_id.state",
        string="Appraisal State",
        store=False,
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "To Review"),
            ("first_approved", "To Approve"),
            ("progress", "Active"),
            ("progress_done", "Done"),
        ],
        default="draft",
        string="Status",
        tracking=True,
    )
    rejection_reason = fields.Text("Rejection Reason")
    rejection_stage = fields.Selection(
        [("first", "First Approval"), ("second", "Second Approval")],
        string="Rejection Stage",
    )
    rejected = fields.Boolean(string="Rejected", default=False)
    create_uid = fields.Many2one(
        "res.users", "Created by", readonly=True, default=lambda self: self.env.uid
    )
    current_uid_int = fields.Integer(
        string="Current User ID", compute="_compute_current_uid", store=False
    )
    employee_user_id_int = fields.Integer(
        string="Employee User ID", compute="_compute_employee_user_id", store=False
    )
    manager_user_id_int = fields.Integer(
        string="Manager User ID", compute="_compute_manager_user_id", store=False
    )
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date(compute="_onchange_dates_from_sources")
    deadline = fields.Date(
        string="Deadline", help="Deadline for completing this objective"
    )
    deadline_days = fields.Integer(compute="_compute_deadline_days", store=True)
    kpi_count = fields.Integer(
        compute="_compute_kpi_count", string="Number of KPIs", store=True
    )
    kpi_total_weight = fields.Integer(
        compute="_compute_kpi_total_weight", string="Total KPI Weight", store=True
    )
    
    # Field for employee autocomplete
    employee_autocomplete_ids = fields.Many2many(
        "hr.employee", 
        string="Available Employees",
        compute="_compute_employee_autocomplete_ids",
        store=False
    )
    
    # Attachment fields for supporting documents at each assessment level
    self_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_appraisal_goal_self_attachment_rel",
        "goal_id", "attachment_id",
        string="Self Assessment Documents",
        help="Supporting documents for self assessment"
    )
    manager_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_appraisal_goal_manager_attachment_rel",
        "goal_id", "attachment_id",
        string="Manager Assessment Documents", 
        help="Supporting documents for manager assessment"
    )
    hr_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_appraisal_goal_hr_attachment_rel",
        "goal_id", "attachment_id",
        string="HR Assessment Documents",
        help="Supporting documents for HR assessment"
    )
    
    # General attachment field (keeping for backward compatibility)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_appraisal_goal_attachment_rel",
        "goal_id", "attachment_id",
        string="General Attachments",
        help="General supporting documents for this objective"
    )

    # Ensure grouping never applies AVG to employee_id in pivots/graphs
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        aggregator='count',
    )
    
    avatar_128 = fields.Image(related='employee_id.avatar_128')

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date >= record.end_date:
                    raise ValidationError("Opening date must be before closing date.")
                # Enforce within source bounds if present
                source_start = False
                source_end = False
                if record.is_common and record.common_origin_id:
                    source_start = record.common_origin_id.start_date
                    source_end = record.common_origin_id.end_date
                elif record.institutional_objective_id:
                    source_start = record.institutional_objective_id.start_date
                    source_end = record.institutional_objective_id.end_date
                if source_start and record.start_date < source_start:
                    raise ValidationError("Start date cannot be before the linked objective's start date.")
                if source_end and record.end_date > source_end:
                    raise ValidationError("End date cannot be after the linked objective's end date.")
                    
    @api.constrains("self_score")
    def _check_self_score_range(self):
        for record in self:
            if record.self_score is not None and (
                record.self_score < 0 or record.self_score > 100
            ):
                raise ValidationError("Score must be between 0 and 100.")

    @api.constrains("manager_score")
    def _check_manager_score_range(self):
        for record in self:
            if record.manager_score is not None and (
                record.manager_score < 0 or record.manager_score > 100
            ):
                raise ValidationError("Manager's score must be between 0 and 100.")

    @api.constrains("supervisor_score")
    def _check_supervisor_score_range(self):
        for record in self:
            if record.supervisor_score is not None and (
                record.supervisor_score < 0 or record.supervisor_score > 100
            ):
                raise ValidationError("HR's score must be between 0 and 100.")

    @api.depends("kpi_line_ids")
    def _compute_kpi_count(self):
        for rec in self:
            rec.kpi_count = len(rec.kpi_line_ids) if rec.kpi_line_ids else 0

    @api.depends('kpi_line_ids.weight')
    def _compute_kpi_total_weight(self):
        for rec in self:
            rec.kpi_total_weight = sum((k.weight or 0) for k in rec.kpi_line_ids)

    @api.depends()
    def _compute_employee_autocomplete_ids(self):
        """Compute available employees for autocomplete"""
        for rec in self:
            # Get all employees from the same department
            if rec.department_objective_id and rec.department_objective_id.department_id:
                rec.employee_autocomplete_ids = self.env['hr.employee'].search([
                    ('department_id', '=', rec.department_objective_id.department_id.id)
                ])
            else:
                rec.employee_autocomplete_ids = self.env['hr.employee'].search([])


    @api.depends('institutional_objective_id.fiscal_year_id',
                 'common_origin_id.fiscal_year_id',
                 'is_common')
    def _compute_fiscal_year(self):
        for rec in self:
            fy = False
            if rec.is_common and rec.common_origin_id:
                # Common objectives now have fiscal_year_id directly
                fy = rec.common_origin_id.fiscal_year_id
            elif rec.institutional_objective_id:
                fy = rec.institutional_objective_id.fiscal_year_id
            rec.fiscal_year_id = fy.id if fy else False

    @api.depends('fiscal_year_id')
    def _compute_is_current_fy(self):
        current_fy = self.env['hr.fiscal.year'].sudo().get_current_fiscal_year()
        current_id = current_fy.id if current_fy else False
        for rec in self:
            rec.is_current_fy = bool(rec.fiscal_year_id and rec.fiscal_year_id.id == current_id)

    @api.depends("name")
    def _compute_name_short(self):
        for rec in self:
            if rec.name and len(rec.name) > 30:
                rec.name_short = rec.name[:30] + "..."
            else:
                rec.name_short = rec.name

    @api.model
    def create(self, vals):
        if vals.get("reference", "New") == "New":
            vals["reference"] = (
                self.env["ir.sequence"].next_by_code("hr.appraisal.goal") or "/"
            )
        return super().create(vals)

    @api.depends("self_score", "manager_score", "supervisor_score")
    def _compute_final_score(self):
        for record in self:
            # Formula: 40% Employee + 60% (Average of HR & Line Manager)
            employee_score = record.self_score or 0
            manager_score = record.manager_score or 0
            hr_score = record.supervisor_score or 0
            
            # Calculate average of manager and HR scores
            management_scores = []
            if manager_score > 0:
                management_scores.append(manager_score)
            if hr_score > 0:
                management_scores.append(hr_score)
            
            if management_scores:
                avg_management_score = sum(management_scores) / len(management_scores)
            else:
                avg_management_score = 0
            
            # Apply the 40% employee + 60% management formula
            if employee_score > 0 and avg_management_score > 0:
                record.final_score = (employee_score * 0.4) + (avg_management_score * 0.6)
            elif employee_score > 0:
                # If only employee score available, use it
                record.final_score = employee_score
            elif avg_management_score > 0:
                # If only management scores available, use them
                record.final_score = avg_management_score
            else:
                record.final_score = 0
    
    @api.depends("final_score")
    def _compute_rating_scale(self):
        """Compute the rating scale based on final score"""
        for record in self:
            if record.final_score > 0:
                rating = self.env['hr.appraisal.rating.scale'].get_rating_for_score(record.final_score)
                record.rating_scale_id = rating.id if rating else False
            else:
                record.rating_scale_id = False

    @api.depends(
        "self_score",
        "manager_score",
        "supervisor_score",
        "manager_notes",
        "supervisor_notes",
        "state",
    )
    def _compute_review_summary(self):
        """Compute comprehensive review summary for final state"""
        for record in self:
            if record.state == "final":
                summary_parts = []

                # Employee self-assessment
                if record.self_score:
                    summary_parts.append(
                        f"""
                    <div class="alert alert-info">
                        <h6><i class="fa fa-user"></i> Self Assessment</h6>
                        <p><strong>Score:</strong> {record.self_score:.1f}/100</p>
                    </div>
                    """
                    )

                # Manager review
                if record.manager_score:
                    manager_section = f"""
                    <div class="alert alert-warning">
                        <h6><i class="fa fa-user-tie"></i> Manager Review</h6>
                        <p><strong>Score:</strong> {record.manager_score:.1f}/100</p>
                    """
                    if record.manager_notes:
                        manager_section += (
                            f"<p><strong>Comments:</strong> {record.manager_notes}</p>"
                        )
                    manager_section += "</div>"
                    summary_parts.append(manager_section)

                # HR review
                if record.supervisor_score:
                    supervisor_section = f"""
                    <div class="alert alert-success">
                        <h6><i class="fa fa-star"></i> HR Review</h6>
                        <p><strong>Score:</strong> {record.supervisor_score:.1f}/100</p>
                    """
                    if record.supervisor_notes:
                        supervisor_section += (
                            f"<p><strong>Comments:</strong> {record.supervisor_notes}</p>"
                        )
                    supervisor_section += "</div>"
                    summary_parts.append(supervisor_section)

                # Final score
                if record.final_score:
                    final_score_html = f"""
                    <div class="alert alert-{'success' if record.final_score >= 80 else 'warning' if record.final_score >= 60 else 'danger'}">
                        <h6><i class="fa fa-trophy"></i> Final Assessment</h6>
                        <h4><strong>Final Score: {record.final_score:.1f}/100</strong></h4>
                        <p><strong>Performance Level:</strong> {
                            'Excellent' if record.final_score >= 80 
                            else 'Good' if record.final_score >= 60 
                            else 'Needs Improvement'
                        }</p>
                    </div>
                    """
                    summary_parts.append(final_score_html)

                record.review_summary = (
                    "".join(summary_parts)
                    if summary_parts
                    else "<p>No review data available.</p>"
                )
            else:
                record.review_summary = ""

    @api.onchange("department_objective_id", "is_common", "common_origin_id", "institutional_objective_id")
    def _onchange_dates_from_sources(self):
        for record in self:
            # Prefill from source bounds but do not block user edits afterwards
            source_start = False
            source_end = False
            if record.is_common and record.common_origin_id:
                source_start = record.common_origin_id.start_date
                source_end = record.common_origin_id.end_date
            elif record.institutional_objective_id:
                inst_obj = record.institutional_objective_id
                source_start = inst_obj.start_date
                source_end = inst_obj.end_date

            # If not set yet, prefill sensible defaults
            if source_start or source_end:
                today = fields.Date.today()
                # Default start: today
                if not record.start_date:
                    record.start_date = today
                # Default end: source_end if available
                if not record.end_date and source_end:
                    record.end_date = source_end

            # Clamp end within upper bound if known
            if source_end and record.end_date and record.end_date > source_end:
                record.end_date = source_end

    @api.depends("end_date")
    def _compute_deadline_days(self):
        for record in self:
            if record.end_date:
                today = fields.Date.today()
                delta = record.end_date - today
                record.deadline_days = delta.days
            else:
                record.deadline_days = 0

    def _compute_current_uid(self):
        for rec in self:
            rec.current_uid_int = self.env.uid

    def _compute_employee_user_id(self):
        for rec in self:
            rec.employee_user_id_int = (
                rec.employee_id.user_id.id if rec.employee_id and rec.employee_id.user_id else 0
            )

    @api.depends("department_objective_id.department_id")
    def _compute_manager_user_id(self):
        for rec in self:
            manager_user = (
                rec.department_objective_id.department_id.manager_id.user_id
                if rec.department_objective_id
                and rec.department_objective_id.department_id
                and rec.department_objective_id.department_id.manager_id
                and rec.department_objective_id.department_id.manager_id.user_id
                else False
            )
            rec.manager_user_id_int = manager_user.id if manager_user else 0

    def action_submit(self):
        """Submit the individual objective for approval"""
        for rec in self:
            if not rec.kpi_line_ids:
                raise UserError("Please add at least one KPI before submitting.")
            rec.rejected = False
            rec.rejection_reason = False
            rec.rejection_stage = False
            rec.write({"state": "submitted"})
            rec._send_notification("submitted")
            
            # Create activity for line manager to review
            if rec.department_objective_id and rec.department_objective_id.department_id:
                dept = rec.department_objective_id.department_id
                if dept.manager_id and dept.manager_id.user_id:
                    rec._create_approval_activity(
                        user_id=dept.manager_id.user_id.id,
                        summary=f"Review Objective: {rec.name}",
                        note=f"""<p><strong>Employee:</strong> {rec.employee_id.name}</p>
                              <p><strong>Department:</strong> {dept.name}</p>
                              <p><strong>Action Required:</strong> First Approval</p>
                              <p>Please review and approve or reject this objective.</p>"""
                    )

    def action_first_approve(self):
        """Approve the individual objective"""
        for rec in self:
            # Mark previous activities as done (use sudo to avoid ir.model access issues)
            rec.activity_ids.filtered(
                lambda a: a.user_id == self.env.user and a.res_model == 'hr.appraisal.goal'
            ).action_feedback(feedback="Approved")
            
            rec.write({"state": "first_approved"})
            rec._send_notification("first_approved")
            
            # Create activity for HR managers to review
            hr_group = self.env.ref('hr_appraisal_objectives.group_hr_appraisal', raise_if_not_found=False)
            if hr_group:
                hr_users = hr_group.users
                for hr_user in hr_users:
                    rec._create_approval_activity(
                        user_id=hr_user.id,
                        summary=f"HR Review Objective: {rec.name}",
                        note=f"""<p><strong>Employee:</strong> {rec.employee_id.name}</p>
                              <p><strong>Department:</strong> {rec.department_objective_id.department_id.name if rec.department_objective_id else 'N/A'}</p>
                              <p><strong>Action Required:</strong> Final HR Approval</p>
                              <p><strong>Line Manager:</strong> Approved by {self.env.user.name}</p>
                              <p>Please review and give final approval to start this objective.</p>"""
                    )

    def action_second_approve(self):
        """Approve the individual objective and automatically start it"""
        for rec in self:
            # Mark previous activities as done (use sudo to avoid ir.model access issues)
            rec.activity_ids.filtered(
                lambda a: a.user_id == self.env.user and a.res_model == 'hr.appraisal.goal'
            ).action_feedback(feedback="Approved by HR")
            
            rec.write({"state": "progress"})  # Automatically transition to progress (ongoing)
            rec._send_notification("progress")
            
            # Notify employee that objective is approved and active
            if rec.employee_id and rec.employee_id.user_id:
                rec._create_approval_activity(
                    user_id=rec.employee_id.user_id.id,
                    summary=f"Objective Approved: {rec.name}",
                    note=f"""<p><strong>Status:</strong> Your objective has been approved!</p>
                          <p><strong>Action Required:</strong> Start working on your objective</p>
                          <p>Your objective has been approved by management and HR. You can now begin work.</p>"""
                )
            # Auto-create tasks for each KPI if not already linked
            # for kpi in rec.kpi_line_ids:
            #     if not kpi.task_ids:
            #         # Auto-select project based on the Institutional Objective name
            #         project = kpi.project_id
            #         if not project:
            #             inst_name = rec.institutional_objective_id.name if rec.institutional_objective_id else False
            #             project_name = inst_name or (f"Objectives - {rec.employee_id.name}" if rec.employee_id else "Objectives")
            #             project = self.env['project.project'].search([('name','=', project_name)], limit=1)
            #             if not project:
            #                 project = self.env['project.project'].create({'name': project_name, 'allow_timesheets': True})
            #         vals = {
            #             "name": kpi.kpi or rec.name,
            #             "project_id": project.id if project else False,
            #             "user_ids": [(4, rec.employee_id.user_id.id)] if rec.employee_id and rec.employee_id.user_id else False,
            #             "date_deadline": rec.deadline,
            #             "description": kpi.description or rec.name,
            #         }
            #         # Add planned hours only if the field exists on project.task in this database
            #         if "planned_hours" in self.env["project.task"]._fields:
            #             vals["planned_hours"] = kpi.planned_hours or 0.0
            #         task = self.env["project.task"].create(vals)
            #         if task:
            #             kpi.write({"task_ids": [(4, task.id)]})

    def action_first_reject_open(self):
        """Open rejection wizard for first approval stage"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Reject Objective",
            "res_model": "hr.appraisal.goal.rejection.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_goal_id": self.id,
                "default_rejection_level": "first",
            },
        }

    def action_second_reject_open(self):
        """Open rejection wizard for second approval stage"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Reject Objective",
            "res_model": "hr.appraisal.goal.rejection.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_goal_id": self.id,
                "default_rejection_level": "second",
            },
        }


    def action_end_progress(self):
        for rec in self:
            if rec.state == 'progress':
                # Require self score before marking as done
                if rec.employee_id and rec.employee_id.user_id and rec.employee_id.user_id.id == self.env.uid:
                    if rec.self_score is None or rec.self_score == 0:
                        raise UserError("Please provide your score before marking as done.")
                rec.write({'state': 'progress_done'})
                self.write({'progression': '100'})
                # Create or update appraisal immediately so review can proceed there
                appraisal = self.env['hr.appraisal'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', 'in', ['new', 'pending'])
                ], limit=1)
                manager_emp = rec.manager_id or rec.employee_id.parent_id
                inst_id = rec.institutional_objective_id.id if rec.institutional_objective_id else False
                if not appraisal:
                    create_vals = {
                        'employee_id': rec.employee_id.id,
                    }
                    if manager_emp:
                        create_vals['manager_ids'] = [(4, manager_emp.id)]
                    if inst_id:
                        create_vals['institutional_objective_id'] = inst_id
                    appraisal = self.env['hr.appraisal'].create(create_vals)
                else:
                    write_vals = {}
                    if manager_emp and manager_emp.id not in appraisal.manager_ids.ids:
                        write_vals.setdefault('manager_ids', []).append((4, manager_emp.id))
                    if inst_id and not appraisal.institutional_objective_id:
                        write_vals['institutional_objective_id'] = inst_id
                    if write_vals:
                        appraisal.write(write_vals)
                if rec.id not in appraisal.employee_goal_ids.ids:
                    appraisal.write({'employee_goal_ids': [(4, rec.id)]})
        return True

    def _create_approval_activity(self, user_id, summary, note):
        """Helper method to create approval activities"""
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
                _logger.info(f"Created activity for user {user_id}: {summary}")
        except Exception as e:
            _logger.warning(f"Failed to create activity: {str(e)}")
            # Never block workflow on activity creation failure
            pass
    
    def _send_notification(self, action):
        """Send notifications and create activities for the appropriate users"""
        for record in self:
            if action not in [
                "submitted",
                "first_approved",
                "progress",
                "self_scored",
                "scored",
                "final",
                "rejected",
            ]:
                continue
            
            action_labels = {
                "submitted": "submitted, waiting for first approval",
                "first_approved": "first approved, waiting for HR approval",
                "progress": "approved and active",
                "self_scored": "scored, waiting for manager review",
                "scored": "scored by manager, waiting for supervisor review",
                "final": "finalized with supervisor score",
                "rejected": "rejected and returned to draft",
            }
            
            # Post chatter message
            if record.department_objective_id and record.department_objective_id.department_id:
                dept = record.department_objective_id.department_id
                if dept.manager_id and dept.manager_id.user_id:
                    record.sudo().message_post(
                        body=f"<p><strong>Objective {action_labels[action].capitalize()}: {record.name}</strong></p>"
                             f"<p>Objective for {record.employee_id.name} has been {action_labels[action]}.</p>"
                             + (f"<p><strong>Reason:</strong> {record.rejection_reason}</p>" if record.rejection_reason else ""),
                        partner_ids=[dept.manager_id.user_id.partner_id.id],
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                    )
            
            # Create activities for the appropriate users
            # Don't create activities here for submitted/first_approved/progress 
            # as they're handled in the action methods
            if action == "rejected" and record.employee_id and record.employee_id.user_id:
                # For rejection, notify employee (also handled in rejection wizard)
                pass
            elif action in ["self_scored", "scored"]:
                # For scoring states, create activities
                try:
                    summary = f"Objective {record.name}: {action_labels[action]}"
                    note = f"Employee: {record.employee_id.name}\nStatus: {action_labels[action].capitalize()}"
                    
                    # Determine recipient based on action
                    recipient_user = None
                    if action == "self_scored" and record.department_objective_id:
                        # Manager needs to review
                        dept = record.department_objective_id.department_id
                        if dept and dept.manager_id and dept.manager_id.user_id:
                            recipient_user = dept.manager_id.user_id
                    elif action == "scored":
                        # HR needs to review
                        hr_group = self.env.ref('hr_appraisal_objectives.group_hr_appraisal', raise_if_not_found=False)
                        if hr_group and hr_group.users:
                            recipient_user = hr_group.users[0]  # Assign to first HR user
                    
                    if recipient_user:
                        record.activity_schedule(
                            'mail.mail_activity_data_todo',
                            date_deadline=fields.Date.today(),
                            user_id=recipient_user.id,
                            summary=summary,
                            note=note,
                        )
                except Exception as e:
                    _logger.warning(f"Failed to create activity: {str(e)}")
                    pass

    @api.model
    def cron_sync_kpi_progress(self):
        goals = self.search([('state','in',['progress','self_scored','scored'])])
        for goal in goals:
            for kpi in goal.kpi_line_ids:
                if kpi.progress_method == "manual":
                    continue
                total = len(kpi.task_ids)
                value = 0.0
                if kpi.progress_method == "timesheet_ratio":
                    planned = kpi.planned_hours or 0.0
                    if planned > 0:
                        aal = self.env['account.analytic.line'].read_group(
                            domain=[('task_id','in',kpi.task_ids.ids), ('employee_id', '=', kpi.employee_id.id)],
                            fields=['unit_amount:sum'], groupby=[])
                        done_hours = (aal[0]['unit_amount_sum'] if aal else 0.0) or 0.0
                        value = round(min(done_hours / planned, 1.0) * 100.0, 2)
                else:
                    if total:
                        done = len(kpi.task_ids.filtered(lambda t: getattr(t.stage_id, 'fold', False)))
                        value = round(100.0 * done / total, 2)
                kpi.write({'progress_percentage': value})
        return True

    @api.model
    def cron_finalize_and_create_appraisals(self):
        today = fields.Date.today()
        goals = self.search([('end_date', '!=', False), ('end_date', '<=', today), ('state', 'in', ['progress', 'progress_done', 'self_scored', 'scored'])])
        for g in goals:
            if g.state == 'progress':
                g.write({'state': 'progress_done'})
            g.write({'state': 'final'})
            appraisal = self.env['hr.appraisal'].search([('employee_id','=', g.employee_id.id), ('state', 'in', ['new', 'pending'])], limit=1)
            manager_emp = g.manager_id or g.employee_id.parent_id
            inst_id = g.institutional_objective_id.id if g.institutional_objective_id else False
            if not appraisal:
                create_vals = {'employee_id': g.employee_id.id}
                if manager_emp:
                    create_vals['manager_ids'] = [(4, manager_emp.id)]
                if inst_id:
                    create_vals['institutional_objective_id'] = inst_id
                appraisal = self.env['hr.appraisal'].create(create_vals)
            else:
                write_vals = {}
                if manager_emp and manager_emp.id not in appraisal.manager_ids.ids:
                    write_vals.setdefault('manager_ids', []).append((4, manager_emp.id))
                if inst_id and not appraisal.institutional_objective_id:
                    write_vals['institutional_objective_id'] = inst_id
                if write_vals:
                    appraisal.write(write_vals)
            if g.id not in appraisal.employee_goal_ids.ids:
                appraisal.write({'employee_goal_ids': [(4, g.id)]})
        return True

    # --- Edit restrictions for specific fields after approval ---
    def write(self, vals):
        blocked_states = {"first_approved", "progress", "self_scored", "scored", "final"}
        # Fields that are restricted for all users when in blocked states
        restricted_fields = {
            "name", "employee_id", "manager_id", "department_objective_id", 
            "institutional_objective_id", "start_date", "end_date", "kpi_line_ids"
        }

        for rec in self:
            if rec.state in blocked_states:
                # Check if trying to modify any restricted fields
                fields_being_modified = set(vals.keys())
                restricted_being_modified = fields_being_modified.intersection(restricted_fields)
                _logger.info(f"Fields being modified: {fields_being_modified}")
                _logger.info(f"Restricted fields being modified: {restricted_being_modified}")
                if restricted_being_modified:
                    raise UserError(
                        f"You cannot modify the following fields after the objective has been approved: {', '.join(restricted_being_modified)}"
                    )
        return super().write(vals)

    # def unlink(self):
    #     blocked_states = {"first_approved", "progress", "progress_done", "self_scored", "scored", "final"}
    #     for rec in self:
    #         if rec.state in blocked_states:
    #             raise UserError(
    #                 "You cannot delete the objective after it has been approved."
    #             )
    #     return super().unlink()
