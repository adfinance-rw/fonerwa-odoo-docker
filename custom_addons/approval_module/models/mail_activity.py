# -*- coding: utf-8 -*-

from odoo import models, api


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.model_create_multi
    def create(self, vals_list):
        """Prevent auto-follow when scheduling activities on approval requests."""
        vals_approval = [vals for vals in vals_list if vals.get('res_model') == 'approval.request']
        vals_other = [vals for vals in vals_list if vals.get('res_model') != 'approval.request']

        records = self.browse()
        if vals_other:
            records |= super().create(vals_other)
        if vals_approval:
            records |= super(MailActivity, self.with_context(skip_activity_auto_follow=True)).create(vals_approval)
        return records
