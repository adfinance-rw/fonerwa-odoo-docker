{
    'name': 'Stock Report Custom',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Custom Stock Report with Filters',
    'author': 'Julien at ADFinance Ltd',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_report_views.xml',
        'wizard/stock_report_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'website': 'https://www.adfinance.co',
}
