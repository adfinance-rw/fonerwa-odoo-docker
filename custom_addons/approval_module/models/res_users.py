# -*- coding: utf-8 -*-

from odoo import models, fields

SIGN_STAMPED_FIELDS = ['sign_signature_stamped']


class ResUsers(models.Model):
    _inherit = 'res.users'

    line_manager_id = fields.Many2one('res.users', string='Line Manager')
    sign_signature_stamped = fields.Binary(
        string="Digital Signature (with Stamp)",
        copy=False,
        groups="base.group_system",
        help="Signature image with embedded company stamp. "
             "Used when signing documents in the Sign app. "
             "The plain signature (without stamp) is used for memo approvals.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + SIGN_STAMPED_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + SIGN_STAMPED_FIELDS

