# -*- coding: utf-8 -*-
{
    'name': "Signature Report",
    'summary': "Add user signature images for approvals and printouts",
    'description': """
        This module allows users to upload handwritten signature images in their user profile.
        When a user approves a document, their signature image can be shown on printouts.
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Tools',
    'version': '18.0.0.0.0',
    'depends': ['base', 'purchase', 'approvals', 'approvals_purchase'],
    'data': [
         'security/ir.model.access.csv',  # Uncomment if you add security rules
        'views/res_users_signature.xml',
        'views/report_purchaseorder_document.xml',   # Your user form view inheritance
        'views/partner_validity.xml',
        'views/purchase_budjet_line.xml',


    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

