# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_contract = fields.Boolean(
        string='Is Contractor/Vendor',
        default=False,
        help='Check this box if this partner is a contractor/vendor '
             'that can be used in contracts'
    )
