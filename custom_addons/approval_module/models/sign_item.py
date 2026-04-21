# -*- coding: utf-8 -*-

from odoo import fields, models


class SignItem(models.Model):
    _inherit = 'sign.item'

    letter_sequence_value = fields.Char(
        string='Letter Sequence Value',
        copy=False,
        help='Unique memo-wide sequence assigned to this Letter Sequence placeholder.',
    )
