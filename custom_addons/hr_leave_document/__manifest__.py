# -*- coding: utf-8 -*-
{
    'name': 'Time Off - Supporting Document Requirement',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Require supporting documents for specific leave types',
    'description': """
        Adds configurable supporting document requirements per leave type:
        - Always required (e.g., Maternity Leave, Paternity Leave)
        - Required after X days (e.g., Sick Time Off > 2 days)
    """,
    'author': 'Your Company',
    'depends': ['hr_holidays'],
    'data': [
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
