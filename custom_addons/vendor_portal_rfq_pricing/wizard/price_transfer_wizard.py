# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class VendorPriceTransferWizard(models.TransientModel):
    _name = 'vendor.price.transfer.wizard'
    _description = 'Wizard to Transfer Vendor Prices to Official Prices'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        readonly=True
    )
    line_ids = fields.One2many(
        'vendor.price.transfer.wizard.line',
        'wizard_id',
        string='Order Lines'
    )
    transfer_all = fields.Boolean(
        string='Transfer All Prices',
        default=True,
        help="If checked, all vendor prices will be transferred. Otherwise, only selected lines."
    )
    notes = fields.Text(
        string='Transfer Notes',
        help="Additional notes for this price transfer"
    )

    @api.model
    def default_get(self, fields_list):
        """Populate wizard with order lines that have vendor prices"""
        res = super().default_get(fields_list)
        
        # Get purchase_order_id from context (try both variations)
        purchase_order_id = (
            self.env.context.get('purchase_order_id') or 
            self.env.context.get('default_purchase_order_id') or
            self.env.context.get('active_id')
        )
        
        if purchase_order_id:
            purchase_order = self.env['purchase.order'].browse(purchase_order_id)
            res['purchase_order_id'] = purchase_order.id
            
            # Create wizard lines for all order lines with vendor prices
            line_vals = []
            for line in purchase_order.order_line:
                # Check if line has vendor price (x_supplier_price > 0)
                if hasattr(line, 'x_supplier_price') and line.x_supplier_price > 0:
                    line_vals.append((0, 0, {
                        'purchase_line_id': line.id,
                        'current_price': line.price_unit,
                        'vendor_price': line.x_supplier_price,
                        'transfer': True,  # Default to transfer
                        'notes': ''
                    }))
            
            res['line_ids'] = line_vals
            
            # Log debug info
            _logger.info(f"Price Transfer Wizard: Found {len(line_vals)} lines with vendor prices for PO {purchase_order.name}")
            
        return res

    def action_reload_wizard_lines(self):
        """Reload wizard lines from the purchase order"""
        if self.purchase_order_id:
            self.line_ids = [(5, 0, 0)]  # Clear existing lines
            line_vals = []
            for line in self.purchase_order_id.order_line:
                if hasattr(line, 'x_supplier_price') and line.x_supplier_price > 0:
                    line_vals.append((0, 0, {
                        'purchase_line_id': line.id,
                        'current_price': line.price_unit,
                        'vendor_price': line.x_supplier_price,
                        'transfer': True,
                        'notes': ''
                    }))
            self.line_ids = line_vals
            _logger.info(f"Reloaded {len(line_vals)} lines with vendor prices")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Lines Reloaded'),
                    'message': _(f'Found {len(line_vals)} products with vendor prices.'),
                    'sticky': False,
                    'type': 'success' if line_vals else 'warning'
                }
            }

    def action_debug_order_lines(self):
        """Debug method to check what's in the purchase order lines"""
        if self.purchase_order_id:
            debug_info = []
            for line in self.purchase_order_id.order_line:
                has_x_supplier_price = hasattr(line, 'x_supplier_price')
                x_supplier_price_value = getattr(line, 'x_supplier_price', 'Field not found') if has_x_supplier_price else 'Field not found'
                debug_info.append(f"Product: {line.product_id.name}, Has x_supplier_price: {has_x_supplier_price}, Value: {x_supplier_price_value}")
            
            _logger.info(f"Debug - Purchase Order {self.purchase_order_id.name} lines:\n" + "\n".join(debug_info))
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Debug Info'),
                    'message': _(f"Debug info logged. Found {len(self.purchase_order_id.order_line)} order lines. Check server logs for details."),
                    'sticky': True,
                    'type': 'info'
                }
            }

    def action_transfer_prices(self):
        """Transfer selected vendor prices to official prices"""
        self.ensure_one()
        
        if not self.line_ids:
            # Try to reload the lines
            self.action_reload_wizard_lines()
            if not self.line_ids:
                raise UserError(_(
                    "No lines available for price transfer. "
                    "Please ensure that vendors have submitted prices for some products."
                ))
        
        lines_to_transfer = self.line_ids.filtered('transfer') if not self.transfer_all else self.line_ids
        
        if not lines_to_transfer:
            raise UserError(_("Please select at least one line to transfer."))
        
        transferred_count = 0
        total_savings = 0.0
        
        for wizard_line in lines_to_transfer:
            purchase_line = wizard_line.purchase_line_id
            old_price = purchase_line.price_unit
            new_price = wizard_line.vendor_price
            
            # Update the purchase line price
            purchase_line.write({
                'price_unit': new_price
            })
            
            # Calculate savings
            line_savings = (old_price - new_price) * purchase_line.product_qty
            total_savings += line_savings
            transferred_count += 1
            
            # Log the price change
            purchase_line.order_id.message_post(
                body=_(
                    "Price updated for %s: %s → %s (Difference: %s per unit)"
                ) % (
                    purchase_line.product_id.name,
                    old_price,
                    new_price,
                    new_price - old_price
                ),
                message_type='notification'
            )
        
        # Update the purchase order status
        self.purchase_order_id.write({
            'vendor_prices_submitted': True
        })
        
        # Log the overall transfer
        self.purchase_order_id.message_post(
            body=_(
                "Vendor prices transferred: %d lines updated. Total savings: %s %s. Notes: %s"
            ) % (
                transferred_count,
                total_savings,
                self.purchase_order_id.currency_id.name,
                self.notes or 'None'
            ),
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    'Successfully transferred %d vendor prices. Total savings: %s %s'
                ) % (
                    transferred_count,
                    total_savings,
                    self.purchase_order_id.currency_id.symbol
                ),
                'sticky': False,
                'type': 'success'
            }
        }

    def action_preview_changes(self):
        """Preview the changes before applying them"""
        self.ensure_one()
        lines_to_transfer = self.line_ids.filtered('transfer') if not self.transfer_all else self.line_ids
        
        preview_data = []
        total_savings = 0.0
        
        for wizard_line in lines_to_transfer:
            purchase_line = wizard_line.purchase_line_id
            old_price = purchase_line.price_unit
            new_price = wizard_line.vendor_price
            line_savings = (old_price - new_price) * purchase_line.product_qty
            total_savings += line_savings
            
            preview_data.append({
                'product': purchase_line.product_id.name,
                'qty': purchase_line.product_qty,
                'old_price': old_price,
                'new_price': new_price,
                'difference': new_price - old_price,
                'line_savings': line_savings
            })
        
        return {
            'name': _('Price Transfer Preview'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.price.transfer.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_preview_data': preview_data,
                'default_total_savings': total_savings,
                'default_wizard_id': self.id
            }
        }


