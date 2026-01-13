# -*- coding: utf-8 -*-
{
    "name": "Approval Module",
    "version": "1.1.1",
    "summary": "Manage approval process",
    "depends": ["base", "approvals", "sign", "web", "contract_management"],
    "data": [
        "security/approval_security_groups.xml",
        "security/ir.model.access.csv",
        "security/approval_record_rules.xml",
        "data/approval_kinds.xml",
        "data/approval_category_templates.xml",
        "data/paperformat.xml",
        "report/approval_request_report.xml",
        "views/approval_menu_views.xml",
        "views/approval_delegation_views.xml",
        "views/approval_category_views.xml",
        "views/approval_request_views.xml",
        "views/res_company_views.xml",
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "approval_module/static/src/css/contract_price_table.css",
            "approval_module/static/src/js/approvals_category_kanban_controller.js",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}