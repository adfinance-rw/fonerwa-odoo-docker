from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    valid_from = fields.Date(string="Valid From")
    valid_until = fields.Date(string="Valid Until")