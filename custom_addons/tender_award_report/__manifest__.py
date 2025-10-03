# -*- coding: utf-8 -*-
{
    'name': 'Tender Award Report',
    'version': '18.0.1.0.0',
    'category': 'Purchase/Reporting',
    'summary': 'Generate Tender Award reports for purchase orders with alternatives',
    'description': """
        Tender Award Report
        ===================
        
        This module generates formal Tender Award reports for Purchase Orders that are part of a tender process.
        
        Features:
        * Generate Tender Award reports before PO validation
        * List all participating vendors with their quoted prices
        * Highlight the selected vendor (winning bid)
        * Include formal recommendation section with justification
        * Professional government-style formatting
        * Integration with purchase alternative workflow
        
        Report Structure:
        * Company header with tender description
        * Legal reference and introduction
        * Bidder comparison table with qualifications and prices
        * Formal recommendation with amount in words
        * Approval chain with signature fields
        
        Usage:
        * Available for Purchase Orders with purchase_group_id (tender groups)
        * Accessible via print button on PO form
        * Generated before PO validation as required
    """,
    'author': 'RGF Team',
    'website': 'https://www.rgf.rw',
    'depends': [
        'base',
        'purchase',
        'purchase_requisition',
        'mail',
        'web',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/tender_award_report.xml',
        'views/purchase_order_views.xml',
    ],
    'test': [
        'tests/test_tender_award_report.py',
    ],
    'assets': {
        'web.assets_backend': [
            'tender_award_report/static/src/css/tender_award.css',
        ],
        'web.assets_report': [
            'tender_award_report/static/src/css/tender_award.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
