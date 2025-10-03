# -*- coding: utf-8 -*-

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    line_manager_id = fields.Many2one('res.users', string='Line Manager')

