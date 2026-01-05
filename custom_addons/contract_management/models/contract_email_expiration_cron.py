# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ContractEmailExpirationCron(models.Model):
    """
    Separate model for contract expiration cron job functionality.
    This keeps the cron job logic separate from the main contract model.
    """
    _name = 'contract.expiration.cron'
    _description = 'Contract Expiration Cron Job'
    _auto = False  # This is a virtual model, no database table needed

    @api.model
    def cron_check_expiring_contracts(self):
        """
        Cron job method to check for contracts that are about to expire
        and send email notifications.
        
        This method:
        1. Finds all active contracts
        2. Checks if contract is within notice period (days_to_expiry <= notice_period_days)
        3. Checks if recurring reminders are enabled
        4. Checks if notification hasn't been sent in the last minute
        5. Sends email notification if all conditions are met
        """
        today = fields.Date.today()
        _logger.info('Starting cron job: Checking for expiring contracts')
        
        # Get the contract model
        Contract = self.env['contract.management']
        
        # Find all active contracts with expiry dates
        contracts = Contract.search([
            ('state', '=', 'active'),
            ('expiry_date', '!=', False),
            ('expiry_date', '>=', today),  # Not yet expired
        ])
        
        _logger.info(f'Found {len(contracts)} active contracts to check')
        
        sent_count = 0
        skipped_count = 0
        
        for contract in contracts:
            try:
                # Calculate days to expiry
                days_to_expiry = (contract.expiry_date - today).days
                notice_period = contract.notice_period_days or 7
                
                # Check if contract is within notice period
                if days_to_expiry > notice_period:
                    _logger.debug(
                        f'Contract {contract.contract_number}: Outside notice period '
                        f'(Days to expiry: {days_to_expiry}, Notice period: {notice_period})'
                    )
                    continue  # Too early to send notification
                
                # Check if recurring reminders are enabled
                if not contract.send_recurring_reminders:
                    _logger.info(
                        f'Contract {contract.contract_number}: Recurring reminders disabled - skipping'
                    )
                    skipped_count += 1
                    continue
                
                # Check if notification was already sent in the last minute
                # This allows sending emails every minute if conditions match
                if contract.last_notification_date:
                    # Get current datetime
                    now_str = fields.Datetime.now()
                    now_dt = fields.Datetime.to_datetime(now_str)
                    last_notification_dt = fields.Datetime.to_datetime(contract.last_notification_date)
                    
                    # Calculate time difference in minutes
                    if last_notification_dt and now_dt:
                        time_diff = (now_dt - last_notification_dt).total_seconds() / 60.0
                        # If email was sent less than 1 minute ago, skip to avoid duplicate
                        if time_diff < 1.0:
                            _logger.info(
                                f'Contract {contract.contract_number}: Notification sent {time_diff:.2f} minutes ago (< 1 minute), skipping'
                            )
                            skipped_count += 1
                            continue
                
                # Check if contract manager has email
                if not contract.contract_manager_id:
                    _logger.warning(
                        f'Contract {contract.contract_number}: No contract manager assigned - skipping'
                    )
                    skipped_count += 1
                    continue
                
                if not contract.contract_manager_id.email:
                    _logger.warning(
                        f'Contract {contract.contract_number}: Contract manager {contract.contract_manager_id.name} has no email address - skipping'
                    )
                    skipped_count += 1
                    continue
                
                # All conditions met - send notification
                _logger.info(
                    f'Contract {contract.contract_number}: Sending expiration notification '
                    f'(Days to expiry: {days_to_expiry}, Notice period: {notice_period})'
                )
                
                result = contract.send_expiration_notification(force_send=True)
                
                if result:
                    sent_count += 1
                    _logger.info(
                        f'Contract {contract.contract_number}: Notification sent successfully'
                    )
                else:
                    _logger.error(
                        f'Contract {contract.contract_number}: Failed to send notification'
                    )
                    skipped_count += 1
                    
            except Exception as e:
                _logger.error(
                    f'Error processing contract {contract.contract_number}: {str(e)}',
                    exc_info=True
                )
                skipped_count += 1
        
        _logger.info(
            f'Cron job completed: {sent_count} notifications sent, '
            f'{skipped_count} contracts skipped'
        )
        
        return {
            'sent': sent_count,
            'skipped': skipped_count,
            'total_checked': len(contracts)
        }
