# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class AccountTax(models.Model):
    _inherit = 'account.tax'

    code = fields.Char(string='Code')
    sort_order = fields.Integer(string='Sort Order')

