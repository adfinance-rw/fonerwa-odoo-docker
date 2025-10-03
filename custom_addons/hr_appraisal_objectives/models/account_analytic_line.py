from odoo import models, fields


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    allowed_kpi_task_ids = fields.Many2many(
        "project.task",
        string="Allowed KPI Tasks",
        compute="_compute_allowed_kpi_task_ids",
        store=False,
    )

    def _compute_allowed_kpi_task_ids(self):
        for line in self:
            employee = self.env.user.employee_id
            tasks = self.env["project.task"]
            if employee:
                kpi_tasks = self.env["hr.appraisal.goal.kpi"].search([
                    ("appraisal_goal_id.employee_id", "=", employee.id)
                ]).mapped("task_ids").ids
                if kpi_tasks:
                    tasks = self.env["project.task"].search([
                        ("id", "in", kpi_tasks),
                        ("user_ids", "in", self.env.user.id),
                    ])
                else:
                    tasks = self.env["project.task"].search([
                        ("user_ids", "in", self.env.user.id)
                    ])
            line.allowed_kpi_task_ids = tasks


