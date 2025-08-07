# -*- coding: utf-8 -*-
{
    'name': 'Budget Extension - IFMIS Integration',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Extend Budget Lines with Budgetary Activity and IFMIS Mapping fields',
    'description': """
Budget Extension Module
=======================

This module extends the standard Odoo budget functionality by adding:

1. **Budgetary Activity Field**: 
   - Classification field for each budget line
   - Master data management for budgetary activities
   - Filtering and grouping capabilities in reports

2. **IFMIS Mapping Field**:
   - Integration mapping for IFMIS (Integrated Financial Management Information System)
   - Allows mapping budget lines to external IFMIS system
   - Supports reporting and reconciliation with external systems

3. **Enhanced Budget Reporting**:
   - Advanced filtering by activity and IFMIS mapping
   - Subtotals and grouping by budgetary activity
   - Subtotals and grouping by IFMIS category
   - Enhanced search and analysis capabilities

Integration with Existing Budget Management:
-------------------------------------------
- Extends the standard budget.line model
- Works within the existing "Budget" menu structure
- Compatible with existing budget analytics and reporting
- Maintains all standard budget functionality

Features:
---------
- Master data management for Budgetary Activities
- IFMIS mapping configuration and sync status tracking
- Enhanced budget line views with classification fields
- Advanced reporting with filtering and subtotals by activity/IFMIS
- Budget lines analysis with grouping capabilities
- Data validation and integrity checks
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'account',
        'account_budget',
    ],
    'data': [
        'views/budget_activity_views.xml',
        'views/ifmis_mapping_views.xml',
        'views/budget_line_views.xml',
        'views/budget_report_views.xml',
        'security/ir.model.access.csv',
        'data/budget_activity_data.xml',
    ],
    'demo': [
        'data/budget_demo_data.xml',
    ],
    'images': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
} 