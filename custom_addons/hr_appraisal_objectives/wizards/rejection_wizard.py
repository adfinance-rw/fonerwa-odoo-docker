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
        
        # Mark current user's activities as done (use res_model string to avoid ir.model access)
        goal.activity_ids.filtered(
            lambda a: a.user_id == self.env.user and a.res_model == 'hr.appraisal.goal'
        ).action_feedback(feedback=f"Rejected: {self.reason or 'No reason provided'}")
        
        # Write rejection reason (may be empty) and send back to draft
        goal.write({
            "rejection_reason": self.reason or False,
            "rejected": True,
            "rejection_stage": self.rejection_level,
            "state": "draft",  # Return to draft instead of rejected state
        })
        goal._send_notification("rejected")
        
        # Create activity for employee to revise the objective
        if goal.employee_id and goal.employee_id.user_id:
            rejection_stage_label = dict(self._fields['rejection_level'].selection).get(self.rejection_level, 'Manager')
            goal._create_approval_activity(
                user_id=goal.employee_id.user_id.id,
                summary=f"Objective Rejected: {goal.name}",
                note=f"""<p><strong>Status:</strong> Your objective has been rejected</p>
                      <p><strong>Rejected by:</strong> {rejection_stage_label} ({self.env.user.name})</p>
                      <p><strong>Reason:</strong> {self.reason or 'No specific reason provided'}</p>
                      <p><strong>Action Required:</strong> Please revise your objective and resubmit</p>"""
            )
        
        return {"type": "ir.actions.act_window_close"}