class VendorPriceTransferWizardLine(models.TransientModel):
    _name = 'vendor.price.transfer.wizard.line'
    _description = 'Vendor Price Transfer Wizard Line'

    wizard_id = fields.Many2one(
        'vendor.price.transfer.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    purchase_line_id = fields.Many2one(
        'purchase.order.line',
        string='Purchase Line',
        required=True,
        readonly=True
    )
    product_id = fields.Many2one(
        'product.product',
        related='purchase_line_id.product_id',
        string='Product',
        readonly=True
    )
    product_qty = fields.Float(
        related='purchase_line_id.product_qty',
        string='Quantity',
        readonly=True
    )
    current_price = fields.Float(
        string='Current Price',
        digits='Product Price',
        readonly=True
    )
    vendor_price = fields.Float(
        string='Vendor Price',
        digits='Product Price',
        readonly=True
    )
    price_difference = fields.Float(
        string='Difference',
        compute='_compute_price_difference',
        digits='Product Price'
    )
    price_difference_percent = fields.Float(
        string='Difference %',
        compute='_compute_price_difference'
    )
    line_savings = fields.Float(
        string='Line Savings',
        compute='_compute_line_savings',
        digits='Product Price'
    )
    transfer = fields.Boolean(
        string='Transfer',
        default=True,
        help="Check to transfer this vendor price to the official price"
    )
    notes = fields.Char(
        string='Notes',
        help="Notes for this specific line transfer"
    )

    @api.depends('current_price', 'vendor_price')
    def _compute_price_difference(self):
        """Compute price difference"""
        for line in self:
            line.price_difference = line.vendor_price - line.current_price
            if line.current_price != 0:
                line.price_difference_percent = (
                    (line.vendor_price - line.current_price) / line.current_price
                ) * 100
            else:
                line.price_difference_percent = 0.0

    @api.depends('price_difference', 'product_qty')
    def _compute_line_savings(self):
        """Compute savings for this line"""
        for line in self:
            line.line_savings = -line.price_difference * line.product_qty


class VendorPriceTransferPreview(models.TransientModel):
    _name = 'vendor.price.transfer.preview'
    _description = 'Preview of Price Transfer Changes'

    preview_data = fields.Text(
        string='Preview Data',
        readonly=True
    )
    total_savings = fields.Float(
        string='Total Savings',
        readonly=True,
        digits='Product Price'
    )
    wizard_id = fields.Many2one(
        'vendor.price.transfer.wizard',
        string='Transfer Wizard',
        readonly=True
    )

    def action_confirm_transfer(self):
        """Confirm and execute the transfer"""
        if self.wizard_id:
            return self.wizard_id.action_transfer_prices()
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cancel the transfer"""
        return {'type': 'ir.actions.act_window_close'} 