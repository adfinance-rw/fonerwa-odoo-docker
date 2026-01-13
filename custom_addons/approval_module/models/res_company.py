# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    cfo_id = fields.Many2one('res.users', string='CFO')
    senior_approver_id = fields.Many2one('res.users', string='CEO office', 
                                         help='Pre-authorization approval before CEO')
    ceo_id = fields.Many2one('res.users', string='CEO')
    default_approval_category_id = fields.Many2one(
        'approval.category',
        string='Default Approval Category',
        help='The approval category that will be pre-selected when clicking "New Request" button'
    )
