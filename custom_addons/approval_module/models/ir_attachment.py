# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _check_approval_request_access(self, request_id):
        """
        Check if current user has access to a specific approval request.
        Returns True if the user can read the related approval.request record
        (owner, approver, optional approver, etc.).
        """
        if not self.env.user._is_internal():
            return False
        try:
            self.env['approval.request'].browse(request_id).check_access_rule('read')
            return True
        except AccessError:
            return False

    def validate_access(self, access_token):
        """Allow internal users to download approval.request attachments they can access."""
        res = super().validate_access(access_token)
        # If already sudo (access token or public), no further check needed
        if res.env.su:
            return res
        # For internal users, grant sudo access to approval.request attachments
        # when they can read the related approval request
        record_sudo = self.sudo()
        if (self.env.user._is_internal()
                and record_sudo.res_model == 'approval.request'
                and record_sudo.res_id
                and self._check_approval_request_access(record_sudo.res_id)):
            return record_sudo
        return res

    def _requested_attachment_ids_from_domain(self, domain):
        """Extract attachment ids from a search domain when it is id-based (e.g. download by id)."""
        if not domain or not isinstance(domain, list):
            return []
        # domain is a list of (field, op, value) or ['|', ...]
        for i, item in enumerate(domain):
            if isinstance(item, (list, tuple)) and len(item) == 3:
                field, op, value = item
                if field == 'id':
                    if op == '=':
                        return [value] if isinstance(value, int) else []
                    if op == 'in' and isinstance(value, (list, tuple)):
                        return [k for k in value if isinstance(k, int)]
        return []

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Override search so internal users can always see approval.request attachments.
        Base (or other) record rules may hide them; we add those ids back when the
        search is by id and the attachment belongs to an approval request.
        """
        ids = super(IrAttachment, self)._search(
            domain, offset=offset, limit=limit, order=order
        )
        if self.env.su:
            return ids

        requested_ids = self._requested_attachment_ids_from_domain(domain)
        if not requested_ids or not self.env.user.has_group('base.group_user'):
            return ids

        result_ids = list(ids) if isinstance(ids, list) else (getattr(ids, 'ids', None) or list(ids))
        missing_ids = [i for i in requested_ids if i not in result_ids]
        if not missing_ids:
            return ids

        original_len = len(result_ids)
        for att_id in missing_ids:
            att = self.sudo().browse(att_id)
            if (
                att.exists()
                and att.res_model == 'approval.request'
                and att.res_id
            ):
                result_ids.append(att_id)

        return result_ids if len(result_ids) > original_len else ids

    def read(self, fields=None, load='_classic_read'):
        """
        Override read to check access to approval request attachments.
        """
        # Check if user can access approval request attachments
        if not self.env.su:
            # Use sudo to read attachment metadata without triggering access errors
            approval_attachments = self.sudo().filtered(
                lambda a: a.res_model == 'approval.request' and a.res_id
            )
            
            if approval_attachments:
                # Check each approval attachment for access
                for attachment in approval_attachments:
                    if not self._check_approval_request_access(attachment.res_id):
                        raise AccessError(
                            _("You don't have access to attachment '%s' because you don't have "
                              "access to the related approval request.") % (attachment.name or 'Unknown')
                        )
        
        return super(IrAttachment, self).read(fields=fields, load=load)

