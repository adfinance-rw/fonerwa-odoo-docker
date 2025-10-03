from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrAppraisalConfig(models.Model):
    _name = "hr.appraisal.config"
    _description = "HR Appraisal Configuration"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # Auto-completion settings
    auto_complete_enabled = fields.Boolean(
        "Enable Auto-Completion",
        default=True,
        help="Enable automatic completion of expired objectives",
    )
    auto_complete_delay_days = fields.Integer(
        "Auto-Complete Delay (Days)",
        default=0,
        help="Number of days after end date to auto-complete objectives",
    )
    min_progress_for_auto_complete = fields.Float(
        "Minimum Progress for Auto-Complete (%)",
        default=80.0,
        help="Minimum progress required for auto-completion",
    )

    # Notification settings
    send_completion_notifications = fields.Boolean(
        "Send Completion Notifications", default=True
    )
    send_reminder_notifications = fields.Boolean(
        "Send Reminder Notifications", default=True
    )
    reminder_days_before = fields.Integer("Reminder Days Before Deadline", default=7)

    # Performance alert settings
    low_progress_threshold = fields.Float("Low Progress Threshold (%)", default=30.0)
    alert_days_before_deadline = fields.Integer(
        "Alert Days Before Deadline", default=14
    )

    # Cron job settings
    cron_frequency_hours = fields.Integer(
        "Cron Job Frequency (Hours)",
        default=24,
        help="How often to run auto-completion checks",
    )

    @api.constrains(
        "auto_complete_delay_days", "reminder_days_before", "alert_days_before_deadline"
    )
    def _check_positive_days(self):
        for record in self:
            if record.auto_complete_delay_days < 0:
                raise ValidationError("Auto-complete delay days cannot be negative.")
            if record.reminder_days_before < 0:
                raise ValidationError(
                    "Reminder days before deadline cannot be negative."
                )
            if record.alert_days_before_deadline < 0:
                raise ValidationError("Alert days before deadline cannot be negative.")

    @api.constrains("min_progress_for_auto_complete", "low_progress_threshold")
    def _check_progress_percentages(self):
        for record in self:
            if not 0 <= record.min_progress_for_auto_complete <= 100:
                raise ValidationError(
                    "Minimum progress for auto-complete must be between 0 and 100."
                )
            if not 0 <= record.low_progress_threshold <= 100:
                raise ValidationError(
                    "Low progress threshold must be between 0 and 100."
                )

    @api.constrains("cron_frequency_hours")
    def _check_cron_frequency(self):
        for record in self:
            if record.cron_frequency_hours < 1:
                raise ValidationError("Cron job frequency must be at least 1 hour.")

    @api.model
    def get_config(self, company_id=None):
        """Get configuration for a specific company or current company"""
        if not company_id:
            company_id = self.env.company.id

        config = self.search([("company_id", "=", company_id)], limit=1)
        if not config:
            # Create default configuration if none exists
            config = self.create(
                {
                    "company_id": company_id,
                    "auto_complete_enabled": True,
                    "auto_complete_delay_days": 0,
                    "min_progress_for_auto_complete": 80.0,
                    "send_completion_notifications": True,
                    "send_reminder_notifications": True,
                    "reminder_days_before": 7,
                    "low_progress_threshold": 30.0,
                    "alert_days_before_deadline": 14,
                    "cron_frequency_hours": 24,
                }
            )

        return config
