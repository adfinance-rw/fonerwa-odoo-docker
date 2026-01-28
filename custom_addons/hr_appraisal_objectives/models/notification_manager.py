from odoo import models, fields, api
from datetime import timedelta
import logging
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class NotificationManager(models.Model):
    _name = "performance.notification"
    _description = "Performance Notification Manager"

    def _send_email_notification(self, partner_ids, subject, body_html):
        """Helper method to send email notifications via mail.mail"""
        if not partner_ids:
            return
        
        try:
            partners = self.env['res.partner'].browse(partner_ids).filtered(lambda p: p.email)
            if not partners:
                _logger.warning(f"No valid email addresses found for partners {partner_ids}")
                return
            
            # Create mail.mail record
            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_to': ','.join(partners.mapped('email')),
                'partner_ids': [(6, 0, partners.ids)],
                'auto_delete': True,
            }
            
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            _logger.info(f"Sent email notification to {mail_values['email_to']}: {subject}")
        except Exception as e:
            _logger.warning(f"Failed to send email notification: {str(e)}")

    @api.model
    def send_deadline_reminders(self):
        """Automated method to send deadline reminders"""
        # Get configuration
        config = self.env["hr.appraisal.config"].get_config()
        
        # Check if reminder notifications are enabled
        if not config.send_reminder_notifications:
            return
        
        # Use configured reminder days before deadline
        deadline_date = fields.Date.today() + timedelta(days=config.reminder_days_before)
        inst_objectives = self.env["hr.institutional.objective"].search(
            [("end_date", "<=", deadline_date), ("state", "=", "active")]
        )
        for obj in inst_objectives:
            self._send_deadline_notification(obj, "institutional")
        goals = self.env["hr.appraisal.goal"].search(
            [("end_date", "<=", deadline_date), ("state", "in", ["scored"])]
        )
        for goal in goals:
            self._send_deadline_notification(goal, "individual")

    def _send_deadline_notification(self, record, obj_type):
        """Send deadline notification"""
        try:
            # Determine recipients: employee and/or line manager when available
            partner_ids = []
            user_ids = []

            # For individual goal: notify employee and their parent (line manager)
            if hasattr(record, 'employee_id') and record.employee_id and record.employee_id.user_id:
                user_ids.append(record.employee_id.user_id.id)
                partner_ids.append(record.employee_id.user_id.partner_id.id)
                if record.employee_id.parent_id and record.employee_id.parent_id.user_id and record.employee_id.parent_id.user_id.partner_id:
                    user_ids.append(record.employee_id.parent_id.user_id.id)
                    partner_ids.append(record.employee_id.parent_id.user_id.partner_id.id)

            # For department/inst objectives: keep department manager behaviour
            if hasattr(record, 'department_id') and record.department_id and record.department_id.manager_id and record.department_id.manager_id.user_id:
                user_ids.append(record.department_id.manager_id.user_id.id)
                partner_ids.append(record.department_id.manager_id.user_id.partner_id.id)

            # Post a chatter message on the record
            title_map = {
                'institutional': 'Institutional Objective Approaching Deadline',
                'department': 'Department Objective Approaching Deadline',
                'individual': 'Objective Approaching Deadline',
            }
            title = title_map.get(obj_type, 'Objective Approaching Deadline')
            message = f'"{getattr(record, "name", "Objective")}" is approaching its deadline on {getattr(record, "end_date", False)}.'

            record.sudo().message_post(
                body=Markup(f"<p><strong>{title}</strong></p><p>{message}</p>"),
                partner_ids=list(set(partner_ids)),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )

            # Schedule To Do activities for recipients
            for uid in set(user_ids):
                try:
                    record.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=fields.Date.today() + timedelta(days=3),
                        user_id=uid,
                        summary=title,
                        note=message,
                    )
                except Exception:
                    # Never block the flow on activity issues
                    continue
        except Exception as e:
            _logger.error(f"Failed to send deadline notification for {record}: {e}")

    @api.model
    def send_performance_alerts(self):
        """Send alerts for performance issues"""
        # Get configuration
        config = self.env["hr.appraisal.config"].get_config()
        
        # Use configured thresholds
        low_progress_goals = self.env["hr.appraisal.goal"].search(
            [
                ("progression", "<", config.low_progress_threshold),
                ("deadline_days", "<", config.alert_days_before_deadline),
                ("state", "in", ["scored"]),
            ]
        )
        for goal in low_progress_goals:
            self._send_performance_alert(goal)

    def _send_performance_alert(self, goal):
        """Send performance alert"""
        try:
            if not goal:
                return
            # Recipients: employee and line manager if available
            partner_ids = []
            user_ids = []
            if goal.employee_id and goal.employee_id.user_id:
                user_ids.append(goal.employee_id.user_id.id)
                partner_ids.append(goal.employee_id.user_id.partner_id.id)
            if goal.employee_id and goal.employee_id.parent_id and goal.employee_id.parent_id.user_id:
                user_ids.append(goal.employee_id.parent_id.user_id.id)
                partner_ids.append(goal.employee_id.parent_id.user_id.partner_id.id)

            title = 'Performance Alert'
            message = (
                f'Objective "{goal.name}" for {goal.employee_id.name} shows low progress '
                f'({goal.progression:.1f}%) with only {goal.deadline_days} day(s) left.'
            )

            # Chatter notification on the goal (sends email if configured)
            goal.sudo().message_post(
                body=Markup(f"<p><strong>{title}</strong></p><p>{message}</p>"),
                partner_ids=list(set(partner_ids)),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )

            # Activities
            for uid in set(user_ids):
                try:
                    goal.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=fields.Date.today() + timedelta(days=2),
                        user_id=uid,
                        summary=title,
                        note=message,
                    )
                except Exception:
                    continue
        except Exception as e:
            _logger.error(f"Failed to send performance alert for goal {getattr(goal, 'id', '')}: {e}")

    @api.model
    def auto_complete_expired_objectives(self):
        """Automatically complete objectives when their end date has passed"""
        # Get configuration
        config = self.env["hr.appraisal.config"].get_config()

        if not config.auto_complete_enabled:
            return {"message": "Auto-completion is disabled"}

        today = fields.Date.today()
        completion_date = today - timedelta(days=config.auto_complete_delay_days)

        # Complete expired institutional objectives
        expired_inst_objectives = self.env["hr.institutional.objective"].search(
            [("end_date", "<", completion_date), ("state", "=", "active")]
        )

        for obj in expired_inst_objectives:
            try:
                obj.write({"state": "completed"})
                if config.send_completion_notifications:
                    # Send email notification
                    recipients = []
                    if hasattr(obj, 'department_id') and obj.department_id and obj.department_id.manager_id:
                        recipients.append(obj.department_id.manager_id.user_id.partner_id.id)
                    if recipients:
                        self._send_email_notification(
                            recipients,
                            f"Institutional Objective Completed: {obj.name}",
                            f"""<p>Dear Manager,</p>
                            <p>The institutional objective <strong>"{obj.name}"</strong> has been automatically completed.</p>
                            <p>End Date: {obj.end_date}</p>
                            <p>Please review the completion status.</p>"""
                        )
            except Exception as e:
                _logger.error(
                    f"Failed to complete institutional objective {obj.id}: {e}"
                )

        # Complete expired department objectives
        expired_dept_objectives = self.env["hr.department.objective"].search(
            [("end_date", "<", completion_date), ("state", "=", "active")]
        )

        for obj in expired_dept_objectives:
            try:
                obj.write({"state": "completed"})
                if config.send_completion_notifications:
                    # Send email notification
                    recipients = []
                    if obj.department_id and obj.department_id.manager_id and obj.department_id.manager_id.user_id:
                        recipients.append(obj.department_id.manager_id.user_id.partner_id.id)
                    if recipients:
                        self._send_email_notification(
                            recipients,
                            f"Department Objective Completed: {obj.name}",
                            f"""<p>Dear Manager,</p>
                            <p>The department objective <strong>"{obj.name}"</strong> has been automatically completed.</p>
                            <p>End Date: {obj.end_date}</p>
                            <p>Please review the completion status.</p>"""
                        )
            except Exception as e:
                _logger.error(f"Failed to complete department objective {obj.id}: {e}")

        # Complete expired individual objectives (appraisal goals)
        expired_goals = self.env["hr.appraisal.goal"].search(
            [
                ("end_date", "<", completion_date),
                ("state", "in", ["progress", "scored"]),
            ]
        )

        for goal in expired_goals:
            try:
                # If the goal has scores, finalize it; otherwise mark as completed
                if goal.final_score > 0:
                    goal.write({"state": "final"})
                else:
                    goal.write({"state": "final"})

                # Send notification to relevant users
                if config.send_completion_notifications:
                    recipients = []
                    # Notify employee
                    if goal.employee_id.user_id and goal.employee_id.user_id.partner_id:
                        recipients.append(goal.employee_id.user_id.partner_id.id)
                        self._send_email_notification(
                            [goal.employee_id.user_id.partner_id.id],
                            f"Objective Completed: {goal.name}",
                            f"""<p>Dear {goal.employee_id.name},</p>
                            <p>Your objective <strong>"{goal.name}"</strong> has been automatically completed.</p>
                            <p>End Date: {goal.end_date}</p>
                            <p>Final Score: {goal.final_score:.1f}%</p>
                            <p>Thank you for your work on this objective.</p>"""
                        )

                    # Notify line manager if exists
                    if goal.employee_id and goal.employee_id.parent_id and goal.employee_id.parent_id.user_id and goal.employee_id.parent_id.user_id.partner_id:
                        self._send_email_notification(
                            [goal.employee_id.parent_id.user_id.partner_id.id],
                            f"Team Objective Completed: {goal.name}",
                            f"""<p>Dear Manager,</p>
                            <p>The objective <strong>"{goal.name}"</strong> for {goal.employee_id.name} has been automatically completed.</p>
                            <p>End Date: {goal.end_date}</p>
                            <p>Final Score: {goal.final_score:.1f}%</p>
                            <p>Please review the completion status.</p>"""
                        )

            except Exception as e:
                _logger.error(f"Failed to complete individual goal {goal.id}: {e}")

        # Log completion summary
        total_completed = (
            len(expired_inst_objectives)
            + len(expired_dept_objectives)
            + len(expired_goals)
        )
        if total_completed > 0:
            _logger.info(f"Auto-completed {total_completed} expired objectives")

        return {
            "institutional_completed": len(expired_inst_objectives),
            "department_completed": len(expired_dept_objectives),
            "individual_completed": len(expired_goals),
            "total_completed": total_completed,
        }

    @api.model
    def auto_complete_with_conditions(self):
        """Auto-complete objectives with additional conditions"""
        # Get configuration
        config = self.env["hr.appraisal.config"].get_config()

        if not config.auto_complete_enabled:
            return {"message": "Auto-completion is disabled"}

        today = fields.Date.today()
        completion_date = today - timedelta(days=config.auto_complete_delay_days)

        # Complete objectives that are past end date AND have sufficient progress
        goals_with_progress = self.env["hr.appraisal.goal"].search(
            [
                ("end_date", "<", completion_date),
                ("state", "in", ["progress"]),
                ("progression", ">=", config.min_progress_for_auto_complete),
            ]
        )

        for goal in goals_with_progress:
            try:
                goal.write({"state": "final"})

                # Send notification
                if config.send_completion_notifications and goal.employee_id.user_id and goal.employee_id.user_id.partner_id:
                    self._send_email_notification(
                        [goal.employee_id.user_id.partner_id.id],
                        f"Objective Auto-Completed: {goal.name}",
                        f"""<p>Dear {goal.employee_id.name},</p>
                        <p>Your objective <strong>"{goal.name}"</strong> has been automatically completed due to high progress ({goal.progression:.1f}%).</p>
                        <p>End Date: {goal.end_date}</p>
                        <p>Progress: {goal.progression:.1f}%</p>
                        <p>Congratulations on achieving this milestone!</p>"""
                    )
            except Exception as e:
                _logger.error(f"Failed to auto-complete goal {goal.id}: {e}")

        return len(goals_with_progress)

    @api.model
    def manual_trigger_auto_completion(self):
        """Manual trigger for auto-completion (for testing purposes)"""
        try:
            result = self.auto_complete_expired_objectives()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Auto-Completion Results",
                    "message": f"Completed: {result.get('total_completed', 0)} objectives\n"
                    f"Institutional: {result.get('institutional_completed', 0)}\n"
                    f"Department: {result.get('department_completed', 0)}\n"
                    f"Individual: {result.get('individual_completed', 0)}",
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Auto-Completion Error",
                    "message": f"Error occurred: {str(e)}",
                    "type": "danger",
                    "sticky": False,
                },
            }
