from odoo import models, fields, api
from datetime import datetime, timedelta
import json


class HrAppraisalDashboard(models.TransientModel):
    _name = "hr.appraisal.dashboard"
    _description = "HR Appraisal Dashboard"

    # Filter fields
    department_id = fields.Many2one("hr.department", string="Department")
    employee_id = fields.Many2one("hr.employee", string="Employee")
    date_from = fields.Date(
        "From Date", default=lambda self: fields.Date.today() - timedelta(days=180)
    )
    date_to = fields.Date("To Date", default=fields.Date.today)

    # Dashboard data storage
    dashboard_data = fields.Text("Dashboard Data")
    
    # Computed fields for display
    total_employees = fields.Integer("Total Employees", compute="_compute_overview_metrics")
    total_goals = fields.Integer("Total Goals", compute="_compute_overview_metrics")
    completed_goals = fields.Integer("Completed Goals", compute="_compute_overview_metrics")
    in_progress_goals = fields.Integer("In Progress Goals", compute="_compute_overview_metrics")
    completion_rate = fields.Float("Completion Rate (%)", compute="_compute_overview_metrics")
    avg_score = fields.Float("Average Score", compute="_compute_overview_metrics")
    avg_progress = fields.Float("Average Progress (%)", compute="_compute_overview_metrics")
    
    # Department performance data
    department_performance_data = fields.Text("Department Performance Data", compute="_compute_department_data")
    top_performers_data = fields.Text("Top Performers Data", compute="_compute_top_performers")
    risk_analysis_data = fields.Text("Risk Analysis Data", compute="_compute_risk_analysis")
    performance_trends_data = fields.Text("Performance Trends Data", compute="_compute_trends")

    @api.model
    def create(self, vals):
        """Create dashboard view with initial data refresh"""
        record = super().create(vals)
        record._refresh_dashboard_data()
        return record

    def _refresh_dashboard_data(self):
        """Build and store dashboard data"""
        data = self._build_dashboard_data()
        self.dashboard_data = json.dumps(data)

    def _build_dashboard_data(self):
        """Build comprehensive dashboard data"""
        Goal = self.env["hr.appraisal.goal"]
        
        # Build domain for filtering
        domain = []
        if self.date_from:
            domain.append(("create_date", ">=", datetime.combine(self.date_from, datetime.min.time())))
        if self.date_to:
            domain.append(("create_date", "<=", datetime.combine(self.date_to, datetime.max.time())))
        if self.department_id:
            domain.append(("department_id", "=", self.department_id.id))
        if self.employee_id:
            domain.append(("employee_id", "=", self.employee_id.id))

        # Get goals
        goals = Goal.search(domain)
        if not goals and not (self.department_id or self.employee_id):
            # If no goals in date range, get all goals for better overview
            goals = Goal.search([])

        # Overview metrics
        overview_metrics = self._compute_overview_data(goals)
        
        # Department performance
        department_performance = self._compute_department_performance(goals)
        
        # Top performers
        top_performers = self._compute_top_performers_data(goals)
        
        # Risk analysis
        risk_analysis = self._compute_risk_analysis_data(goals)
        

        return {
            "overview_metrics": overview_metrics,
            "department_performance": department_performance,
            "top_performers": top_performers,
            "risk_analysis": risk_analysis
        }

    def _compute_overview_data(self, goals):
        """Compute overview metrics"""
        if not goals:
            return {
                "total_employees": 0,
                "total_goals": 0,
                "completed_goals": 0,
                "in_progress_goals": 0,
                "completion_rate": 0.0,
                "avg_score": 0.0,
                "avg_progress": 0.0,
            }

        employees = goals.mapped("employee_id")
        completed_goals = goals.filtered(lambda g: g.state == "final")
        in_progress_goals = goals.filtered(lambda g: g.state == "progress")
        
        # Calculate averages
        scored_goals = goals.filtered(lambda g: g.final_score > 0)
        avg_score = sum(scored_goals.mapped("final_score")) / len(scored_goals) if scored_goals else 0.0
        
        progressed_goals = goals.filtered(lambda g: g.progression > 0)
        avg_progress = sum(progressed_goals.mapped("progression")) / len(progressed_goals) if progressed_goals else 0.0
        
        completion_rate = (len(completed_goals) / len(goals) * 100) if goals else 0.0

        return {
            "total_employees": len(employees),
            "total_goals": len(goals),
            "completed_goals": len(completed_goals),
            "in_progress_goals": len(in_progress_goals),
            "completion_rate": round(completion_rate, 2),
            "avg_score": round(avg_score, 2),
            "avg_progress": round(avg_progress, 2),
        }

    def _compute_department_performance(self, goals):
        """Compute department performance data"""
        dept_data = {}
        
        for goal in goals:
            dept = goal.department_id
            if not dept:
                continue
                
            dept_key = dept.id
            if dept_key not in dept_data:
                dept_data[dept_key] = {
                    "department_name": dept.name,
                    "total_goals": 0,
                    "completed_goals": 0,
                    "avg_progress": 0.0,
                    "avg_score": 0.0,
                    "employee_count": 0,
                    "progress_sum": 0.0,
                    "score_sum": 0.0,
                    "score_count": 0,
                }
            
            dept_data[dept_key]["total_goals"] += 1
            if goal.state == "final":
                dept_data[dept_key]["completed_goals"] += 1
            
            dept_data[dept_key]["progress_sum"] += goal.progression
            
            if goal.final_score > 0:
                dept_data[dept_key]["score_sum"] += goal.final_score
                dept_data[dept_key]["score_count"] += 1

        # Calculate averages and completion rates
        result = []
        for dept_key, data in dept_data.items():
            employees_in_dept = goals.filtered(lambda g: g.department_id.id == dept_key).mapped("employee_id")
            data["employee_count"] = len(employees_in_dept)
            data["completion_rate"] = round((data["completed_goals"] / data["total_goals"] * 100), 2) if data["total_goals"] else 0.0
            data["avg_progress"] = round((data["progress_sum"] / data["total_goals"]), 2) if data["total_goals"] else 0.0
            data["avg_score"] = round((data["score_sum"] / data["score_count"]), 2) if data["score_count"] else 0.0
            
            # Clean up helper fields
            data.pop("progress_sum", None)
            data.pop("score_sum", None)
            data.pop("score_count", None)
            
            result.append(data)

        return sorted(result, key=lambda x: x["completion_rate"], reverse=True)

    def _compute_top_performers_data(self, goals):
        """Compute top performers"""
        employee_data = {}
        
        for goal in goals:
            employee = goal.employee_id
            if not employee:
                continue
                
            emp_key = employee.id
            if emp_key not in employee_data:
                employee_data[emp_key] = {
                    "employee_name": employee.name,
                    "department": employee.department_id.name if employee.department_id else "N/A",
                    "total_goals": 0,
                    "completed_goals": 0,
                    "avg_progress": 0.0,
                    "avg_score": 0.0,
                    "progress_sum": 0.0,
                    "score_sum": 0.0,
                    "score_count": 0,
                }
            
            employee_data[emp_key]["total_goals"] += 1
            if goal.state == "final":
                employee_data[emp_key]["completed_goals"] += 1
            
            employee_data[emp_key]["progress_sum"] += goal.progression
            
            if goal.final_score > 0:
                employee_data[emp_key]["score_sum"] += goal.final_score
                employee_data[emp_key]["score_count"] += 1

        # Calculate metrics and get top performers
        result = []
        for emp_key, data in employee_data.items():
            data["completion_rate"] = round((data["completed_goals"] / data["total_goals"] * 100), 2) if data["total_goals"] else 0.0
            data["avg_progress"] = round((data["progress_sum"] / data["total_goals"]), 2) if data["total_goals"] else 0.0
            data["avg_score"] = round((data["score_sum"] / data["score_count"]), 2) if data["score_count"] else 0.0
            
            # Calculate performance index (weighted combination of metrics)
            performance_index = (data["avg_score"] * 0.4) + (data["avg_progress"] * 0.3) + (data["completion_rate"] * 0.3)
            data["performance_index"] = round(performance_index, 2)
            
            # Clean up helper fields
            data.pop("progress_sum", None)
            data.pop("score_sum", None)
            data.pop("score_count", None)
            
            result.append(data)

        # Return top 10 performers
        return sorted(result, key=lambda x: x["performance_index"], reverse=True)[:10]

    def _compute_risk_analysis_data(self, goals):
        """Compute risk analysis - employees/goals at risk"""
        risk_goals = []
        
        for goal in goals:
            risk_factors = []
            risk_score = 0
            
            # Check overdue goals
            if goal.deadline and goal.deadline < fields.Date.today() and goal.state not in ["final"]:
                risk_factors.append("Overdue")
                risk_score += 3
            
            # Check low progress
            if goal.progression < 25 and goal.state in ["progress", "self_scored"]:
                risk_factors.append("Low Progress")
                risk_score += 2
            
            # Check goals near deadline with low progress
            if goal.deadline:
                days_to_deadline = (goal.deadline - fields.Date.today()).days
                if days_to_deadline <= 30 and goal.progression < 75:
                    risk_factors.append("Near Deadline")
                    risk_score += 2
            
            if risk_factors:
                risk_goals.append({
                    "employee_name": goal.employee_id.name if goal.employee_id else "Unknown",
                    "goal_name": goal.name,
                    "department": goal.department_id.name if goal.department_id else "N/A",
                    "risk_factors": risk_factors,
                    "risk_score": risk_score,
                    "progression": goal.progression,
                    "deadline": goal.deadline.strftime("%Y-%m-%d") if goal.deadline else "No deadline",
                    "state": goal.state,
                })

        # Sort by risk score (highest risk first)
        return sorted(risk_goals, key=lambda x: x["risk_score"], reverse=True)

    def _compute_goal_creation_trends(self, goals):
        """Fallback trend computation based on goal creation"""
        monthly_data = {}
        
        for goal in goals:
            if not goal.create_date:
                continue
                
            month_key = goal.create_date.strftime("%Y-%m")
            month_label = goal.create_date.strftime("%b %Y")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "period": month_label,
                    "goals_created": 0,
                    "avg_progress": 0.0,
                    "progress_sum": 0.0,
                }
            
            monthly_data[month_key]["goals_created"] += 1
            monthly_data[month_key]["progress_sum"] += goal.progression

        # Calculate averages
        result = []
        for month_key, data in monthly_data.items():
            if data["goals_created"] > 0:
                data["avg_progress"] = round(data["progress_sum"] / data["goals_created"], 2)
            data.pop("progress_sum")
            result.append(data)

        return sorted(result, key=lambda x: x["period"])[-6:]  # Last 6 months

    def action_refresh_dashboard(self):
        """Refresh dashboard data"""
        self.ensure_one()
        self._refresh_dashboard_data()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": "Dashboard data refreshed successfully!",
                "type": "success",
                "sticky": False,
            },
        }

    def get_dashboard_data(self):
        """Get parsed dashboard data"""
        if self.dashboard_data:
            try:
                return json.loads(self.dashboard_data)
            except json.JSONDecodeError:
                return {}
        return {}

    @api.depends("dashboard_data")
    def _compute_overview_metrics(self):
        """Compute overview metrics for display"""
        for record in self:
            try:
                data = record.get_dashboard_data()
                overview = data.get("overview_metrics", {})
                record.total_employees = overview.get("total_employees", 0)
                record.total_goals = overview.get("total_goals", 0)
                record.completed_goals = overview.get("completed_goals", 0)
                record.in_progress_goals = overview.get("in_progress_goals", 0)
                record.completion_rate = overview.get("completion_rate", 0.0)
                record.avg_score = overview.get("avg_score", 0.0)
                record.avg_progress = overview.get("avg_progress", 0.0)
            except Exception:
                record.total_employees = 0
                record.total_goals = 0
                record.completed_goals = 0
                record.in_progress_goals = 0
                record.completion_rate = 0.0
                record.avg_score = 0.0
                record.avg_progress = 0.0

    @api.depends("dashboard_data")
    def _compute_department_data(self):
        """Compute department performance data"""
        for record in self:
            data = record.get_dashboard_data()
            dept_data = data.get("department_performance", [])
            record.department_performance_data = json.dumps(dept_data)

    @api.depends("dashboard_data")
    def _compute_top_performers(self):
        """Compute top performers data"""
        for record in self:
            data = record.get_dashboard_data()
            performers_data = data.get("top_performers", [])
            record.top_performers_data = json.dumps(performers_data)

    @api.depends("dashboard_data")
    def _compute_risk_analysis(self):
        """Compute risk analysis data"""
        for record in self:
            data = record.get_dashboard_data()
            risk_data = data.get("risk_analysis", [])
            record.risk_analysis_data = json.dumps(risk_data)

    @api.depends("dashboard_data")
    def _compute_trends(self):
        """Compute performance trends data"""
        for record in self:
            data = record.get_dashboard_data()
            trends_data = data.get("performance_trends", [])
            record.performance_trends_data = json.dumps(trends_data)

    def action_export_pdf(self):
        """Export dashboard as PDF"""
        return {
            "type": "ir.actions.report",
            "report_name": "hr_appraisal_objectives.performance_report",
            "report_type": "qweb-pdf",
            "data": {
                "report_type": "dashboard",
                "date_from": self.date_from,
                "date_to": self.date_to,
                "dashboard_data": self.get_dashboard_data(),
            },
            "context": self.env.context,
        }

    def action_export_excel(self):
        """Export dashboard data as Excel"""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Export Feature",
                "message": "Excel export feature will be implemented in the next version.",
                "type": "info",
                "sticky": False,
            },
        }