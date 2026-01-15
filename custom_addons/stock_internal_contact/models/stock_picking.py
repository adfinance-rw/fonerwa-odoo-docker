from odoo import models, api

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.onchange('picking_type_id')
    def _set_internal_contact(self):
        for record in self:
            # Only apply for Internal Transfers
            if record.picking_type_id and record.picking_type_id.code == 'internal':
                # Only set if draft and partner is empty
                if record.state == 'draft' and not record.partner_id:
                    record.partner_id = self.env.user.partner_id
