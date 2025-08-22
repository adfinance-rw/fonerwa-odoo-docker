# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Rwanda - Accounting Reports',
    'countries': ['rw'],
    'version': '18.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Base module for Rwandan reports
    """,
    'depends': [
        'l10n_rw_adf',
        'account_reports',
    ],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_and_loss.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
}
