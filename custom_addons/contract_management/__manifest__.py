# -*- coding: utf-8 -*-
{
    'name': 'Contract Management System',
    'version': '18.0.1.0.1',
    'category': 'Sales',
    'summary': 'Contract Management System for managing contracts',
    'description': """
        Contract Management System
        =========================

        This module provides functionality to manage contracts and agreements.
        Features include:
        - Contract creation and management
        - Contract templates
        - Contract tracking and monitoring
        - Contract renewal management
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/contract_configuration_data.xml',
        'data/email_templates.xml',
        'data/cron_data.xml',
        'views/contract_views.xml',
        'views/milestone_views.xml',
        'views/contract_amendment_views.xml',
        'views/contract_amendment_wizard_views.xml',
        'views/contract_termination_wizard_views.xml',
        'views/wizard_views.xml',
        'views/menu.xml',
        'views/contract_configuration_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}