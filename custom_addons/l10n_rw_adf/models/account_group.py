# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountGroup(models.Model):
    _inherit = 'account.group'

    def name_get(self):
        result = []
        for group in self:
            if (group.company_id and group.company_id.chart_template_id  # If company have chart_template
                    and group.company_id.chart_template_id.id == self.env.ref('l10n_rw.l10n_rw_chart_template').id
                    # And is using our chart template
            ):
                prefix = group.code_prefix_start and str(group.code_prefix_start)
                name = prefix.ljust(6, '0') + ' ' + group.name
                result.append((group.id, name))
            else:
                name = super(AccountGroup, group).name_get()
                if isinstance(name, list):
                    name = name[0]
                result.append(name)
        return result
