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
    fiscal_year_id = fields.Many2one(
        "hr.fiscal.year",
        string="Fiscal Year",
        required=True,
        default=lambda self: self.env['hr.fiscal.year'].get_current_fiscal_year(),
        help="Fiscal year for this common objective"
    )
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date(required=True)
    tag_ids = fields.Many2many("hr.appraisal.goal.tag", string="Tags")
    
    @api.onchange('fiscal_year_id')
    def _onchange_fiscal_year(self):
        """Auto-fill end date from fiscal year"""
        if self.fiscal_year_id:
            # Only auto-fill end date, start date stays as today
            self.end_date = self.fiscal_year_id.date_to

    kpi_template_ids = fields.One2many(
        "hr.common.objective.kpi", "common_objective_id", string="KPI Templates", required=True
    )

    target_employee_ids = fields.Many2many(
        "hr.employee", string="Target Employees",
        help="Leave empty to target all employees",
    )

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date >= record.end_date:
                    raise UserError(_("Start date must be before end date."))
    
    @api.constrains("start_date", "end_date", "fiscal_year_id")
    def _check_dates_within_fiscal_year(self):
        """Ensure dates are within the fiscal year"""
        for record in self:
            if record.fiscal_year_id and record.start_date and record.end_date:
                fy_start = record.fiscal_year_id.date_from
                fy_end = record.fiscal_year_id.date_to
                
                if fy_start and record.start_date < fy_start:
                    raise UserError(_("Start date cannot be before the fiscal year's start date (%s).") % fy_start)
                    
                if fy_end and record.end_date > fy_end:
                    raise UserError(_("End date cannot be after the fiscal year's end date (%s).") % fy_end)

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
    weight = fields.Integer(default=1)


