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
        Returns True if user has access, False otherwise.
        """
        if not request_id:
            return False
        
        # Try to read the request with current user's rights
        # This will apply the approval request record rules
        try:
            request = self.env['approval.request'].browse(request_id)
            # Try to access a field - this will trigger access checks
            request.check_access_rights('read')
            request.check_access_rule('read')
            # If we get here, user has access
            return True
        except AccessError:
            return False
        except Exception as e:
            _logger.warning(f"Error checking approval request access for request {request_id}: {e}")
            return False

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Override search to filter approval.request attachments based on accessible requests.
        """
        # First get all attachments matching the domain
        ids = super(IrAttachment, self)._search(
            domain, offset=offset, limit=limit, order=order
        )
        
        # If this is a superuser search, return as-is
        if self.env.su:
            return ids
        
        # Get the actual attachment records
        if isinstance(ids, list):
            attachments = self.sudo().browse(ids)  # Use sudo to read attachment metadata
        else:
            # ids might be a Query object or integer in some cases
            return ids
        
        # Filter out approval request attachments the user doesn't have access to
        approval_attachments = attachments.filtered(
            lambda a: a.res_model == 'approval.request' and a.res_id
        )
        
        if approval_attachments:
            # Check each request individually for access
            accessible_attachment_ids = []
            for attachment in approval_attachments:
                if self._check_approval_request_access(attachment.res_id):
                    accessible_attachment_ids.append(attachment.id)
            
            # Get non-approval attachments
            other_attachment_ids = (attachments - approval_attachments).ids
            
            # Combine accessible approval attachments with other attachments
            result = accessible_attachment_ids + other_attachment_ids
            return result
        
        return ids

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

