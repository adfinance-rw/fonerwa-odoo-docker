# -*- coding: utf-8 -*-
from odoo import models, fields


class HrAppraisalGoalRejectionWizard(models.TransientModel):
    _name = "hr.appraisal.goal.rejection.wizard"
    _description = "Rejection Wizard for Individual Objective"

    goal_id = fields.Many2one("hr.appraisal.goal", string="Objective", required=True)
    rejection_level = fields.Selection(
        [("first", "First Approval"), ("second", "Second Approval")],
        string="Stage",
        required=True,
    )
    reason = fields.Text("Reason (optional)")

    def action_reject(self):
        self.ensure_one()
        goal = self.goal_id
        # Write rejection reason (may be empty) and send back to draft
        goal.write({
            "rejection_reason": self.reason or False,
            "rejected": True,
            "rejection_stage": self.rejection_level,
            "state": "draft",  # Return to draft instead of rejected state
        })
        goal._send_notification("rejected")
        return {"type": "ir.actions.act_window_close"}


