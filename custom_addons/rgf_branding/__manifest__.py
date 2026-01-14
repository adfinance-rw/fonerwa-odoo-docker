# -*- coding: utf-8 -*-
{
    'name': 'Rwanda Green Fund Branding',
    'version': '2.1',
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
        # Dark mode variable overrides (loaded first in compilation chain)
        'web.dark_mode_variables': [
            'rgf_branding/static/src/scss/dark_mode_variables.scss',
        ],
        # Light mode variable overrides (loaded early in compilation chain)
        'web._assets_primary_variables': [
            'rgf_branding/static/src/scss/light_mode_variables.scss',
        ],
        # Backend styling (loaded after variables are compiled)
        'web.assets_backend': [
            'rgf_branding/static/src/scss/rgf_backend.scss',
        ],
        # Frontend styling
        'web.assets_frontend': [
            'rgf_branding/static/src/scss/rgf_frontend.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

