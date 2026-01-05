# -*- coding: utf-8 -*-

from odoo import models, fields, tools


class ContractReport(models.Model):
    _name = 'contract.report'
    _description = 'Contract Report'
    _auto = False

    contract_id = fields.Many2one(
        'contract.management',
        string='Contract'
    )
    
    contract_number = fields.Char(
        string='Contract Number'
    )
    
    contract_name = fields.Char(
        string='Contract Name'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner'
    )
    
    contract_type_id = fields.Many2one(
        'contract.management.type',
        string='Contract Type'
    )
    
    contract_type_name = fields.Char(
        string='Contract Type Name'
    )
    
    classification_names = fields.Char(
        string='Classifications'
    )
    
    category_names = fields.Char(
        string='Categories'
    )
    
    department_names = fields.Char(
        string='Departments'
    )
    
    effective_date = fields.Date(
        string='Effective Date'
    )
    
    expiry_date = fields.Date(
        string='Expiry Date'
    )
    
    days_to_expiry = fields.Integer(
        string='Days to Expiry'
    )
    
    contract_value = fields.Monetary(
        string='Contract Value',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('renewed', 'Renewed'),
        ('terminated', 'Terminated'),
        ('archived', 'Archived')
    ], string='Status')
    
    contract_manager_id = fields.Many2one(
        'res.users',
        string='Contract Manager'
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Check if configuration tables exist by querying PostgreSQL catalog
        def table_exists(table_name):
            self.env.cr.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table_name,))
            return self.env.cr.fetchone()[0]
        
        type_table_exists = table_exists('contract_management_type')
        classification_table_exists = table_exists('contract_management_classification')
        category_table_exists = table_exists('contract_management_category')
        department_table_exists = table_exists('contract_management_department')
        
        # Check relation tables
        classification_rel_exists = table_exists('contract_classification_rel')
        category_rel_exists = table_exists('contract_category_rel')
        department_rel_exists = table_exists('contract_department_rel')
        
        # Build the query based on which tables exist
        if (type_table_exists and classification_table_exists and 
            category_table_exists and department_table_exists and
            classification_rel_exists and category_rel_exists and 
            department_rel_exists):
            # Full query with all joins
            query = """
                SELECT 
                    c.id as id,
                    c.id as contract_id,
                    c.contract_number,
                    c.name as contract_name,
                    c.partner_id,
                    c.contract_type_id,
                    t.name::text as contract_type_name,
                    cls.names as classification_names,
                    cat.names as category_names,
                    dept.names as department_names,
                    c.effective_date,
                    c.expiry_date,
                    CASE 
                        WHEN c.expiry_date IS NOT NULL 
                        THEN (c.expiry_date - CURRENT_DATE)::integer
                        ELSE 0
                    END as days_to_expiry,
                    c.contract_value,
                    c.state,
                    c.contract_manager_id
                FROM contract_management c
                LEFT JOIN contract_management_type t ON t.id = c.contract_type_id
                LEFT JOIN (
                    SELECT rel.contract_id, string_agg(classification.name::text, ', ') AS names
                    FROM contract_classification_rel rel
                    JOIN contract_management_classification classification ON classification.id = rel.classification_id
                    GROUP BY rel.contract_id
                ) cls ON cls.contract_id = c.id
                LEFT JOIN (
                    SELECT rel.contract_id, string_agg(category.name::text, ', ') AS names
                    FROM contract_category_rel rel
                    JOIN contract_management_category category ON category.id = rel.category_id
                    GROUP BY rel.contract_id
                ) cat ON cat.contract_id = c.id
                LEFT JOIN (
                    SELECT rel.contract_id, string_agg(department.name::text, ', ') AS names
                    FROM contract_department_rel rel
                    JOIN contract_management_department department ON department.id = rel.department_id
                    GROUP BY rel.contract_id
                ) dept ON dept.contract_id = c.id
            """
        else:
            # Simplified query without configuration joins (for initial install)
            query = """
                SELECT 
                    c.id as id,
                    c.id as contract_id,
                    c.contract_number,
                    c.name as contract_name,
                    c.partner_id,
                    c.contract_type_id,
                    NULL::text as contract_type_name,
                    NULL::text as classification_names,
                    NULL::text as category_names,
                    NULL::text as department_names,
                    c.effective_date,
                    c.expiry_date,
                    CASE 
                        WHEN c.expiry_date IS NOT NULL 
                        THEN (c.expiry_date - CURRENT_DATE)::integer
                        ELSE 0
                    END as days_to_expiry,
                    c.contract_value,
                    c.state,
                    c.contract_manager_id
                FROM contract_management c
            """
        
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (%s)
        """ % (self._table, query))


class ContractMilestoneReport(models.Model):
    _name = 'contract.milestone.report'
    _description = 'Contract Milestone Report'
    _auto = False

    milestone_id = fields.Many2one(
        'contract.milestone',
        string='Milestone'
    )
    
    contract_id = fields.Many2one(
        'contract.management',
        string='Contract'
    )
    
    milestone_name = fields.Char(
        string='Deliverable Name'
    )
    
    milestone_date = fields.Date(
        string='Deliverable Date'
    )
    
    status = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue')
    ], string='Status')
    
    payment_amount = fields.Monetary(
        string='Payment Amount',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency'
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    m.id as id,
                    m.id as milestone_id,
                    m.contract_id,
                    m.name as milestone_name,
                    m.milestone_date,
                    m.status,
                    m.payment_amount,
                    c.currency_id
                FROM contract_milestone m
                JOIN contract_management c ON m.contract_id = c.id
            )
        """ % (self._table,))


class ContractArchiveWizard(models.TransientModel):
    _name = 'contract.archive.wizard'
    _description = 'Contract Archive Wizard'

    contract_ids = fields.Many2many(
        'contract.management',
        string='Contracts to Archive'
    )
    
    archive_reason = fields.Selection([
        ('expired', 'Contract Expired'),
        ('terminated', 'Contract Terminated'),
        ('completed', 'Contract Completed'),
        ('other', 'Other')
    ], string='Archive Reason', required=True)
    
    archive_date = fields.Date(
        string='Archive Date',
        default=fields.Date.today,
        required=True
    )
    
    archive_notes = fields.Text(
        string='Archive Notes'
    )
    
    restrict_access = fields.Boolean(
        string='Restrict Access',
        default=True,
        help='If checked, only authorized users can access archived contracts'
    )

    def action_archive_contracts(self):
        """Archive the selected contracts"""
        for contract in self.contract_ids:
            contract.write({
                'state': 'archived',
                'notes': f"Archived: {self.archive_reason}. {self.archive_notes or ''}"
            })
            
            # Archive related documents
            if contract.contract_documents:
                contract.write({
                    'contract_documents': False,
                    'contract_document_name': False,
                    'contract_document_size': 0
                })
            
            if contract.additional_documents:
                contract.write({
                    'additional_documents': False,
                    'additional_document_name': False,
                    'additional_document_size': 0
                })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Contracts Archived',
                'message': f'{len(self.contract_ids)} contracts have been archived.',
                'type': 'success',
            }
        }