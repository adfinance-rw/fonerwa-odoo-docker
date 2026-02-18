# -*- coding: utf-8 -*-

from odoo import models, fields


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    document_requirement = fields.Selection([
        ('no', 'No Document Required'),
        ('always', 'Always Required'),
        ('conditional', 'Required After X Days'),
    ], string='Document Requirement', default='no',
        help='Configure when a supporting document is mandatory for this leave type.')

    document_required_days = fields.Integer(
        string='Document Required After (Days)',
        default=0,
        help='Number of days after which a supporting document becomes mandatory. '
             'Only used when Document Requirement is set to "Required After X Days".')
