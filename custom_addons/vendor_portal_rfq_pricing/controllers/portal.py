# -*- coding: utf-8 -*-

import json
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http, _, fields
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.purchase.controllers.portal import CustomerPortal as PurchaseCustomerPortal
from odoo.tools import float_round


class VendorRFQPortal(PurchaseCustomerPortal):
    """Extended portal controller for vendor RFQ pricing"""

    def _check_vendor_access(self, order_sudo, access_token=None):
        """Check if current user/token has access to this RFQ"""
        # Check if user is logged in and is the vendor
        if request.env.user and not request.env.user._is_public():
            current_partner = request.env.user.partner_id
            if current_partner and order_sudo.partner_id == current_partner:
                return True
        
        # Check if access token is provided and valid
        if access_token:
            # The _document_check_access already validated the token
            return True
            
        return False

    def _prepare_home_portal_values(self, counters):
        """Add vendor RFQ counters to portal home"""
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        if 'rfq_pricing_count' in counters:
            # Count RFQs where current user is the vendor and can input prices
            rfq_count = request.env['purchase.order'].search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['draft', 'sent']),
            ])
            values['rfq_pricing_count'] = rfq_count
            
        return values

    @http.route(['/my/purchase/<int:order_id>/pricing'], type='http', auth="public", website=True)
    def portal_order_pricing(self, order_id, access_token=None, **kw):
        """Display RFQ pricing form for vendors"""
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Check vendor access
        if not self._check_vendor_access(order_sudo, access_token):
            return request.redirect(f'/web/login?redirect=/my/purchase/{order_id}/pricing')
            
        # Check if RFQ is in correct state for pricing
        if order_sudo.state not in ['draft', 'sent']:
            raise Forbidden(_("This RFQ is no longer available for pricing."))

        values = {
            'order': order_sudo,
            'token': access_token,
            'return_url': '/my/purchase/%s' % order_id,
            'bootstrap_formatting': True,
            'partner_id': order_sudo.partner_id.id,
            'report_type': 'html',
        }
        
        return request.render('vendor_portal_rfq_pricing.portal_rfq_pricing_form', values)

    @http.route(['/my/purchase/<int:order_id>/pricing/submit'], type='http', auth="public", 
                website=True, methods=['POST'], csrf=True)
    def portal_order_pricing_submit(self, order_id, access_token=None, **post):
        """Handle vendor price submission"""
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Check vendor access
        if not self._check_vendor_access(order_sudo, access_token):
            raise Forbidden(_("You are not authorized to access this RFQ."))
            
        if order_sudo.state not in ['draft', 'sent']:
            raise Forbidden(_("This RFQ is no longer available for pricing."))

        # Process price submissions
        success_count = 0
        error_messages = []
        
        for line in order_sudo.order_line:
            price_key = f'supplier_price_{line.id}'
            if price_key in post:
                try:
                    supplier_price = float(post[price_key] or 0.0)
                    if supplier_price >= 0:  # Allow zero prices
                        line.sudo().write({
                            'x_supplier_price': supplier_price,
                            'supplier_price_submitted': supplier_price > 0
                        })
                        success_count += 1
                    else:
                        error_messages.append(
                            _("Invalid price for %s: Price cannot be negative.") % line.product_id.name
                        )
                except (ValueError, TypeError):
                    error_messages.append(
                        _("Invalid price format for %s.") % line.product_id.name
                    )

        # Update order status if any prices were submitted
        if success_count > 0:
            order_sudo.sudo().write({
                'vendor_prices_submitted': True,
                'vendor_submission_date': fields.Datetime.now()
            })
            
            # Send notification to purchasing team
            order_sudo.sudo()._notify_purchasing_team()
            
            # Log activity
            order_sudo.sudo().message_post(
                body=_("Vendor has submitted prices for %d line(s).") % success_count,
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )

        # Prepare response message
        if error_messages:
            message = _("Prices submitted with some errors:\n") + "\n".join(error_messages)
            message_type = 'warning'
        elif success_count > 0:
            message = _("Prices submitted successfully! The purchasing team has been notified.")
            message_type = 'success'
        else:
            message = _("No prices were submitted.")
            message_type = 'info'

        # Redirect with message
        return request.redirect(
            f'/my/purchase/{order_id}?access_token={access_token}&message={message}&message_type={message_type}'
        )

    @http.route(['/my/purchase/<int:order_id>/pricing/update'], type='json', auth="public", 
                website=True, methods=['POST'], csrf=True)
    def portal_order_pricing_update_ajax(self, order_id, line_id, price, access_token=None, **kw):
        """AJAX handler for real-time price updates"""
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token)
        except (AccessError, MissingError):
            return {'error': _("Access denied")}

        # Check vendor access
        if not self._check_vendor_access(order_sudo, access_token):
            return {'error': _("You are not authorized to access this RFQ.")}
            
        if order_sudo.state not in ['draft', 'sent']:
            return {'error': _("This RFQ is no longer available for pricing.")}

        # Find the line
        line = order_sudo.order_line.filtered(lambda l: l.id == int(line_id))
        if not line:
            return {'error': _("Order line not found.")}

        try:
            supplier_price = float(price or 0.0)
            if supplier_price < 0:
                return {'error': _("Price cannot be negative.")}
                
            # Update the line
            line.sudo().write({
                'x_supplier_price': supplier_price,
                'supplier_price_submitted': supplier_price > 0
            })
            
            # Calculate totals
            subtotal = supplier_price * line.product_qty
            
            return {
                'success': True,
                'subtotal': subtotal,
                'formatted_price': f"{supplier_price:.2f}",
                'formatted_subtotal': f"{subtotal:.2f}",
                'currency_symbol': order_sudo.currency_id.symbol or '$'
            }
            
        except (ValueError, TypeError):
            return {'error': _("Invalid price format.")}

    @http.route(['/my/rfq/pricing'], type='http', auth="user", website=True)
    def portal_my_rfq_pricing(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        """List all RFQs available for pricing by the current vendor"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        # Domain for RFQs where user is vendor and can input prices
        domain = [
            ('partner_id', '=', partner.id),
            ('state', 'in', ['draft', 'sent']),
        ]
        
        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }
        
        # Default sort
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Date filtering
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # Count total RFQs
        rfq_count = request.env['purchase.order'].search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/rfq/pricing",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=rfq_count,
            page=page,
            step=self._items_per_page
        )
        
        # Get RFQs
        rfqs = request.env['purchase.order'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'date': date_begin,
            'rfqs': rfqs,
            'page_name': 'rfq_pricing',
            'pager': pager,
            'default_url': '/my/rfq/pricing',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        
        return request.render("vendor_portal_rfq_pricing.portal_my_rfq_pricing", values)


class VendorPortalMenu(CustomerPortal):
    """Add vendor pricing menu to portal"""

    def _prepare_home_portal_values(self, counters):
        """Add RFQ pricing count to portal home"""
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        if 'rfq_pricing_count' in counters:
            rfq_count = request.env['purchase.order'].search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['draft', 'sent']),
            ])
            values['rfq_pricing_count'] = rfq_count
            
        return values 