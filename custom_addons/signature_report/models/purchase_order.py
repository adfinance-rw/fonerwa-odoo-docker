from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_signature_ids = fields.One2many('purchase.order.signature', 'purchase_id', string="Approval Signatures")
    budget_line = fields.Char(string="Budget Line")
    def button_approve(self, force=False):
        res = super(PurchaseOrder, self).button_approve(force=force)

        for order in self:
            # Fetch approved users from studio_approval_entry
            self.env.cr.execute("""
                SELECT e.user_id, p.name as username
                FROM studio_approval_entry e
                JOIN res_users u ON e.user_id = u.id
                JOIN res_partner p ON u.partner_id = p.id
                WHERE e.model = 'purchase.order' AND e.res_id = %s AND e.approved = true
                ORDER BY e.create_date DESC
            """, (order.id,))
            approved_entries = self.env.cr.dictfetchall()

            for entry in approved_entries:
                user_id = entry['user_id']
                user = self.env['res.users'].browse(user_id)

                # Only add signature if user has one and hasn't already signed
                if user.signature_image:
                    already_signed = order.approval_signature_ids.filtered(lambda s: s.user_id.id == user_id)
                    if not already_signed:
                        self.env['purchase.order.signature'].create({
                            'purchase_id': order.id,
                            'user_id': user_id,
                            'signature': user.signature_image,
                        })

        return res
