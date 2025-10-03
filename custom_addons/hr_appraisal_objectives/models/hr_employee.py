from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    kpi_task_ids = fields.Many2many(
        "project.task",
        string="KPI Tasks",
        compute="_compute_kpi_task_ids",
        store=False,
    )

    def _compute_kpi_task_ids(self):
        for emp in self:
            kpis = self.env["hr.appraisal.goal.kpi"].search([
                ("appraisal_goal_id.employee_id", "=", emp.id)
            ])
            emp.kpi_task_ids = kpis.mapped("task_ids")


