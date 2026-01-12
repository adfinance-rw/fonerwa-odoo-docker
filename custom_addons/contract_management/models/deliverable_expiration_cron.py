# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class DeliverableExpirationCron(models.Model):
    """
    Separate model for deliverable expiration cron job functionality.
    This keeps the cron job logic separate from the main deliverable model.
    """
    _name = 'deliverable.expiration.cron'
    _description = 'Deliverable Expiration Cron Job'
    _auto = False  # This is a virtual model, no database table needed

    @api.model
    def cron_check_expiring_deliverables(self):
        """
        Cron job method to check for deliverables that are about to expire
        and send email notifications based on alert_days_before setting.
        
        This method:
        1. Finds all pending deliverables
        2. Checks if deliverable is within alert period (days_until_due <= alert_days_before)
        3. Checks if alert hasn't been sent or was sent more than 1 minute ago
        4. Sends email notification if all conditions are met
        """
        today = fields.Date.today()
        _logger.info('Starting cron job: Checking for expiring deliverables')
        
        # Get the deliverable model
        Deliverable = self.env['contract.deliverable']
        
        # Find all pending deliverables with due dates
        deliverables = Deliverable.search([
            ('status', '=', 'pending'),
            ('deliverable_date', '!=', False),
            ('deliverable_date', '>=', today),  # Not yet overdue
        ])
        
        _logger.info(f'Found {len(deliverables)} pending deliverables to check')
        
        sent_count = 0
        skipped_count = 0
        
        for deliverable in deliverables:
            try:
                # Calculate days until due
                days_until_due = (deliverable.deliverable_date - today).days
                alert_days_before = deliverable.alert_days_before or 7
                
                # Check if deliverable is within alert period
                if days_until_due > alert_days_before:
                    _logger.debug(
                        f'Deliverable {deliverable.name}: Outside alert period '
                        f'(Days until due: {days_until_due}, Alert days before: {alert_days_before})'
                    )
                    continue  # Too early to send notification
                
                # Check if alert was already sent in the last minute
                if deliverable.last_alert_date:
                    now_str = fields.Datetime.now()
                    now_dt = fields.Datetime.to_datetime(now_str)
                    last_alert_dt = fields.Datetime.to_datetime(deliverable.last_alert_date)
                    
                    if last_alert_dt and now_dt:
                        time_diff = (now_dt - last_alert_dt).total_seconds() / 60.0
                        # If email was sent less than 1 minute ago, skip to avoid duplicate
                        if time_diff < 1.0:
                            _logger.info(
                                f'Deliverable {deliverable.name}: Alert sent {time_diff:.2f} minutes ago (< 1 minute), skipping'
                            )
                            skipped_count += 1
                            continue
                
                # Check if contract manager has email
                assigned_user = (
                    deliverable.contract_manager_id
                    or deliverable.contract_id.contract_manager_id
                )
                
                if not assigned_user:
                    _logger.warning(
                        f'Deliverable {deliverable.name}: No contract manager assigned - skipping'
                    )
                    skipped_count += 1
                    continue
                
                if not assigned_user.email:
                    _logger.warning(
                        f'Deliverable {deliverable.name}: Contract manager {assigned_user.name} has no email address - skipping'
                    )
                    skipped_count += 1
                    continue
                
                # All conditions met - send notification
                _logger.info(
                    f'Deliverable {deliverable.name}: Sending expiration notification '
                    f'(Days until due: {days_until_due}, Alert days before: {alert_days_before})'
                )
                
                result = deliverable.send_deliverable_expiration_notification(force_send=True)
                
                if result:
                    sent_count += 1
                    _logger.info(
                        f'Deliverable {deliverable.name}: Notification sent successfully'
                    )
                else:
                    _logger.error(
                        f'Deliverable {deliverable.name}: Failed to send notification'
                    )
                    skipped_count += 1
                    
            except Exception as e:
                _logger.error(
                    f'Error processing deliverable {deliverable.name}: {str(e)}',
                    exc_info=True
                )
                skipped_count += 1
        
        _logger.info(
            f'Cron job completed: {sent_count} notifications sent, '
            f'{skipped_count} deliverables skipped'
        )
        
        return {
            'sent': sent_count,
            'skipped': skipped_count,
            'total_checked': len(deliverables)
        }

