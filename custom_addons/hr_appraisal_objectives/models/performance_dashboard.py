from odoo import models, fields, api
import json


class PerformanceDashboard(models.TransientModel):
    _name = "performance.dashboard"
    _description = "Performance Dashboard View"

    dashboard_data = fields.Text(string="Dashboard Data", readonly=True)
    report_type = fields.Selection(
        [
            ("department", "Department Performance"),
            ("institutional", "Institutional Overview"),
            ("individual", "Individual Performance"),
            ("comparative", "Comparative Analysis"),
            ("dashboard", "Executive Dashboard"),
        ],
        string="Report Type",
        readonly=True,
    )
    date_from = fields.Date("From Date", readonly=True)
    date_to = fields.Date("To Date", readonly=True)

    # Additional fields for data storage
    overview_metrics = fields.Text(string="Overview Metrics", readonly=True)
    department_performance = fields.Text(string="Department Performance", readonly=True)
    top_performers = fields.Text(string="Top Performers", readonly=True)
    performance_trends = fields.Text(string="Performance Trends", readonly=True)
    risk_analysis = fields.Text(string="Risk Analysis", readonly=True)
    completion_forecast = fields.Text(string="Completion Forecast", readonly=True)

    # Computed fields for dashboard display
    total_employees = fields.Integer(
        string="Total Employees", compute="_compute_overview_metrics"
    )
    completed_goals = fields.Integer(
        string="Completed Goals", compute="_compute_overview_metrics"
    )
    completion_rate = fields.Float(
        string="Completion Rate (%)", compute="_compute_overview_metrics"
    )
    avg_score = fields.Float(
        string="Average Score", compute="_compute_overview_metrics"
    )

    # Data fields for detailed information
    department_performance_data = fields.Text(
        string="Department Performance Data", compute="_compute_department_data"
    )
    top_performers_data = fields.Text(
        string="Top Performers Data", compute="_compute_top_performers"
    )
    risk_analysis_data = fields.Text(
        string="Risk Analysis Data", compute="_compute_risk_analysis"
    )
    performance_trends_data = fields.Text(
        string="Performance Trends Data", compute="_compute_trends"
    )
    completion_forecast_data = fields.Text(
        string="Completion Forecast Data", compute="_compute_forecast"
    )

    @api.model
    def create(self, vals):
        """Parse dashboard data and store specific sections"""
        if "dashboard_data" in vals and vals["dashboard_data"]:
            try:
                data = json.loads(vals["dashboard_data"])
                # Store specific sections as separate fields
                vals["overview_metrics"] = json.dumps(data.get("overview_metrics", {}))
                vals["department_performance"] = json.dumps(
                    data.get("department_performance", [])
                )
                vals["top_performers"] = json.dumps(data.get("top_performers", []))
                vals["performance_trends"] = json.dumps(
                    data.get("performance_trends", [])
                )
                vals["risk_analysis"] = json.dumps(data.get("risk_analysis", []))
                vals["completion_forecast"] = json.dumps(
                    data.get("completion_forecast", {})
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return super().create(vals)

    def get_dashboard_data(self):
        """Get parsed dashboard data"""
        if self.dashboard_data:
            try:
                return json.loads(self.dashboard_data)
            except json.JSONDecodeError:
                return {}
        return {}

    def get_overview_metrics(self):
        """Get overview metrics data"""
        data = self.get_dashboard_data()
        return data.get("overview_metrics", {})

    def get_department_performance(self):
        """Get department performance data"""
        data = self.get_dashboard_data()
        return data.get("department_performance", [])

    def get_top_performers(self):
        """Get top performers data"""
        data = self.get_dashboard_data()
        return data.get("top_performers", [])

    def get_performance_trends(self):
        """Get performance trends data"""
        data = self.get_dashboard_data()
        return data.get("performance_trends", [])

    def get_risk_analysis(self):
        """Get risk analysis data"""
        data = self.get_dashboard_data()
        return data.get("risk_analysis", [])

    def get_completion_forecast(self):
        """Get completion forecast data"""
        data = self.get_dashboard_data()
        return data.get("completion_forecast", {})

    @api.depends("dashboard_data")
    def _compute_overview_metrics(self):
        """Compute overview metrics for display"""
        for record in self:
            try:
                overview = record.get_overview_metrics()
                record.total_employees = overview.get("total_employees", 0)
                record.completed_goals = overview.get("completed_goals", 0)
                record.completion_rate = overview.get("completion_rate", 0.0)
                record.avg_score = overview.get("avg_score", 0.0)
            except Exception:
                record.total_employees = 0
                record.completed_goals = 0
                record.completion_rate = 0.0
                record.avg_score = 0.0

    @api.depends("dashboard_data")
    def _compute_department_data(self):
        """Compute department performance data"""
        for record in self:
            try:
                dept_data = record.get_department_performance()
                record.department_performance_data = json.dumps(dept_data)
            except Exception:
                record.department_performance_data = json.dumps([])

    @api.depends("dashboard_data")
    def _compute_top_performers(self):
        """Compute top performers data"""
        for record in self:
            try:
                top_data = record.get_top_performers()
                record.top_performers_data = json.dumps(top_data)
            except Exception:
                record.top_performers_data = json.dumps([])

    @api.depends("dashboard_data")
    def _compute_risk_analysis(self):
        """Compute risk analysis data"""
        for record in self:
            try:
                risk_data = record.get_risk_analysis()
                record.risk_analysis_data = json.dumps(risk_data)
            except Exception:
                record.risk_analysis_data = json.dumps([])

    @api.depends("dashboard_data")
    def _compute_trends(self):
        """Compute performance trends data"""
        for record in self:
            try:
                trends_data = record.get_performance_trends()
                record.performance_trends_data = json.dumps(trends_data)
            except Exception:
                record.performance_trends_data = json.dumps([])

    @api.depends("dashboard_data")
    def _compute_forecast(self):
        """Compute completion forecast data"""
        for record in self:
            try:
                forecast_data = record.get_completion_forecast()
                record.completion_forecast_data = json.dumps(forecast_data)
            except Exception:
                record.completion_forecast_data = json.dumps({})

    def action_export_pdf(self):
        """Export dashboard data as PDF report"""
        # Create a temporary wizard to generate the PDF
        wizard = self.env["performance.report.wizard"].create(
            {
                "report_type": self.report_type or "dashboard",
                "date_from": self.date_from,
                "date_to": self.date_to,
                "include_charts": True,
                "include_details": True,
                "include_trends": True,
                "include_recommendations": True,
            }
        )

        return wizard.action_generate_report()

    def action_export_excel(self):
        """Export dashboard data as Excel (placeholder for future implementation)"""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": "Excel export feature will be implemented in a future update.",
                "type": "info",
                "sticky": False,
            },
        }
