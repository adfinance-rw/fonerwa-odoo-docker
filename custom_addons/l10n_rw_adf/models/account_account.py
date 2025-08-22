# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    l10n_rw_report_mapping = fields.Selection(
        [
            # Non-current assets
            ('property_plant_and_equipment','Property, Plant and Equipment and Investment Property'),
            ('intangible_assets', 'Intangible Assets'),
            # Current Assets
            ('inventories', 'Inventories'),
            ('trade_receivables', 'Trade Receivables'),
            ('other_current_assets', 'Other Current Assets'),
            ('income_tax_asset', 'Income Tax Asset'),
            ('cash_and_cash_equivalents', 'Cash and Cash Equivalents'),
            # Equity
            ('share_capital', 'Share Capital'),
            ('retained_earnings', 'Retained Earnings'),
            ('revaluation_reserves', 'Revaluation Reserves'),
            # Non Current Liability
            ('long_term_borrowings', 'Long Term Borrowings'),
            ('long_term_provisions', 'Long Term Provisions'),
            # Current Liability
            ('short_term_borrowings', 'Short Term Borrowings'),
            ('short_term_provision', 'Short Term Provision'),
            ('trade_payables', 'Trade Payables'),
            ('income_tax_liability', 'Income Tax Liability'),
            ('other_current_liabilities', 'Other Current Liabilities'),
            # Profit and Loss
            ('revenue', 'Revenue'),
            ('cost_of_sales', 'Cost of Sales'),
            ('other_income', 'Other Income'),
            ('administrative_expenses', 'Administrative Expenses'),
            ('selling_and_distribution', 'Selling and Distribution'),
            ('staff_cost', 'Staff Cost'),
            ('depreciation_and_amortisation', 'Depreciation and Amortisation'),
            ('finance_costs', 'Finance Costs'),
            ('cit', 'CIT(Current Income Tax)'),
        ]
        ,
        'Report Mapping',
        help=""
    )

    @api.depends('company_id')
    @api.constrains('code')
    def _check_code(self):
        for record in self:
            # if (record.company_id and record.company_id.chart_template_id # If company have chart_template
            #         and record.company_id.chart_template_id.id == self.env.ref('l10n_rw.l10n_rw_chart_template').id # And is using the our chart template
            #         and record.code and not (record.code.isdigit() and len(record.code)==6)):
            #     raise ValidationError("Code must be 6 digits")
            pass
