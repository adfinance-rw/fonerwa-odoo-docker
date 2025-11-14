# -*- coding: utf-8 -*-
{
    "name": "HR Appraisal Objectives",
    "version": "2.0.0",
    "summary": "Comprehensive hierarchical performance management system",
    "description": """
        HR Appraisal Objectives Module
        ==============================
        Features:
        - Hierarchical objective management (Institutional → Department → Individual)
        - Real-time progress tracking and reporting
        - Comprehensive dashboard and analytics
        - Automated notifications and reminders
        - Role-based access control and workflow
        - Performance evaluation and scoring system
        - Bulk operations and management tools
        - Template system for standardized objectives
        - Detailed reporting and performance analytics
        - Mobile-friendly responsive design
        User Roles:
        - HR Manager: Full system access, institutional objectives, appraisal creation
        - Line Managers: Department objectives, team performance management
        - Employees: Individual objectives, progress tracking, self-assessment
    """,
    "author": "ADFinance",
    "website": "https://www.adfinance.co",
    "category": "Human Resources/Appraisals",
    "depends": ["base_setup", "web", "hr", "hr_appraisal", "mail", "project", "hr_timesheet"],
    "data": [
        # Security
        "security/hr_appraisal_objectives_groups.xml",
        "security/ir.model.access.csv",
        "security/hr_appraisal_objectives_security.xml",
        # Data and configurations
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "data/rating_scale_data.xml",
        # Views
        "views/fiscal_year_views.xml",
        "views/rating_scale_views.xml",
        "views/kpi_views.xml",
        "views/appraisal_views.xml",
        "views/institutional_objective_views.xml",
        "views/department_objective_views.xml",
        "views/individual_objective_views.xml",
        "views/common_objective_views.xml",
        "views/timesheet_views.xml",
        "views/objective_dashboard_views.xml",
        # Wizards
        # "wizards/performance_report_views.xml",
        "wizards/rejection_wizard_views.xml",
        "wizards/batch_rejection_wizard_views.xml",
        "wizards/hr_revert_wizard_views.xml",
        # Actions
        "views/batch_approval_actions.xml",
        # Reports
        "reports/performance_report.xml",
        # Dashboard Views
        "views/performance_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_appraisal_objectives/static/src/css/analytics.css",
            "hr_appraisal_objectives/static/src/css/kanban_enhancements.css",
            "hr_appraisal_objectives/static/src/js/custom_datepicker_limit.js",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
    "support": "support@adfinance.com",
}
