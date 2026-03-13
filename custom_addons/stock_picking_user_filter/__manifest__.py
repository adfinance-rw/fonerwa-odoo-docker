{
    'name': 'Stock Picking User Filter',
    'version': '18.0.1.0.0',
    'summary': 'Restrict stock picking visibility to own records',
    'description': 'Users only see their own inventory operations (by contact). Admins see all.',
    'category': 'Inventory',
    'depends': ['stock'],
    'data': [
        'security/ir_rule.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
