from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class NotificationManager(models.Model):
    _name = "performance.notification"
    _description = "Performance Notification Manager"

    @api.model
    def send_deadline_reminders(self):
        """Automated method to send deadline reminders"""
        deadline_date = fields.Date.today() + timedelta(days=7)
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
            # Determine recipients: employee and/or department manager when available
            partner_ids = []
            user_ids = []

            # For individual goal
            if hasattr(record, 'employee_id') and record.employee_id and record.employee_id.user_id:
                user_ids.append(record.employee_id.user_id.id)
                partner_ids.append(record.employee_id.user_id.partner_id.id)

            # For department/inst objectives
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
                body=message,
                subject=title,
                partner_ids=list(set(partner_ids)),
                message_type='notification',
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
        low_progress_goals = self.env["hr.appraisal.goal"].search(
            [
                ("progression", "<", 30),
                ("deadline_days", "<", 14),
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
            # Recipients: employee and manager if available
            partner_ids = []
            user_ids = []
            if goal.employee_id and goal.employee_id.user_id:
                user_ids.append(goal.employee_id.user_id.id)
                partner_ids.append(goal.employee_id.user_id.partner_id.id)
            if goal.department_objective_id and goal.department_objective_id.department_id \
               and goal.department_objective_id.department_id.manager_id \
               and goal.department_objective_id.department_id.manager_id.user_id:
                user_ids.append(goal.department_objective_id.department_id.manager_id.user_id.id)
                partner_ids.append(goal.department_objective_id.department_id.manager_id.user_id.partner_id.id)

            title = 'Performance Alert'
            message = (
                f'Objective "{goal.name}" for {goal.employee_id.name} shows low progress '
                f'({goal.progression:.1f}%) with only {goal.deadline_days} day(s) left.'
            )

            # Chatter notification on the goal
            goal.sudo().message_post(
                body=message,
                subject=title,
                partner_ids=list(set(partner_ids)),
                message_type='notification',
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
                    self.env["bus.bus"]._sendone(
                        self.env.user.partner_id,
                        "objective_completed",
                        {
                            "title": "Institutional Objective Completed",
                            "message": f'Institutional objective "{obj.name}" has been automatically completed.',
                            "type": "success",
                        },
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
                    self.env["bus.bus"]._sendone(
                        self.env.user.partner_id,
                        "objective_completed",
                        {
                            "title": "Department Objective Completed",
                            "message": f'Department objective "{obj.name}" has been automatically completed.',
                            "type": "success",
                        },
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
                    if goal.employee_id.user_id:
                        self.env["bus.bus"]._sendone(
                            goal.employee_id.user_id.partner_id,
                            "objective_completed",
                            {
                                "title": "Individual Objective Completed",
                                "message": f'Your objective "{goal.name}" has been automatically completed.',
                                "type": "success",
                            },
                        )

                    # Notify manager if exists
                    if goal.department_objective_id.department_id.manager_id.user_id:
                        self.env["bus.bus"]._sendone(
                            goal.department_objective_id.department_id.manager_id.user_id.partner_id,
                            "objective_completed",
                            {
                                "title": "Team Objective Completed",
                                "message": f'Objective "{goal.name}" for {goal.employee_id.name} has been automatically completed.',
                                "type": "info",
                            },
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
                if config.send_completion_notifications and goal.employee_id.user_id:
                    self.env["bus.bus"]._sendone(
                        goal.employee_id.user_id.partner_id,
                        "objective_completed",
                        {
                            "title": "Objective Auto-Completed",
                            "message": f'Your objective "{goal.name}" has been automatically completed due to high progress ({goal.progression:.1f}%).',
                            "type": "success",
                        },
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
