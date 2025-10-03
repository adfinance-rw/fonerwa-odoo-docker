# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import ValidationError


class HrAppraisalRevertWizard(models.TransientModel):
    _name = "hr.appraisal.revert.wizard"
    _description = "HR Appraisal Revert to Draft Wizard"

    appraisal_id = fields.Many2one("hr.appraisal", string="Appraisal", required=True)
    reason = fields.Text("Reason for Change", required=True, 
                        help="Please provide a reason for reverting this appraisal to draft")

    def action_revert(self):
        self.ensure_one()
        if not self.env.user.has_group('hr_appraisal_objectives.group_hr_appraisal'):
            raise ValidationError("Only HR users can revert appraisals to draft.")
        
        appraisal = self.appraisal_id
        appraisal.write({
            'state': 'new',
            'hr_change_reason': self.reason,
            'hr_change_date': fields.Datetime.now()
        })
        
        # Send notification
        appraisal.message_post(
            subject="Appraisal Reverted to Draft",
            body=f"HR has reverted this appraisal to draft state. Reason: {self.reason}",
            message_type="notification"
        )
        
        return {"type": "ir.actions.act_window_close"}
