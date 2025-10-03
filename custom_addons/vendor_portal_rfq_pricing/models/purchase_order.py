# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    vendor_prices_submitted = fields.Boolean(
        string='Vendor Prices Submitted',
        default=False,
        help="Indicates if the vendor has submitted their prices"
    )
    vendor_submission_date = fields.Datetime(
        string='Vendor Submission Date',
        help="Date when vendor submitted their prices"
    )
    has_vendor_prices = fields.Boolean(
        string='Has Vendor Prices',
        compute='_compute_has_vendor_prices',
        store=True,
        help="Check if any line has vendor prices"
    )

    @api.depends('order_line.x_supplier_price')
    def _compute_has_vendor_prices(self):
        """Compute if the RFQ has vendor prices submitted"""
        for order in self:
            order.has_vendor_prices = any(
                line.x_supplier_price > 0 for line in order.order_line
            )

    def action_mark_vendor_prices_submitted(self):
        """Mark that vendor has submitted prices and send notification"""
        self.ensure_one()
        if not self.has_vendor_prices:
            raise UserError(_("No vendor prices have been submitted yet."))
        
        self.write({
            'vendor_prices_submitted': True,
            'vendor_submission_date': fields.Datetime.now()
        })
        
        # Send notification to purchasing team
        self._notify_purchasing_team()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Your prices have been submitted successfully!'),
                'sticky': False,
                'type': 'success'
            }
        }

    def action_transfer_vendor_prices(self):
        """Open wizard to transfer vendor prices to official prices"""
        self.ensure_one()
        return {
            'name': _('Transfer Vendor Prices'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.price.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
                'purchase_order_id': self.id  # Add this for the wizard to find
            }
        }

    def _notify_purchasing_team(self):
        """Send notification to purchasing team when vendor submits prices"""
        template = self.env.ref(
            'vendor_portal_rfq_pricing.email_template_vendor_prices_submitted',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)


    
    def action_rfq_send(self):
        """Override to use our enhanced email template for RFQs"""
        result = super().action_rfq_send()
        
        # If we're in draft or sent state, use our enhanced template
        if self.state in ['draft', 'sent']:
            enhanced_template = self.env.ref('vendor_portal_rfq_pricing.email_template_rfq_with_pricing_link', False)
            if enhanced_template and isinstance(result, dict) and result.get('context'):
                result['context']['default_template_id'] = enhanced_template.id
        
        return result


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    x_supplier_price = fields.Float(
        string='Supplier Price',
        digits='Product Price',
        help="Price submitted by the supplier through the portal"
    )
    x_supplier_price_display = fields.Float(
        string='Supplier Price',
        compute='_compute_x_supplier_price_display',
        help="Display price - returns zero if after deadline"
    )
    supplier_price_submitted = fields.Boolean(
        string='Price Submitted',
        default=False,
        help="Indicates if supplier has submitted a price for this line"
    )
    price_difference = fields.Float(
        string='Price Difference',
        compute='_compute_price_difference',
        digits='Product Price',
        help="Difference between supplier price and current unit price"
    )
    price_difference_percent = fields.Float(
        string='Price Difference %',
        compute='_compute_price_difference',
        help="Percentage difference between supplier price and current unit price"
    )
    price_difference_display = fields.Float(
        string='Price Difference',
        compute='_compute_price_difference_display',
        digits='Product Price',
        help="Display price difference - returns zero if after deadline"
    )
    price_difference_percent_display = fields.Float(
        string='Price Difference %',
        compute='_compute_price_difference_display',
        help="Display price difference percentage - returns zero if after deadline"
    )

    @api.depends('x_supplier_price', 'order_id.date_order')
    def _compute_x_supplier_price_display(self):
        """Compute display supplier price - returns zero if after deadline"""
        now = fields.Datetime.now()
        for line in self:
            if line.order_id.date_order and now <= line.order_id.date_order:
                # After deadline - return zero
                line.x_supplier_price_display = 0.0
            else:
                # Before deadline or no date_order - return actual price
                line.x_supplier_price_display = line.x_supplier_price

    @api.depends('price_difference', 'price_difference_percent', 'order_id.date_order')
    def _compute_price_difference_display(self):
        """Compute display price difference - returns zero if after deadline"""
        now = fields.Datetime.now()
        for line in self:
            if line.order_id.date_order and now <= line.order_id.date_order:
                # After deadline - return zero
                line.price_difference_display = 0.0
                line.price_difference_percent_display = 0.0
            else:
                # Before deadline or no date_order - return actual values
                line.price_difference_display = line.price_difference
                line.price_difference_percent_display = line.price_difference_percent

    @api.depends('x_supplier_price', 'price_unit', 'order_id.date_order')
    def _compute_price_difference(self):
        """Compute price difference between supplier price and unit price"""
        now = fields.Datetime.now()
        for line in self:
            # Check if before deadline - show zero if before deadline
            if line.order_id.date_order and now <= line.order_id.date_order:
                # Before deadline - return zero
                line.price_difference = 0.0
                line.price_difference_percent = 0.0
            else:
                # After deadline or no date_order - compute actual values
                if line.x_supplier_price and line.price_unit:
                    line.price_difference = line.x_supplier_price - line.price_unit
                    if line.price_unit != 0:
                        line.price_difference_percent = (
                            (line.x_supplier_price - line.price_unit) / line.price_unit
                        ) * 100
                    else:
                        line.price_difference_percent = 0.0
                else:
                    line.price_difference = 0.0
                    line.price_difference_percent = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set default values"""
        lines = super().create(vals_list)
        for line in lines:
            if line.x_supplier_price > 0:
                line.supplier_price_submitted = True
        return lines

    def write(self, vals):
        """Override write to track price submissions"""
        result = super().write(vals)
        if 'x_supplier_price' in vals:
            for line in self:
                if line.x_supplier_price > 0:
                    line.supplier_price_submitted = True
                else:
                    line.supplier_price_submitted = False
        return result

    def action_accept_supplier_price(self):
        """Accept supplier price and update unit price"""
        self.ensure_one()
        if not self.x_supplier_price:
            raise UserError(_("No supplier price to accept."))
        
        self.write({
            'price_unit': self.x_supplier_price,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Supplier price has been accepted and applied.'),
                'sticky': False,
                'type': 'success'
            }
        }

    def action_reject_supplier_price(self):
        """Reject supplier price"""
        self.ensure_one()
        self.x_supplier_price = 0.0
        self.supplier_price_submitted = False
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Supplier price has been rejected.'),
                'sticky': False,
                'type': 'info'
            }
        } 