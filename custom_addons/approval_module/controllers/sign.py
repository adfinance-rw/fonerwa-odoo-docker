# -*- coding: utf-8 -*-

from odoo.addons.sign.controllers.main import Sign
from odoo import http

import logging
_logger = logging.getLogger(__name__)


class SignApproval(Sign):

    @http.route(["/sign/get_document/<int:request_id>/<token>"], type='json', auth='user')
    def get_document(self, request_id, token):
        _logger.info("[RGF-SIGN] get_document called — request_id=%s, token=%s...", request_id, token[:8] if token else None)
        result = super().get_document(request_id, token)
        if not isinstance(result, dict) or 'context' not in result:
            return result
        return result

    @http.route(["/sign/reference_doc_info/<int:request_id>"], type='json', auth='user')
    def get_reference_doc_info(self, request_id):
        """Dedicated endpoint to fetch reference doc info for a sign request."""
        sign_request = http.request.env['sign.request'].sudo().browse(request_id)
        if sign_request.exists() and sign_request.reference_doc:
            ref = sign_request.reference_doc
            if ref.exists():
                return {
                    'model': ref._name,
                    'id': ref.id,
                    'name': ref.display_name,
                }
        return {}

    def get_document_qweb_context(self, sign_request_id, token, **post):
        _logger.info("[RGF-SIGN] get_document_qweb_context called — sign_request_id=%s", sign_request_id)
        result = super().get_document_qweb_context(sign_request_id, token, **post)
        if not isinstance(result, dict):
            return result

        sign_request = result.get('sign_request')
        if not sign_request:
            return result

        # Trace back: sign_request.template_id → checklist line → approval request
        # This is more reliable than reference_doc which may not always be set.
        checklist_line = http.request.env['approval.checklist.line'].sudo().search([
            ('sign_template_id', '=', sign_request.template_id.id),
        ], limit=1)

        _logger.info("[RGF-SIGN] template_id=%s, checklist_line=%s, request_id=%s",
                     sign_request.template_id.id, checklist_line, checklist_line.request_id if checklist_line else None)

        if checklist_line and checklist_line.request_id:
            approval = checklist_line.request_id
            result['reference_doc_model'] = 'approval.request'
            result['reference_doc_id'] = approval.id
            result['reference_doc_name'] = approval.display_name
            _logger.info("[RGF-SIGN] Injected approval ref into QWeb context: id=%s, name=%s",
                         approval.id, approval.display_name)

            # Letter sequence injection
            letter_seq_type = http.request.env.ref(
                'approval_module.sign_item_type_letter_sequence',
                raise_if_not_found=False,
            )
            if letter_seq_type:
                sequence_map = checklist_line._ensure_template_letter_sequence_values()
                sequence_number = sequence_map and next(iter(sequence_map.values()), False)
                if not sequence_number:
                    sequence_number = checklist_line.letter_number
                if not sequence_number:
                    approval_name = approval.name or ''
                    sequence_number = approval_name.rsplit('-', 1)[-1] if '-' in approval_name else approval_name

                item_values = result.setdefault('item_values', {})
                for sign_item in sign_request.template_id.sign_item_ids.filtered(
                    lambda item: item.type_id == letter_seq_type
                ):
                    value = sequence_map.get(sign_item.id)
                    if value:
                        item_values[sign_item.id] = value

                sign_item_types = result.get('sign_item_types', [])
                for item_type in sign_item_types:
                    if item_type['id'] == letter_seq_type.id:
                        item_type['auto_value'] = sequence_number
                        break
        else:
            # Fallback: try reference_doc field
            _logger.info("[RGF-SIGN] No checklist_line found, trying reference_doc field. value=%s",
                         sign_request.reference_doc)
            if sign_request.reference_doc:
                ref = sign_request.sudo().reference_doc
                if ref.exists():
                    result['reference_doc_model'] = ref._name
                    result['reference_doc_id'] = ref.id
                    result['reference_doc_name'] = ref.display_name
                    _logger.info("[RGF-SIGN] Injected reference_doc into QWeb context: %s,%s", ref._name, ref.id)

        return result
