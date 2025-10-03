# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestTenderAwardReport(TransactionCase):

    def setUp(self):
        super().setUp()
        
        # Create test vendors
        self.vendor1 = self.env['res.partner'].create({
            'name': 'Joseph Gaga',
            'is_company': True,
            'supplier_rank': 1,
        })
        
        self.vendor2 = self.env['res.partner'].create({
            'name': 'Geoffrey Kayonga',
            'is_company': True,
            'supplier_rank': 1,
        })
        
        self.vendor3 = self.env['res.partner'].create({
            'name': 'Jean Paul Turikumwe',
            'is_company': True,
            'supplier_rank': 1,
        })
        
        # Create test product
        self.product = self.env['product.product'].create({
            'name': 'Website Design Service',
            'type': 'service',
            'purchase_ok': True,
        })
        
        # Create test users for approval chain
        self.prepared_by = self.env['res.users'].create({
            'name': 'Enock NTIGAMBURURA',
            'login': 'enock',
            'email': 'enock@rgf.rw',
        })
        
        self.first_approval = self.env['res.users'].create({
            'name': 'Alex MUGANZA',
            'login': 'alex',
            'email': 'alex@rgf.rw',
        })
        
        self.final_approval = self.env['res.users'].create({
            'name': 'Teddy MUGABO MPINGANZIMA',
            'login': 'teddy',
            'email': 'teddy@rgf.rw',
        })

    def test_tender_award_report_generation(self):
        """Test tender award report generation for a tender group"""
        
        # Create first PO (selected one)
        po1 = self.env['purchase.order'].create({
            'partner_id': self.vendor1.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 944000,
            })],
            'tender_description': 'HIRING A CONSULTANT TO IMPROVE GCKC WEBSITE',
            'prepared_by': self.prepared_by.id,
            'first_approval': self.first_approval.id,
            'final_approval': self.final_approval.id,
        })
        
        # Create alternative POs
        po2 = self.env['purchase.order'].create({
            'partner_id': self.vendor2.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 1500000,
            })],
        })
        
        po3 = self.env['purchase.order'].create({
            'partner_id': self.vendor3.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 1200000,
            })],
        })
        
        # Create purchase group to link POs
        purchase_group = self.env['purchase.order.group'].create({
            'order_ids': [(6, 0, [po1.id, po2.id, po3.id])]
        })
        
        # Update POs with group
        po1.write({'purchase_group_id': purchase_group.id})
        po2.write({'purchase_group_id': purchase_group.id})
        po3.write({'purchase_group_id': purchase_group.id})
        
        # Test computed fields
        self.assertEqual(po1.tender_participants_count, 3)
        self.assertTrue(po1.tender_participants)
        
        # Test report generation
        result = po1.action_generate_tender_award_report()
        self.assertEqual(result['type'], 'ir.actions.report')
        self.assertEqual(result['report_name'], 'tender_award_report.tender_award_template')
        
        # Test that report is marked as generated
        self.assertTrue(po1.tender_award_generated)
        self.assertTrue(po1.tender_award_date)
        
        # Test participants data
        participants = po1._get_tender_participants_for_report()
        self.assertEqual(len(participants), 3)
        
        # Check that participants are sorted by price (ascending)
        self.assertEqual(participants[0]['vendor_name'], 'Joseph Gaga')
        self.assertEqual(participants[0]['quoted_price'], 944000)
        self.assertTrue(participants[0]['is_selected'])
        
        self.assertEqual(participants[1]['vendor_name'], 'Jean Paul Turikumwe')
        self.assertEqual(participants[1]['quoted_price'], 1200000)
        self.assertFalse(participants[1]['is_selected'])
        
        self.assertEqual(participants[2]['vendor_name'], 'Geoffrey Kayonga')
        self.assertEqual(participants[2]['quoted_price'], 1500000)
        self.assertFalse(participants[2]['is_selected'])

    def test_validation_without_report(self):
        """Test that validation fails without tender award report"""
        
        # Create PO with tender group
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor1.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 944000,
            })],
        })
        
        # Create purchase group
        purchase_group = self.env['purchase.order.group'].create({
            'order_ids': [(6, 0, [po.id])]
        })
        po.write({'purchase_group_id': purchase_group.id})
        
        # Test that validation fails without report
        with self.assertRaises(UserError):
            po.button_confirm()

    def test_validation_with_report(self):
        """Test that validation succeeds with tender award report"""
        
        # Create PO with tender group
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor1.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 944000,
            })],
        })
        
        # Create purchase group
        purchase_group = self.env['purchase.order.group'].create({
            'order_ids': [(6, 0, [po.id])]
        })
        po.write({'purchase_group_id': purchase_group.id})
        
        # Generate report
        po.action_generate_tender_award_report()
        
        # Test that validation succeeds
        po.button_confirm()
        self.assertEqual(po.state, 'purchase')

    def test_no_tender_group(self):
        """Test that report generation fails for PO without tender group"""
        
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor1.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 944000,
            })],
        })
        
        # Test that report generation fails
        with self.assertRaises(UserError):
            po.action_generate_tender_award_report()

    def test_amount_in_words(self):
        """Test amount conversion to words"""
        
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor1.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 944000,
            })],
        })
        
        amount_words = po._get_amount_in_words(944000)
        self.assertIn('944,000', amount_words)
        self.assertIn('Rwandan Francs', amount_words)
