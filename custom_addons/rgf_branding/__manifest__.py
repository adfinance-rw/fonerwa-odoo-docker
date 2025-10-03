# -*- coding: utf-8 -*-
{
    'name': 'Rwanda Green Fund Branding',
    'version': '1.0',
    'category': 'Customizations',
    'summary': 'Custom branding and color scheme for Rwanda Green Fund',
    'description': """
        Rwanda Green Fund Branding Module
        ==================================
        
        This module applies the official Rwanda Green Fund brand colors
        throughout the Odoo interface, including:
        
        * Primary colors: Rich Black, Garden Glow, Bleached Jade
        * Supporting colors: Cambridge Blue, Sagebrush, Tetsu Iron, etc.
        * Custom CSS overrides for buttons, navigation, forms, and more
        
        Brand Colors:
        - Rich Black (#013f41) - 60%
        - Garden Glow (#7faf81) - 20%
        - Bleached Jade (#e0e5d1) - 20%
    """,
    'author': 'Rwanda Green Fund',
    'website': 'https://www.fonerwa.org',
    'depends': ['web', 'base'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'rgf_branding/static/src/css/rgf_backend.css',
        ],
        'web.assets_frontend': [
            'rgf_branding/static/src/css/rgf_frontend.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

