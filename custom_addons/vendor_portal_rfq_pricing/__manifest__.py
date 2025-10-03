{
    'name': 'Vendor Portal RFQ Pricing',
    'version': '18.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Allow vendors to input prices for RFQ lines through the portal',
    'description': """
        Vendor Portal RFQ Pricing
        =========================
        
        This module enhances the vendor portal to allow suppliers to:
        * Input prices for each product line on RFQs they receive
        * Store prices in a separate field (x_supplier_price) 
        * Notify purchasing team when prices are submitted
        * Enable internal users to review and transfer prices
        
        Features:
        * Secure vendor portal integration
        * Custom field for supplier pricing
        * Backend price review and transfer tools
        * Notification system for price submissions
        * Bulk price transfer wizard
        * Comprehensive access control
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'purchase', 
        'purchase_stock',
        'portal',
        'mail',
        'website',
        'web'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/purchase_order_views.xml',
        'views/portal_templates.xml',
        'wizard/price_transfer_wizard.xml',
        'data/mail_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'vendor_portal_rfq_pricing/static/src/css/portal_style.css',
            'vendor_portal_rfq_pricing/static/src/js/portal_rfq.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
} 
