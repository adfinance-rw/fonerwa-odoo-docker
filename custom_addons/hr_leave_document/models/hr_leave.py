# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    document_required = fields.Boolean(
        string='Document Required',
        compute='_compute_document_required',
        store=False,
        help='Indicates if a supporting document is mandatory for this leave request.')

    @api.depends('holiday_status_id', 'number_of_days')
    def _compute_document_required(self):
        for leave in self:
            leave_type = leave.holiday_status_id
            if not leave_type:
                leave.document_required = False
                continue

            if leave_type.document_requirement == 'always':
                leave.document_required = True
            elif leave_type.document_requirement == 'conditional':
                leave.document_required = (leave.number_of_days or 0) > leave_type.document_required_days
            else:
                leave.document_required = False

    def _needs_document(self, leave_type, number_of_days):
        """Check if a leave type requires a supporting document"""
        if not leave_type or leave_type.document_requirement == 'no':
            return False
        if leave_type.document_requirement == 'always':
            return True
        if leave_type.document_requirement == 'conditional':
            return (number_of_days or 0) > leave_type.document_required_days
        return False

    def _get_days_from_vals(self, vals):
        """Calculate number of days from date fields in vals"""
        date_from = vals.get('request_date_from') or vals.get('date_from')
        date_to = vals.get('request_date_to') or vals.get('date_to')
        if date_from and date_to:
            if isinstance(date_from, str):
                date_from = fields.Date.from_string(date_from[:10])
            if isinstance(date_to, str):
                date_to = fields.Date.from_string(date_to[:10])
            return (date_to - date_from).days + 1
        return 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            holiday_status_id = vals.get('holiday_status_id')
            if holiday_status_id:
                leave_type = self.env['hr.leave.type'].browse(holiday_status_id)
                has_attachment = bool(vals.get('supported_attachment_ids'))
                # Calculate days from the date fields in vals
                number_of_days = self._get_days_from_vals(vals)
                if self._needs_document(leave_type, number_of_days) and not has_attachment:
                    if leave_type.document_requirement == 'conditional':
                        raise ValidationError(
                            _('A supporting document is required for "%s" when the duration exceeds %d days.')
                            % (leave_type.name, leave_type.document_required_days)
                        )
                    else:
                        raise ValidationError(
                            _('A supporting document is required for "%s".')
                            % leave_type.name
                        )
        return super().create(vals_list)
