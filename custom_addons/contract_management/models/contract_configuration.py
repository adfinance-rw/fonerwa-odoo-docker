
from odoo import models, fields


class ContractConfigurationMixin(models.AbstractModel):
    _name = 'contract.configuration.mixin'
    _description = 'Contract Configuration Mixin'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    description = fields.Text()
    active = fields.Boolean(default=True)


class ContractManagementType(models.Model):
    _name = 'contract.management.type'
    _inherit = 'contract.configuration.mixin'
    _description = 'Contract Type'

    _sql_constraints = [
        ('contract_type_name_unique', 'unique(name)', 'Contract type must be unique.'),
        ('contract_type_code_unique', 'unique(code)', 'Contract type code must be unique.')
    ]


class ContractManagementClassification(models.Model):
    _name = 'contract.management.classification'
    _inherit = 'contract.configuration.mixin'
    _description = 'Contract Classification'

    contract_type_ids = fields.Many2many(
        'contract.management.type',
        'contract_type_classification_rel',
        'classification_id',
        'type_id',
        string='Contract Types',
        help='Contract types that can use this classification'
    )

    _sql_constraints = [
        ('contract_classification_name_unique', 'unique(name)', 'Classification must be unique.'),
        ('contract_classification_code_unique', 'unique(code)', 'Classification code must be unique.')
    ]


class ContractManagementCategory(models.Model):
    _name = 'contract.management.category'
    _inherit = 'contract.configuration.mixin'
    _description = 'Contract Category'

    contract_type_ids = fields.Many2many(
        'contract.management.type',
        'contract_type_category_rel',
        'category_id',
        'type_id',
        string='Contract Types',
        help='Contract types that can use this category'
    )

    _sql_constraints = [
        ('contract_category_name_unique', 'unique(name)', 'Category must be unique.'),
        ('contract_category_code_unique', 'unique(code)', 'Category code must be unique.')
    ]


class ContractManagementDepartment(models.Model):
    _name = 'contract.management.department'
    _inherit = 'contract.configuration.mixin'
    _description = 'Contract Department'

    contract_type_ids = fields.Many2many(
        'contract.management.type',
        'contract_type_department_rel',
        'department_id',
        'type_id',
        string='Contract Types',
        help='Contract types that can use this department'
    )

    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible',
        help='Default responsible user for this department.'
    )

    _sql_constraints = [
        ('contract_department_name_unique', 'unique(name)', 'Department must be unique.'),
        ('contract_department_code_unique', 'unique(code)', 'Department code must be unique.')
    ]
