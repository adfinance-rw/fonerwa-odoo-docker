# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    cfo_id = fields.Many2one('res.users', string='CFO')
    ceo_id = fields.Many2one('res.users', string='CEO')

