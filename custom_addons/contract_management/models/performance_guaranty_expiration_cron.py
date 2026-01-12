# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PerformanceGuarantyExpirationCron(models.Model):
    """
    Separate model for performance guaranty expiration cron job functionality.
    This keeps the cron job logic separate from the main performance guaranty model.
    """
    _name = 'performance.guaranty.expiration.cron'
    _description = 'Performance Guaranty Expiration Cron Job'
    _auto = False  # This is a virtual model, no database table needed

    @api.model
    def cron_check_expiring_performance_guaranties(self):
        """
        Cron job method to check for performance guaranties that are about to expire
        and send email notifications based on alert_days_before setting.
        
        This method:
        1. Finds all active performance guaranties
        2. Checks if guaranty is within alert period (days_to_expiry <= alert_days_before)
        3. Checks if alert hasn't been sent or was sent more than 1 minute ago
        4. Sends email notification if all conditions are met
        """
        today = fields.Date.today()
        _logger.info('Starting cron job: Checking for expiring performance guaranties')
        
        # Get the performance guaranty model
        PerformanceGuaranty = self.env['contract.performance.guaranty']
        
        # Find all active performance guaranties with expiry dates
        guaranties = PerformanceGuaranty.search([
            ('status', '=', 'active'),
            ('expiry_date', '!=', False),
            ('expiry_date', '>=', today),  # Not yet expired
        ])
        
        _logger.info(f'Found {len(guaranties)} active performance guaranties to check')
        
        sent_count = 0
        skipped_count = 0
        
        for guaranty in guaranties:
            try:
                # Calculate days to expiry
                days_to_expiry = (guaranty.expiry_date - today).days
                alert_days_before = guaranty.alert_days_before or 7
                
                # Check if guaranty is within alert period
                if days_to_expiry > alert_days_before:
                    _logger.debug(
                        f'Performance Guaranty {guaranty.name}: Outside alert period '
                        f'(Days to expiry: {days_to_expiry}, Alert days before: {alert_days_before})'
                    )
                    continue  # Too early to send notification
                
                # Check if alert was already sent in the last minute
                if guaranty.last_alert_date:
                    now_str = fields.Datetime.now()
                    now_dt = fields.Datetime.to_datetime(now_str)
                    last_alert_dt = fields.Datetime.to_datetime(guaranty.last_alert_date)
                    
                    if last_alert_dt and now_dt:
                        time_diff = (now_dt - last_alert_dt).total_seconds() / 60.0
                        # If email was sent less than 1 minute ago, skip to avoid duplicate
                        if time_diff < 1.0:
                            _logger.info(
                                f'Performance Guaranty {guaranty.name}: Alert sent {time_diff:.2f} minutes ago (< 1 minute), skipping'
                            )
                            skipped_count += 1
                            continue
                
                # Check if contract manager has email
                if not guaranty.contract_manager_id:
                    _logger.warning(
                        f'Performance Guaranty {guaranty.name}: No contract manager assigned - skipping'
                    )
                    skipped_count += 1
                    continue
                
                if not guaranty.contract_manager_id.email:
                    _logger.warning(
                        f'Performance Guaranty {guaranty.name}: Contract manager {guaranty.contract_manager_id.name} has no email address - skipping'
                    )
                    skipped_count += 1
                    continue
                
                # All conditions met - send notification
                _logger.info(
                    f'Performance Guaranty {guaranty.name}: Sending expiration notification '
                    f'(Days to expiry: {days_to_expiry}, Alert days before: {alert_days_before})'
                )
                
                result = guaranty.send_performance_guaranty_expiration_notification(force_send=True)
                
                if result:
                    sent_count += 1
                    _logger.info(
                        f'Performance Guaranty {guaranty.name}: Notification sent successfully'
                    )
                else:
                    _logger.error(
                        f'Performance Guaranty {guaranty.name}: Failed to send notification'
                    )
                    skipped_count += 1
                    
            except Exception as e:
                _logger.error(
                    f'Error processing performance guaranty {guaranty.name}: {str(e)}',
                    exc_info=True
                )
                skipped_count += 1
        
        _logger.info(
            f'Cron job completed: {sent_count} notifications sent, '
            f'{skipped_count} performance guaranties skipped'
        )
        
        return {
            'sent': sent_count,
            'skipped': skipped_count,
            'total_checked': len(guaranties)
        }

