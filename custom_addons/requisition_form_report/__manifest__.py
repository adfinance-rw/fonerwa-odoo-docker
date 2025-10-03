# -*- coding: utf-8 -*-
{
    'name': 'Requisition Form Report',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Reporting',
    'summary': 'Generate Requisition Form reports from Internal Transfer operations',
    'description': """
        Requisition Form Report
        ======================
        
        This module provides a comprehensive requisition form report for Internal Transfer operations.
        
        Features:
        * Generate requisition forms from Internal Transfer records
        * Professional layout matching government standards
        * Detailed item listing with quantities requested and received
        * Signature fields for approval and receipt tracking
        * Print directly from Internal Transfer views
        
        Report Structure:
        * Item description and quantities
        * Requested by and approval fields
        * Received by and issued by signatures
        * Professional government-style formatting
    """,
    'author': 'ADFinance Team',
    'website': 'https://www.adfinance.co',
    'depends': [
        'base',
        'stock',
        'purchase',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/requisition_form_report.xml',
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'requisition_form_report/static/src/css/requisition_form.css',
        ],
        'web.assets_report': [
            'requisition_form_report/static/src/css/requisition_form.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
