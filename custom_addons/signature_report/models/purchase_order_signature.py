from odoo import models, fields

class PurchaseOrderSignature(models.Model):
    _name = 'purchase.order.signature'
    _description = 'Purchase Order Approval Signature'

    purchase_id = fields.Many2one('purchase.order', string="Purchase Order", required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string="User", required=True)
    signature = fields.Binary(string="Signature", required=True)
