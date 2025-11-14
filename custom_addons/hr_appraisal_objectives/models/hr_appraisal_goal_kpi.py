from odoo import models, fields, api
from odoo.exceptions import UserError


class HrAppraisalGoalKPI(models.Model):
    _name = "hr.appraisal.goal.kpi"
    _description = "Appraisal Goal KPI"
    _order = "sequence, id"
    _rec_name = "kpi"

    sequence = fields.Integer("Sequence", default=10)
    appraisal_goal_id = fields.Many2one(
        "hr.appraisal.goal", string="Goal", ondelete="cascade", required=True
    )
    kpi = fields.Char("KPI", required=True)
    description = fields.Html("Description")
    target = fields.Html("Target/Goal")
    measurement_method = fields.Html("Measurement Method")
    weight = fields.Integer("Weight", default=1)

    # --- Project integration ---
    project_id = fields.Many2one(
        "project.project", string="Project", help="Linked project for this KPI"
    )
    task_ids = fields.Many2many(
        "project.task",
        "hr_appraisal_kpi_task_rel",
        "kpi_id",
        "task_id",
        string="Tasks",
        help="Tasks contributing to this KPI",
    )
    progress_method = fields.Selection(
        [
            ("tasks_done_ratio", "Done Tasks Ratio"),
            ("timesheet_ratio", "Timesheet Hours / Planned Hours"),
            ("manual", "Manual Percentage"),
        ],
        default="tasks_done_ratio",
        string="Progress Method",
        help="How to compute KPI progress",
    )
    auto_progress = fields.Boolean(
        string="Auto Progress", default=True, help="Auto compute progress from tasks"
    )
    planned_hours = fields.Float(
        string="Planned Hours",
        help="Expected hours for this KPI (used for timesheet ratio)",
    )
    manual_progress = fields.Float(
        string="Manual Progress %", help="Used when Progress Method is Manual"
    )
    progress_percentage = fields.Float(
        string="Progress %", compute="_compute_progress_percentage", store=True
    )
    employee_id = fields.Many2one(
        related="appraisal_goal_id.employee_id", comodel_name="hr.employee", store=True, readonly=True
    )

    @api.depends("progress_method", "manual_progress", "planned_hours", "task_ids.stage_id", "task_ids.active")
    def _compute_progress_percentage(self):
        for rec in self:
            if rec.progress_method == "manual":
                value = rec.manual_progress or 0.0
                rec.progress_percentage = max(0.0, min(100.0, value))
                continue

            if rec.progress_method == "timesheet_ratio":
                planned = rec.planned_hours or 0.0
                if planned <= 0:
                    rec.progress_percentage = 0.0
                    continue
                aal = rec.env["account.analytic.line"].read_group(
                    domain=[
                        ("task_id", "in", rec.task_ids.ids),
                        ("employee_id", "=", rec.employee_id.id),
                    ],
                    fields=["unit_amount:sum"],
                    groupby=[],
                )
                done_hours = (aal[0]["unit_amount_sum"] if aal else 0.0) or 0.0
                ratio = min(done_hours / planned, 1.0)
                rec.progress_percentage = round(ratio * 100.0, 2)
                continue

            # tasks_done_ratio
            total = len(rec.task_ids)
            if total == 0:
                rec.progress_percentage = 0.0
                continue
            # Consider tasks in a folded (done) stage as completed
            done = len(rec.task_ids.filtered(lambda t: getattr(t.stage_id, "fold", False)))
            rec.progress_percentage = round(100.0 * done / total, 2)

    def write(self, vals):
        # Block edits after approval except safe linkage updates (task_ids)
        blocked_states = {"first_approved", "progress", "self_scored", "scored", "final"}
        allowed_after_approval = {"task_ids"}  # allow linking tasks when starting
        for rec in self:
            parent = rec.appraisal_goal_id
            if parent and parent.state in blocked_states:
                forbidden = set(vals.keys()) - allowed_after_approval
                if forbidden:
                    raise UserError(
                        "You cannot modify KPIs after the objective has been approved."
                    )
        return super().write(vals)

    def unlink(self):
        blocked_states = {"first_approved", "progress", "self_scored", "scored", "final"}
        for rec in self:
            parent = rec.appraisal_goal_id
            if parent and parent.state in blocked_states:
                raise UserError(
                    "You cannot delete KPIs after the objective has been approved."
                )
        return super().unlink()

    # --- Actions ---
    def action_open_task_timesheets(self):
        self.ensure_one()
        action = self.env.ref('hr_timesheet.timesheet_action_task').read()[0]
        task_ids = self.task_ids.ids
        action['domain'] = [('task_id', 'in', task_ids)]
        # keep list view default; pass helpful context
        ctx = dict(self._context or {})
        ctx.update({'is_timesheet': 1})
        action['context'] = ctx
        return action
