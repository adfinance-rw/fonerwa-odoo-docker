from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrInstitutionalObjective(models.Model):
    _name = "hr.institutional.objective"
    _description = "Institutional Objective"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    reference = fields.Char(
        string="Reference", readonly=True, copy=False, default="New"
    )
    name = fields.Char(required=True)
    description = fields.Html()
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date(required=True)
    deadline_days = fields.Integer(
        string="Days to Deadline", compute="_compute_deadline_days", store=True
    )
    department_objective_ids = fields.One2many(
        "hr.department.objective",
        "institutional_objective_id",
        string="Department Objectives",
    )
    progress = fields.Float(
        string="Progress (%)",
        compute="_compute_progress",
        store=True,
        aggregator="avg",
    )
    department_objective_count = fields.Integer(
        compute="_compute_department_objective_count",
        string="Department Count",
        store=True,
    )
    total_individual_objectives = fields.Integer(
        compute="_compute_total_individual_objectives",
        string="Total Individual Objectives",
        store=True,
    )
    avg_score = fields.Float(
        string="Average Score",
        compute="_compute_avg_score",
        store=True,
        aggregator="avg",
    )
    create_uid = fields.Many2one(
        "res.users", "Created by", readonly=True, default=lambda self: self.env.uid
    )
    current_uid_int = fields.Integer(
        string="Current User ID", compute="_compute_current_uid", store=False
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

    # Link to fiscal year chosen based on the selected dates
    fiscal_year_id = fields.Many2one(
        "hr.fiscal.year",
        string="Fiscal Year",
        compute="_compute_fiscal_year",
        store=True,
        readonly=False,
        help="Fiscal year is determined from the objective dates."
    )

    risk_label = fields.Char(
        string="Risk Level", compute="_compute_risk_label", store=False
    )
    risk_message = fields.Char(
        string="Risk Message", compute="_compute_risk_label", store=False
    )
    risk_alert_class = fields.Char(
        string="Risk Alert Class", compute="_compute_risk_label", store=False
    )
    risk_alert_full_class = fields.Char(
        string="Risk Alert Full Class", compute="_compute_risk_label", store=False
    )

    strength_label = fields.Char(
        string="Strengths", compute="_compute_labels", store=False
    )
    improvement_label = fields.Char(
        string="Areas for Improvement", compute="_compute_labels", store=False
    )
    recommendation_label = fields.Char(
        string="Recommendations", compute="_compute_labels", store=False
    )

    def _compute_labels(self):
        for record in self:
            # Strengths
            if record.department_objective_count > 3:
                record.strength_label = "Good department coverage"
            else:
                record.strength_label = "Focused approach"

            # Areas for Improvement
            if record.progress < 70:
                record.improvement_label = "Progress acceleration needed"
            else:
                record.improvement_label = "Maintain momentum"

            # Recommendations
            if record.avg_score < 3.5:
                record.recommendation_label = "Focus on quality improvement"
            else:
                record.recommendation_label = "Continue excellence"

    def _compute_risk_label(self):
        for record in self:
            if record.progress < 30:
                record.risk_label = "High Risk"
                record.risk_message = "Immediate attention required"
                record.risk_alert_class = "alert-danger"
                record.risk_alert_full_class = "alert alert-danger"
            elif record.progress < 60:
                record.risk_label = "Medium Risk"
                record.risk_message = "Monitor closely"
                record.risk_alert_class = "alert-warning"
                record.risk_alert_full_class = "alert alert-warning"
            else:
                record.risk_label = "Low Risk"
                record.risk_message = "On track"
                record.risk_alert_class = "alert-success"
                record.risk_alert_full_class = "alert alert-success"

    def unlink(self):
        for record in self:
            linked_goals = self.env["hr.department.objective"].search(
                [
                    ("institutional_objective_id", "=", record.id),
                    ("state", "!=", "draft"),
                ]
            )
            if linked_goals:
                raise ValidationError(
                    _(
                        "Cannot delete Institutional Objective '%s' because it is linked to department objectives that are not in draft state."
                    )
                    % record.name
                )
        return super(HrInstitutionalObjective, self).unlink()

    @api.model
    def create(self, vals):
        if vals.get("reference", "New") == "New":
            vals["reference"] = (
                self.env["ir.sequence"].next_by_code("hr.institutional.objective")
                or "/"
            )
        return super().create(vals)

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

    @api.depends("end_date")
    def _compute_deadline_days(self):
        for record in self:
            if record.end_date:
                today = fields.Date.today()
                delta = record.end_date - today
                record.deadline_days = delta.days
            else:
                record.deadline_days = 0

    @api.depends("department_objective_ids", "department_objective_ids.state")
    def _compute_department_objective_count(self):
        for rec in self:
            rec.department_objective_count = len(rec.department_objective_ids.filtered(lambda d: d.state != "draft"))

    @api.depends("department_objective_ids", "department_objective_ids.state", "department_objective_ids.appraisal_goal_ids", "department_objective_ids.appraisal_goal_ids.state")
    def _compute_total_individual_objectives(self):
        for rec in self:
            total = sum(
                len(dept.appraisal_goal_ids.filtered(lambda g: g.state != "draft")) for dept in rec.department_objective_ids.filtered(lambda d: d.state != "draft")
            )
            rec.total_individual_objectives = total

    @api.depends("department_objective_ids.progress")
    def _compute_progress(self):
        for record in self:
            departments = record.department_objective_ids
            vals = [
                float(d.progress or 0) for d in departments if d.progress is not None
            ]
            if vals:
                record.progress = sum(vals) / len(vals)
            else:
                record.progress = 0

    @api.depends("department_objective_ids.avg_score")
    def _compute_avg_score(self):
        for record in self:
            departments = record.department_objective_ids
            scores = [d.avg_score for d in departments if d.avg_score > 0]
            if scores:
                record.avg_score = sum(scores) / len(scores)
            else:
                record.avg_score = 0

    @api.model
    def _compute_all_analytics_fields(self):
        """Compute all analytics fields for a record"""
        for record in self:
            record._compute_risk_label()
            record._compute_labels()

    def _compute_current_uid(self):
        for rec in self:
            rec.current_uid_int = self.env.uid

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date >= record.end_date:
                    raise ValidationError("Opening date must be before closing date.")
                elif record.start_date < fields.Date.today():
                    raise ValidationError("Opening date cannot be in the past.")

    @api.constrains("end_date", "fiscal_year_id")
    def _check_end_date_within_fiscal_year(self):
        for record in self:
            if record.fiscal_year_id and record.end_date:
                fy_end = record.fiscal_year_id.date_to
                if fy_end and record.end_date > fy_end:
                    raise ValidationError("End date cannot be after the fiscal year's end date.")

    def action_start(self):
        """Start the institutional objective"""
        self.write({"state": "active"})

    def action_complete(self):
        """Mark as completed"""
        self.write({"state": "completed"})

    def action_cancel(self):
        """Cancel the objective"""
        self.write({"state": "cancelled"})

    def action_view_department_objectives(self):
        """View department objectives related to this institutional objective"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Department Objectives - {self.name}",
            "res_model": "hr.department.objective",
            "view_mode": "kanban,list,form",
            "domain": [("institutional_objective_id", "=", self.id), ("state", "!=", "draft")],
            "context": {
                "default_institutional_objective_id": self.id,
            },
        }

    def action_view_individual_objectives(self):
        """View all individual objectives related to this institutional objective"""
        return {
            "type": "ir.actions.act_window",
            "name": f"Individual Objectives - {self.name}",
            "res_model": "hr.appraisal.goal",
            "view_mode": "kanban,list,form",
            "domain": [("institutional_objective_id", "=", self.id)],
            "context": {
                "default_institutional_objective_id": self.id,
                "search_default_group_by_department": 1,
            },
        }
