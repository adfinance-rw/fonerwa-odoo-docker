# -*- coding: utf-8 -*-
{
    "name": "Approval Module",
    "version": "1.1.1",
    "summary": "Manage approval process",
    "depends": ["base", "approvals", "sign"],
    "data": [
        "security/ir.model.access.csv",
        "report/approval_request_report.xml",
        "views/approval_request_views.xml",
        "views/res_company_views.xml",
        "views/res_users_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}