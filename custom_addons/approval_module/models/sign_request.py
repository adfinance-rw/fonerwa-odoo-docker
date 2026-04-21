# -*- coding: utf-8 -*-

from odoo import models, _

import logging
_logger = logging.getLogger(__name__)


class SignRequestItem(models.Model):
    _inherit = 'sign.request.item'

    def _get_user_signature(self, signature_type='sign_signature'):
        """Use the stamped signature (if available) when signing in the Sign app.

        The plain ``sign_signature`` is kept for memo-approval reports, while
        ``sign_signature_stamped`` (signature + company stamp) is used here.
        """
        self.ensure_one()
        if signature_type == 'sign_signature':
            sign_user = self.partner_id.user_ids[:1]
            if sign_user and sign_user.sign_signature_stamped:
                return sign_user.sign_signature_stamped
        return super()._get_user_signature(signature_type)


class SignRequest(models.Model):
    _inherit = 'sign.request'

    def action_open_reference_doc(self):
        """Open the linked record (e.g. approval request) in form view."""
        self.ensure_one()
        if not self.reference_doc or not self.reference_doc.exists():
            return None
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.reference_doc._name,
            'res_id': self.reference_doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def get_reference_doc_info(self):
        """Return reference_doc info for the frontend (model, id, name).

        Uses sudo() so that any signer (even without approval.request access)
        can see the link to the source document.
        """
        self.ensure_one()
        rec = self.sudo().reference_doc
        if not rec or not rec.exists():
            return {}
        return {
            'model': rec._name,
            'id': rec.id,
            'name': rec.display_name,
        }

    def _sign(self):
        super()._sign()
        self._attach_signed_document_to_approval()

    def _attach_signed_document_to_approval(self):
        """After signing completion, link the sign request to the checklist line,
        attach the completed signed document to the approval request, and
        optionally notify the request owner."""
        self.ensure_one()
        ChecklistLine = self.env['approval.checklist.line'].sudo()
        lines = ChecklistLine.search([
            ('sign_template_id', '=', self.template_id.id),
            ('sign_request_id', '=', False),
        ])
        if not lines:
            return

        for line in lines:
            line.sign_request_id = self.id
            request = line.request_id
            if not request:
                continue

            # Copy certificate first, then the signed document, so the
            # signed document gets the highest id and appears first in
            # the Files list (which is ordered by id descending).
            for att in self.completed_document_attachment_ids.sorted('id', reverse=True):
                att.sudo().copy({
                    'res_model': 'approval.request',
                    'res_id': request.id,
                })

            category = request.category_id
            if category and getattr(category, 'notify_owner_after_signing', False):
                owner = request.request_owner_id or request.create_uid
                if owner:
                    request.message_post(
                        body=_('The document "%(doc)s" has been fully signed and attached to this request.',
                               doc=line.name),
                        subject=_('Document Signed: %s') % request.name,
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment',
                        partner_ids=owner.partner_id.ids,
                    )
