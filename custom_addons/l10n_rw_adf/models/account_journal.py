# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _prepare_liquidity_account_vals(self, company, code, vals):
        # Add mapping for new cash and bank account
        result = super(AccountJournal, self)._prepare_liquidity_account_vals(company, code, vals)
        result.update({
            'l10n_rw_report_mapping': 'cash_and_cash_equivalents',
        })
        return result
