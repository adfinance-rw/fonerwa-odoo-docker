# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import locale
import json


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    tender_award_recommendation = fields.Text(
        string='Tender Award Recommendation',
        help="Formal recommendation and justification for the tender award decision"
    )
    tender_award_generated = fields.Boolean(
        string='Tender Award Report Generated',
        default=False,
        help="Indicates if the tender award report has been generated"
    )
    tender_award_date = fields.Datetime(
        string='Tender Award Report Date',
        help="Date when the tender award report was generated"
    )
    tender_description = fields.Text(
        string='Tender Description',
        help="Description of the tender/procurement project"
    )
    legal_reference = fields.Text(
        string='Legal Reference',
        default="Ministerial Order N° 001/23/10/TC of 10/10/2023 establishing regulations on public procurement in Article 74",
        help="Legal reference for the tender award process"
    )
    prepared_by = fields.Many2one(
        'res.users',
        string='Prepared By',
        default=lambda self: self.env.user,
        help="Person who prepared the tender award report"
    )
    first_approval = fields.Many2one(
        'res.users',
        string='First Approval',
        help="Person responsible for first level approval"
    )
    final_approval = fields.Many2one(
        'res.users',
        string='Final Approval',
        help="Person responsible for final approval"
    )
    
    # Fix for purchase_requisition_stock module compatibility
    on_time_rate_perc = fields.Float(
        string="On Time Rate",
        default=0.0,
        help="On time delivery rate"
    )

    @api.depends('purchase_group_id', 'purchase_group_id.order_ids')
    def _compute_tender_participants(self):
        """Compute all participants in the tender group"""
        for order in self:
            if order.purchase_group_id:
                # Get all POs in the same tender group
                # Include also cancelled tenders (state == 'cancel')
                tender_pos = order.purchase_group_id.order_ids.filtered(
                    lambda po: po.state in ['draft', 'sent', 'to approve', 'purchase', 'cancel']
                )
                order.tender_participants = tender_pos
            else:
                order.tender_participants = self.env['purchase.order']

    tender_participants = fields.Many2many(
        'purchase.order',
        compute='_compute_tender_participants',
        string='Tender Participants',
        help="All purchase orders participating in this tender"
    )

    @api.depends('tender_participants')
    def _compute_tender_summary(self):
        """Compute tender summary data for the report"""
        for order in self:
            if order.tender_participants:
                # Calculate total amounts for each participant
                participants_data = []
                for po in order.tender_participants:
                    total_amount = sum(po.order_line.mapped('price_subtotal'))
                    participants_data.append({
                        'po_id': po.id,
                        'vendor_id': po.partner_id.id,
                        'total_amount': total_amount,
                        'is_selected': po.id == order.id,
                        'line_count': len(po.order_line),
                        'submission_date': po.date_order.strftime('%Y-%m-%d') if po.date_order else None,
                    })
                
                # Sort by total amount (ascending - lowest first)
                participants_data.sort(key=lambda x: x['total_amount'])
                order.tender_participants_data = json.dumps(participants_data)
                order.tender_participants_count = len(participants_data)
            else:
                order.tender_participants_data = json.dumps([])
                order.tender_participants_count = 0

    tender_participants_data = fields.Text(
        compute='_compute_tender_summary',
        string='Tender Participants Data',
        help="Structured data about tender participants for the report",
        store=False
    )
    tender_participants_count = fields.Integer(
        compute='_compute_tender_summary',
        string='Number of Participants',
        help="Number of participants in the tender"
    )

    def action_generate_tender_award_report(self):
        """Generate the tender award report"""
        self.ensure_one()
        
        if not self.purchase_group_id:
            raise UserError(_("This purchase order is not part of a tender process. Only purchase orders with alternatives can generate tender award reports."))
        
        if not self.tender_participants:
            raise UserError(_("No tender participants found. Please ensure there are alternative purchase orders in the tender group."))
        
        # Mark as generated
        self.write({
            'tender_award_generated': True,
            'tender_award_date': fields.Datetime.now()
        })
        
        # Generate the report using the report action
        report_action = self.env.ref('tender_award_report.action_tender_award_report')
        return report_action.report_action(self.id)

    def _get_amount_in_words(self, amount):
        """Convert amount to words in English"""
        try:
            # Set locale to English
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
            
            # Convert to integer (assuming Rwandan Francs)
            amount_int = int(amount)
            
            # Simple conversion for common amounts
            if amount_int == 0:
                return "Zero Rwandan Francs"
            
            # For now, return a simple format
            # In a production environment, you might want to use a proper number-to-words library
            return f"{amount_int:,} Rwandan Francs"
        except:
            return f"{amount:,.0f} Rwandan Francs"

    def _get_formatted_date(self):
        """Get formatted date for the report"""
        if self.tender_award_date:
            return self.tender_award_date.strftime('%d/%m/%Y')
        else:
            return fields.Date.today().strftime('%d/%m/%Y')

    def _get_tender_participants_for_report(self):
        """Get formatted data for tender participants in the report"""
        # If no purchase group, return empty list
        if not self.purchase_group_id:
            return []
        
        # Get all POs in the same tender group directly
        tender_pos = self.purchase_group_id.order_ids.filtered(
            lambda po: po.state in ['draft', 'sent', 'to approve', 'purchase']
        )
        
        if not tender_pos:
            return []
        
        participants = []
        for i, po in enumerate(tender_pos, 1):
            # Calculate total amount for this PO
            total_amount = sum(po.order_line.mapped('price_subtotal'))
            
            # Check if vendor has submitted qualifications (CV, degree, etc.)
            qualifications = []
            if hasattr(po.partner_id, 'x_cv_submitted') and po.partner_id.x_cv_submitted:
                qualifications.append("CV submitted")
            if hasattr(po.partner_id, 'x_degree_submitted') and po.partner_id.x_degree_submitted:
                qualifications.append("Degree submitted")
            
            qualification_text = ", ".join(qualifications) if qualifications else "No supporting documents submitted"
            
            participants.append({
                'sn': i,
                'vendor_name': po.partner_id.name,
                'qualifications': qualification_text,
                'quoted_price': total_amount,
                'quoted_price_formatted': f"{total_amount:,.0f} FRW",
                'is_selected': po.id == self.id,
                'submission_date': po.date_order.strftime('%d/%m/%Y') if po.date_order else '',
            })
        
        # Sort by total amount (ascending - lowest first)
        participants.sort(key=lambda x: x['quoted_price'])
        
        return participants

    def action_create_tender_group(self):
        """Create a tender group for this PO"""
        self.ensure_one()
        
        if self.purchase_group_id:
            raise UserError(_("This Purchase Order is already part of a tender group."))
        
        # Create a new purchase group
        purchase_group = self.env['purchase.order.group'].create({
            'order_ids': [(6, 0, [self.id])]
        })
        
        self.write({'purchase_group_id': purchase_group.id})
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                **self.env.context,
                'tender_group_created': True,
            }
        }
