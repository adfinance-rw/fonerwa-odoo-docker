# -*- coding: utf-8 -*-
{
    'name': 'Rwanda - Accounting',
    'icon': '/l10n_rw_adf/static/description/icon.png',
    'countries': ['rw'],
    'version': '18.0',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'ADFinance ltd',
    'description': """
        Chart accounting and taxes for Rwanda
    """,
    'depends': [
        'account', 'base_vat',
    ],
    'data': [
        'data/tax_report.xml',

        'views/account_account_views.xml',
        'views/account_tax_views.xml',
    ],
    'license': 'LGPL-3',
}
