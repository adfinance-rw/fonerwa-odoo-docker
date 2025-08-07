# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools import SQL


class BudgetReport(models.Model):
    """Extend Budget Report with Budgetary Activity and IFMIS Mapping fields"""
    _inherit = 'budget.report'

    # NEW FIELDS for reporting
    budget_activity_id = fields.Many2one(
        'budget.activity',
        string='Budgetary Activity',
        readonly=True,
        help="Classification of this budget by activity type"
    )
    budget_activity_code = fields.Char(
        string='Activity Code',
        readonly=True,
        help="Code of the budgetary activity"
    )
    budget_activity_name = fields.Char(
        string='Activity Name',
        readonly=True,
        help="Name of the budgetary activity"
    )
    ifmis_mapping_id = fields.Many2one(
        'ifmis.mapping',
        string='IFMIS Mapping',
        readonly=True,
        help="Mapping to IFMIS system"
    )
    ifmis_code = fields.Char(
        string='IFMIS Code',
        readonly=True,
        help="Code in IFMIS system"
    )
    ifmis_category = fields.Selection([
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
        ('capital', 'Capital Expenditure'),
        ('transfer', 'Transfer'),
        ('other', 'Other'),
    ], string='IFMIS Category', readonly=True)
    
    # MEASURE FIELDS for reporting
    activity_count = fields.Integer(
        string='Activity Count',
        readonly=True,
        help="Count of budget lines with this activity (useful as measure)"
    )
    ifmis_count = fields.Integer(
        string='IFMIS Count', 
        readonly=True,
        help="Count of budget lines with this IFMIS mapping (useful as measure)"
    )
    budget_by_activity = fields.Float(
        string='Budget by Activity',
        readonly=True,
        help="Budget amount grouped by activity (measure)"
    )
    budget_by_ifmis = fields.Float(
        string='Budget by IFMIS',
        readonly=True,
        help="Budget amount grouped by IFMIS category (measure)"
    )

    def _get_bl_query(self, plan_fnames):
        """Override budget line query to include our new fields"""
        return SQL(
            """
            SELECT CONCAT('bl', bl.id::TEXT) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'budget.analytic' AS res_model,
                   bl.budget_analytic_id AS res_id,
                   bl.date_from AS date,
                   ba.name AS description,
                   bl.company_id AS company_id,
                   NULL AS user_id,
                   'budget' AS line_type,
                   bl.budget_amount AS budget,
                   0 AS committed,
                   0 AS achieved,
                   bl.budget_activity_id AS budget_activity_id,
                   COALESCE(bl.budget_activity_code, 'No Activity') AS budget_activity_code,
                   COALESCE(bl.budget_activity_name, 'No Activity Assigned') AS budget_activity_name,
                   bl.ifmis_mapping_id AS ifmis_mapping_id,
                   COALESCE(bl.ifmis_code, 'No IFMIS') AS ifmis_code,
                   bl.ifmis_category AS ifmis_category,
                   CASE WHEN bl.budget_activity_id IS NOT NULL THEN 1 ELSE 0 END AS activity_count,
                   CASE WHEN bl.ifmis_mapping_id IS NOT NULL THEN 1 ELSE 0 END AS ifmis_count,
                   CASE WHEN bl.budget_activity_id IS NOT NULL THEN bl.budget_amount ELSE 0 END AS budget_by_activity,
                   CASE WHEN bl.ifmis_mapping_id IS NOT NULL THEN bl.budget_amount ELSE 0 END AS budget_by_ifmis,
                   %(plan_fields)s
              FROM budget_line bl
              JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
            """,
            plan_fields=SQL(', ').join(self.env['budget.line']._field_to_sql('bl', fname) for fname in plan_fnames)
        )

    def _get_aal_query(self, plan_fnames):
        """Override analytic line query to include our new fields"""
        return SQL(
            """
            SELECT CONCAT('aal', aal.id::TEXT) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'account.analytic.line' AS res_model,
                   aal.id AS res_id,
                   aal.date AS date,
                   aal.name AS description,
                   aal.company_id AS company_id,
                   aal.user_id AS user_id,
                   'achieved' AS line_type,
                   0 AS budget,
                   aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END AS committed,
                   aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END AS achieved,
                   bl.budget_activity_id AS budget_activity_id,
                   COALESCE(bl.budget_activity_code, 'No Activity') AS budget_activity_code,
                   COALESCE(bl.budget_activity_name, 'No Activity Assigned') AS budget_activity_name,
                   bl.ifmis_mapping_id AS ifmis_mapping_id,
                   COALESCE(bl.ifmis_code, 'No IFMIS') AS ifmis_code,
                   bl.ifmis_category AS ifmis_category,
                   CASE WHEN bl.budget_activity_id IS NOT NULL THEN 1 ELSE 0 END AS activity_count,
                   CASE WHEN bl.ifmis_mapping_id IS NOT NULL THEN 1 ELSE 0 END AS ifmis_count,
                   CASE WHEN bl.budget_activity_id IS NOT NULL THEN (aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END) ELSE 0 END AS budget_by_activity,
                   CASE WHEN bl.ifmis_mapping_id IS NOT NULL THEN (aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END) ELSE 0 END AS budget_by_ifmis,
                   %(analytic_fields)s
              FROM account_analytic_line aal
         LEFT JOIN budget_line bl ON (bl.company_id IS NULL OR aal.company_id = bl.company_id)
                                 AND aal.date >= bl.date_from
                                 AND aal.date <= bl.date_to
                                 AND %(condition)s
         LEFT JOIN account_account aa ON aa.id = aal.general_account_id
         LEFT JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
             WHERE CASE
                       WHEN ba.budget_type = 'expense' THEN (
                           SPLIT_PART(aa.account_type, '_', 1) = 'expense'
                           OR (aa.account_type IS NULL AND aal.category NOT IN ('invoice', 'other'))
                           OR (aa.account_type IS NULL AND aal.category = 'other' AND aal.amount < 0)
                       )
                       WHEN ba.budget_type = 'revenue' THEN (
                           SPLIT_PART(aa.account_type, '_', 1) = 'income'
                           OR (aa.account_type IS NULL AND aal.category = 'other' AND aal.amount > 0)
                       )
                       ELSE TRUE
                   END
                   AND (SPLIT_PART(aa.account_type, '_', 1) IN ('income', 'expense') OR aa.account_type IS NULL)
            """,
            analytic_fields=SQL(', ').join(self.env['account.analytic.line']._field_to_sql('aal', fname) for fname in plan_fnames),
            condition=SQL(' AND ').join(SQL(
                "(%(bl)s IS NULL OR %(aal)s = %(bl)s)",
                bl=self.env['budget.line']._field_to_sql('bl', fname),
                aal=self.env['budget.line']._field_to_sql('aal', fname),
            ) for fname in plan_fnames)
        )

    def _get_pol_query(self, plan_fnames):
        """Override purchase order line query to include our new fields"""
        qty_invoiced_table = SQL(
            """
               SELECT SUM(
                          CASE WHEN COALESCE(uom_aml.id != uom_pol.id, FALSE)
                               THEN ROUND((aml.quantity / uom_aml.factor) * uom_pol.factor, -LOG(uom_pol.rounding)::integer)
                               ELSE COALESCE(aml.quantity, 0)
                          END
                          * CASE WHEN am.move_type = 'in_invoice' THEN 1
                                 WHEN am.move_type = 'in_refund' THEN -1
                                 ELSE 0 END
                      ) AS qty_invoiced,
                      pol.id AS pol_id
                 FROM purchase_order po
            LEFT JOIN purchase_order_line pol ON pol.order_id = po.id
            LEFT JOIN account_move_line aml ON aml.purchase_line_id = pol.id
            LEFT JOIN account_move am ON aml.move_id = am.id
            LEFT JOIN uom_uom uom_aml ON uom_aml.id = aml.product_uom_id
            LEFT JOIN uom_uom uom_pol ON uom_pol.id = pol.product_uom
            LEFT JOIN uom_category uom_category_aml ON uom_category_aml.id = uom_pol.category_id
            LEFT JOIN uom_category uom_category_pol ON uom_category_pol.id = uom_pol.category_id
                WHERE aml.parent_state = 'posted'
             GROUP BY pol.id
        """)
        return SQL(
            """
            SELECT (pol.id::TEXT || '-' || ROW_NUMBER() OVER (PARTITION BY pol.id ORDER BY pol.id)) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'purchase.order' AS res_model,
                   po.id AS res_id,
                   po.date_order AS date,
                   pol.name AS description,
                   pol.company_id AS company_id,
                   po.user_id AS user_id,
                   'committed' AS line_type,
                   0 AS budget,
                   COALESCE(pol.price_subtotal::FLOAT, pol.price_unit::FLOAT * pol.product_qty)
                        / COALESCE(NULLIF(pol.product_qty, 0), 1)
                        * (pol.product_qty - COALESCE(qty_invoiced_table.qty_invoiced, 0))
                        / po.currency_rate
                        * (a.rate)
                        * CASE WHEN ba.budget_type = 'both' THEN -1 ELSE 1 END AS committed,
                   0 AS achieved,
                   bl.budget_activity_id AS budget_activity_id,
                   COALESCE(bl.budget_activity_code, 'No Activity') AS budget_activity_code,
                   COALESCE(bl.budget_activity_name, 'No Activity Assigned') AS budget_activity_name,
                   bl.ifmis_mapping_id AS ifmis_mapping_id,
                   COALESCE(bl.ifmis_code, 'No IFMIS') AS ifmis_code,
                   bl.ifmis_category AS ifmis_category,
                   CASE WHEN bl.budget_activity_id IS NOT NULL THEN 1 ELSE 0 END AS activity_count,
                   CASE WHEN bl.ifmis_mapping_id IS NOT NULL THEN 1 ELSE 0 END AS ifmis_count,
                   CASE WHEN bl.budget_activity_id IS NOT NULL THEN (COALESCE(pol.price_subtotal::FLOAT, pol.price_unit::FLOAT * pol.product_qty) / COALESCE(NULLIF(pol.product_qty, 0), 1) * (pol.product_qty - COALESCE(qty_invoiced_table.qty_invoiced, 0)) / po.currency_rate * (a.rate) * CASE WHEN ba.budget_type = 'both' THEN -1 ELSE 1 END) ELSE 0 END AS budget_by_activity,
                   CASE WHEN bl.ifmis_mapping_id IS NOT NULL THEN (COALESCE(pol.price_subtotal::FLOAT, pol.price_unit::FLOAT * pol.product_qty) / COALESCE(NULLIF(pol.product_qty, 0), 1) * (pol.product_qty - COALESCE(qty_invoiced_table.qty_invoiced, 0)) / po.currency_rate * (a.rate) * CASE WHEN ba.budget_type = 'both' THEN -1 ELSE 1 END) ELSE 0 END AS budget_by_ifmis,
                   %(analytic_fields)s
              FROM purchase_order_line pol
         LEFT JOIN (%(qty_invoiced_table)s) qty_invoiced_table ON qty_invoiced_table.pol_id = pol.id
              JOIN purchase_order po ON pol.order_id = po.id AND po.state in ('purchase', 'done')
        CROSS JOIN JSONB_TO_RECORDSET(pol.analytic_json) AS a(rate FLOAT, %(field_cast)s)
         LEFT JOIN budget_line bl ON (bl.company_id IS NULL OR po.company_id = bl.company_id)
                                 AND po.date_order >= bl.date_from
                                 AND date_trunc('day', po.date_order) <= bl.date_to
                                 AND %(condition)s
         LEFT JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
             WHERE pol.product_qty > COALESCE(qty_invoiced_table.qty_invoiced, 0)
               AND ba.budget_type != 'revenue'
            """,
            analytic_fields=SQL(', ').join(self.env['account.analytic.line']._field_to_sql('a', fname) for fname in plan_fnames),
            qty_invoiced_table=qty_invoiced_table,
            field_cast=SQL(', ').join(SQL('%s FLOAT', SQL.identifier(fname)) for fname in plan_fnames),
            condition=SQL(' AND ').join(SQL(
                "(%(bl)s IS NULL OR %(a)s = %(bl)s)",
                bl=self.env['budget.line']._field_to_sql('bl', fname),
                a=self.env['budget.line']._field_to_sql('a', fname),
            ) for fname in plan_fnames)
        ) 