# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrAppraisalGoalBatchRejectionWizard(models.TransientModel):
    _name = "hr.appraisal.goal.batch.rejection.wizard"
    _description = "Batch Rejection Wizard for Employee Objectives"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, readonly=True)
    objective_ids = fields.Many2many(
        "hr.appraisal.goal",
        string="Objectives to Reject",
        domain="[('employee_id', '=', employee_id), ('state', 'in', ['submitted', 'first_approved'])]",
        required=True,
    )
    rejection_reason = fields.Text("Rejection Reason", required=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Pre-fill with all pending objectives if called from dashboard
        if 'objective_ids' in fields_list and res.get('employee_id'):
            pending = self.env['hr.appraisal.goal'].search([
                ('employee_id', '=', res['employee_id']),
                ('state', 'in', ['submitted', 'first_approved'])
            ])
            res['objective_ids'] = [(6, 0, pending.ids)]
        return res

    def action_reject_selected(self):
        """Reject selected objectives"""
        self.ensure_one()
        
        rejected_count = 0
        for objective in self.objective_ids:
            # Determine rejection level based on current state
            rejection_level = 'first' if objective.state == 'submitted' else 'second'
            
            # Mark current user's activities as done (use res_model string to avoid ir.model access)
            objective.activity_ids.filtered(
                lambda a: a.user_id == self.env.user and a.res_model == 'hr.appraisal.goal'
            ).action_feedback(feedback=f"Rejected: {self.rejection_reason}")
            
            # Write rejection reason and return to draft
            objective.write({
                "rejection_reason": self.rejection_reason,
                "rejected": True,
                "rejection_stage": rejection_level,
                "state": "draft",
            })
            objective._send_notification("rejected")
            
            # Create activity for employee
            if objective.employee_id and objective.employee_id.user_id:
                rejection_stage_label = "Line Manager" if rejection_level == 'first' else "HR Manager"
                objective._create_approval_activity(
                    user_id=objective.employee_id.user_id.id,
                    summary=f"Objective Rejected: {objective.name}",
                    note=f"""<p><strong>Status:</strong> Your objective has been rejected</p>
                          <p><strong>Rejected by:</strong> {rejection_stage_label} ({self.env.user.name})</p>
                          <p><strong>Reason:</strong> {self.rejection_reason}</p>
                          <p><strong>Action Required:</strong> Please revise your objective and resubmit</p>"""
                )
            
            rejected_count += 1
        
        # Show confirmation message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"✓ Rejected {rejected_count} objective(s) for {self.employee_id.name}",
                'type': 'success',
                'sticky': False,
            },
        }

