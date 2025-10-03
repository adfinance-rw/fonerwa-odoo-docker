# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrCommonObjective(models.Model):
    _name = "hr.common.objective"
    _description = "HR Common Objective Template"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    description = fields.Html()
    institutional_objective_id = fields.Many2one(
        "hr.institutional.objective", 
        string="Institutional Objective", 
        required=True
    )
    start_date = fields.Date(related="institutional_objective_id.start_date", store=True)
    end_date = fields.Date(related="institutional_objective_id.end_date", store=True)
    tag_ids = fields.Many2many("hr.appraisal.goal.tag", string="Tags")

    kpi_template_ids = fields.One2many(
        "hr.common.objective.kpi", "common_objective_id", string="KPI Templates", required=True
    )

    target_employee_ids = fields.Many2many(
        "hr.employee", string="Target Employees",
        help="Leave empty to target all employees",
    )

    @api.depends("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date >= record.end_date:
                    raise UserError(_("Start date must be before end date."))
                elif record.start_date < fields.Date.today():
                    raise UserError(_("Start date cannot be in the past."))
                elif record.end_date < record.institutional_objective_id.start_date:
                    raise UserError(_("End date cannot be before the institutional objective's start date."))
                elif record.end_date > record.institutional_objective_id.end_date:
                    raise UserError(_("End date cannot be after the institutional objective's end date."))
            else:
                raise UserError(_("Start and end date are required."))

    def action_publish_objectives(self):
        """Create individual objectives for employees based on this template.
        Copies KPI templates into KPIs of the created goals.
        """
        if not self.kpi_template_ids:
            raise UserError(_("Please add at least one KPI to the common objective."))

        HrGoal = self.env["hr.appraisal.goal"]
        created = 0
        skipped_no_manager = 0
        skipped_no_user = 0

        employees = self.target_employee_ids
        if not employees:
            employees = self.env["hr.employee"].search([("active", "=", True)])

        for obj in self:
            for emp in employees:
                # Determine manager: prefer department manager, fallback to employee's parent
                manager_emp = emp.department_id.manager_id or emp.parent_id
                if not manager_emp:
                    skipped_no_manager += 1
                    continue
                # Ensure employee has a linked user to set as creator
                if not emp.user_id:
                    skipped_no_user += 1
                    continue
                vals = {
                    "name": obj.name,
                    "employee_id": emp.id,
                    "manager_id": manager_emp.id,
                    # Mark as common; do not attach to a specific department objective
                    "is_common": True,
                    "common_origin_id": obj.id,
                    # Keep institutional reference via related fields on dept objective out; show on appraisal
                    "deadline": obj.end_date,
                    "tag_ids": [(6, 0, obj.tag_ids.ids)],
                    # Create as draft to satisfy creator draft rule for base users
                    "state": "draft",
                }
                # Create goal as the employee's user so create_uid is the employee
                goal = HrGoal.with_user(emp.user_id.id).create(vals)
                # Copy KPIs
                for kpi_t in obj.kpi_template_ids:
                    self.env["hr.appraisal.goal.kpi"].with_user(emp.user_id.id).create({
                        "appraisal_goal_id": goal.id,
                        "kpi": kpi_t.kpi,
                        "description": kpi_t.description,
                        "target": kpi_t.target,
                        "measurement_method": kpi_t.measurement_method,
                        "weight": kpi_t.weight,
                    })
                # Transition to submitted and approved using HR context to avoid permission issues
                goal.write({"state": "progress"})
                goal._send_notification("progress")
                created += 1

        msg = _("Published %s objective(s) to employees") % created
        if skipped_no_manager:
            msg += _(". Skipped %s without a manager.") % skipped_no_manager
        if skipped_no_user:
            msg += _(" Skipped %s without a linked user.") % skipped_no_user
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": msg,
                "type": "success" if created else "warning",
                "sticky": False,
            },
        }


class HrCommonObjectiveKPI(models.Model):
    _name = "hr.common.objective.kpi"
    _description = "KPI Template for Common Objective"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    common_objective_id = fields.Many2one(
        "hr.common.objective", required=True, ondelete="cascade"
    )
    kpi = fields.Char(required=True)
    description = fields.Html()
    target = fields.Html()
    measurement_method = fields.Html()
    weight = fields.Float(default=1.0)


