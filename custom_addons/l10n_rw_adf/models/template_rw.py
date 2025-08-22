# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('rw')
    def _get_rw_template_data(self):
        return {
            'property_account_expense_categ_id':'l10n_rw_600101',
            'property_account_income_categ_id':'l10n_rw_700101',
            'property_account_receivable_id':'l10n_rw_500401',
            'property_account_payable_id':'l10n_rw_300101',
            #'property_tax_payable_account_id': 'l10n_rw_500502',
            #'property_tax_receivable_account_id': 'l10n_rw_500502',
            'code_digits': '6',
        }

    @template('rw', 'res.company')
    def _get_rw_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.rw',
                'bank_account_code_prefix': '5007',
                'cash_account_code_prefix': '5009',
                'transfer_account_code_prefix': '50072',
                'income_currency_exchange_account_id': 'l10n_rw_600621',
                'expense_currency_exchange_account_id': 'l10n_rw_600622',
                #'account_sale_tax_id': 'l10n_rw_500502',
                #'account_purchase_tax_id': 'l10n_rw_500502',
                'default_cash_difference_expense_account_id': 'l10n_rw_500902',
                'default_cash_difference_income_account_id': 'l10n_rw_500903',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_rw_600623',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_rw_600624',
                'account_journal_payment_credit_account_id':'l10n_rw_500906',
                'account_journal_payment_debit_account_id':'l10n_rw_500905',
                'account_journal_suspense_account_id':'l10n_rw_500904',
            },
        }
