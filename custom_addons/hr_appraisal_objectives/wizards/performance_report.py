from odoo import models, fields
from datetime import datetime, timedelta
import json


class PerformanceReportWizard(models.TransientModel):
    _name = "performance.report.wizard"
    _description = "Performance Report Generator"

    report_type = fields.Selection(
        [
            ("department", "Department Performance"),
            ("institutional", "Institutional Overview"),
            ("individual", "Individual Performance"),
            ("comparative", "Comparative Analysis"),
            ("dashboard", "Executive Dashboard"),
        ],
        string="Report Type",
        required=True,
        default="dashboard",
    )
    date_from = fields.Date(
        "From Date",
        required=True,
        default=lambda self: (datetime.now() - timedelta(days=90)).date(),
    )
    date_to = fields.Date("To Date", required=True, default=fields.Date.today)
    department_ids = fields.Many2many("hr.department", string="Departments")
    employee_ids = fields.Many2many("hr.employee", string="Employees")
    institutional_objective_ids = fields.Many2many(
        "hr.institutional.objective", string="Institutional Objectives"
    )
    include_charts = fields.Boolean("Include Charts", default=True)
    include_details = fields.Boolean("Include Detailed Breakdown", default=True)
    include_trends = fields.Boolean("Include Trend Analysis", default=True)
    include_recommendations = fields.Boolean("Include Recommendations", default=True)

    def action_generate_report(self):
        """Generate performance report based on selections"""
        data = self._prepare_report_data()
        return {
            "type": "ir.actions.report",
            "report_name": "hr_appraisal_objectives.performance_report",
            "report_type": "qweb-pdf",
            "data": data,
            "context": self.env.context,
        }

    def action_generate_dashboard(self):
        """Generate interactive dashboard view"""
        data = self._prepare_dashboard_data()

        # Create dashboard record
        dashboard = self.env["performance.dashboard"].create(
            {
                "dashboard_data": json.dumps(data),
                "report_type": self.report_type,
                "date_from": self.date_from,
                "date_to": self.date_to,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": "Performance Dashboard",
            "res_model": "performance.dashboard",
            "view_mode": "form",
            "view_id": self.env.ref(
                "hr_appraisal_objectives.view_performance_dashboard_form"
            ).id,
            "res_id": dashboard.id,
            "target": "new",
        }

    def _prepare_report_data(self):
        """Prepare data for the report"""
        data = {
            "report_type": self.report_type,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "include_charts": self.include_charts,
            "include_details": self.include_details,
            "include_trends": self.include_trends,
            "include_recommendations": self.include_recommendations,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if self.report_type == "department":
            data["departments"] = self._get_department_data()
            data["department_summary"] = self._get_department_summary(
                data["departments"]
            )
        elif self.report_type == "institutional":
            data["institutional"] = self._get_institutional_data()
            data["institutional_summary"] = self._get_institutional_summary(
                data["institutional"]
            )
        elif self.report_type == "individual":
            data["individuals"] = self._get_individual_data()
            data["individual_summary"] = self._get_individual_summary(
                data["individuals"]
            )
        elif self.report_type == "comparative":
            data["comparative"] = self._get_comparative_data()
            data["comparative_summary"] = self._get_comparative_summary(
                data["comparative"]
            )
        elif self.report_type == "dashboard":
            data.update(self._prepare_dashboard_data())

        return data

    def _prepare_dashboard_data(self):
        """Prepare comprehensive dashboard data"""
        return {
            "overview_metrics": self._get_overview_metrics(),
            "department_performance": self._get_department_data(),
            "top_performers": self._get_top_performers(),
            "performance_trends": self._get_performance_trends(),
            "risk_analysis": self._get_risk_analysis(),
            "completion_forecast": self._get_completion_forecast(),
        }

    def _get_overview_metrics(self):
        """Get high-level overview metrics"""
        total_employees = self.env["hr.employee"].search_count([])
        total_departments = self.env["hr.department"].search_count([])

        # Get objectives data
        institutional_objs = self.env["hr.institutional.objective"].search(
            [("start_date", ">=", self.date_from), ("end_date", "<=", self.date_to)]
        )

        dept_objs = self.env["hr.department.objective"].search(
            [("start_date", ">=", self.date_from), ("end_date", "<=", self.date_to)]
        )

        individual_goals = self.env["hr.appraisal.goal"].search(
            [("create_date", ">=", self.date_from), ("create_date", "<=", self.date_to)]
        )

        completed_goals = individual_goals.filtered(lambda g: g.state == "final")

        return {
            "total_employees": total_employees,
            "total_departments": total_departments,
            "total_institutional_objectives": len(institutional_objs),
            "total_department_objectives": len(dept_objs),
            "total_individual_goals": len(individual_goals),
            "completed_goals": len(completed_goals),
            "completion_rate": (
                (len(completed_goals) / len(individual_goals) * 100)
                if individual_goals
                else 0
            ),
            "avg_progress": (
                sum(obj.progress for obj in institutional_objs)
                / len(institutional_objs)
                if institutional_objs
                else 0
            ),
            "avg_score": (
                sum(goal.final_score for goal in individual_goals if goal.final_score)
                / len([g for g in individual_goals if g.final_score])
                if [g for g in individual_goals if g.final_score]
                else 0
            ),
        }

    def _get_department_data(self):
        """Enhanced department data with more metrics"""
        departments = self.department_ids or self.env["hr.department"].search([])
        data = []
        for dept in departments:
            dept_objectives = self.env["hr.department.objective"].search(
                [
                    ("department_id", "=", dept.id),
                    ("start_date", ">=", self.date_from),
                    ("end_date", "<=", self.date_to),
                ]
            )
            individual_goals = self.env["hr.appraisal.goal"].search(
                [
                    ("department_id", "=", dept.id),
                    ("create_date", ">=", self.date_from),
                    ("create_date", "<=", self.date_to),
                ]
            )

            # Calculate additional metrics
            completed_goals = individual_goals.filtered(lambda g: g.state == "final")
            avg_progress = (
                sum(obj.progress for obj in dept_objectives) / len(dept_objectives)
                if dept_objectives
                else 0
            )
            scored_goals = [g for g in individual_goals if g.final_score]
            avg_score = (
                sum(goal.final_score for goal in scored_goals) / len(scored_goals)
                if scored_goals
                else 0
            )
            completion_rate = (
                len(completed_goals) / len(individual_goals) if individual_goals else 0
            )

            # Performance trend calculation
            recent_goals = individual_goals.sorted("create_date", reverse=True)[:5]
            older_goals = individual_goals.sorted("create_date")[:5]

            recent_avg = (
                sum(g.progression for g in recent_goals) / len(recent_goals)
                if recent_goals
                else 0
            )
            older_avg = (
                sum(g.progression for g in older_goals) / len(older_goals)
                if older_goals
                else 0
            )
            trend = recent_avg - older_avg

            data.append(
                {
                    "department": dept,
                    "objectives_count": len(dept_objectives),
                    "goals_count": len(individual_goals),
                    "avg_progress": avg_progress,
                    "avg_score": avg_score,
                    "completed_goals": len(completed_goals),
                    "completion_rate": completion_rate * 100,
                    "performance_trend": trend,
                    "employee_count": dept.total_employee,
                    "risk_level": self._calculate_risk_level(
                        avg_progress, avg_score, completion_rate
                    ),
                    "recommendations": self._get_department_recommendations(
                        avg_progress, avg_score, completion_rate
                    ),
                }
            )
        return data

    def _get_institutional_data(self):
        """Enhanced institutional data"""
        institutional_objs = self.institutional_objective_ids or self.env[
            "hr.institutional.objective"
        ].search(
            [("start_date", ">=", self.date_from), ("end_date", "<=", self.date_to)]
        )
        data = []
        for obj in institutional_objs:
            # Calculate additional metrics
            dept_objectives = obj.department_objective_ids
            individual_goals = self.env["hr.appraisal.goal"].search(
                [
                    (
                        "department_id",
                        "in",
                        dept_objectives.mapped("department_id").ids,
                    ),
                    ("create_date", ">=", self.date_from),
                    ("create_date", "<=", self.date_to),
                ]
            )

            scored_goals = [g for g in individual_goals if g.final_score]
            avg_score = (
                sum(goal.final_score for goal in scored_goals) / len(scored_goals)
                if scored_goals
                else 0
            )
            completion_rate = (
                len(individual_goals.filtered(lambda g: g.state == "final"))
                / len(individual_goals)
                if individual_goals
                else 0
            )

            data.append(
                {
                    "objective": obj,
                    "progress": obj.progress,
                    "departments_count": len(obj.department_objective_ids),
                    "total_individuals": obj.total_individual_objectives,
                    "avg_score": avg_score,
                    "completion_rate": completion_rate * 100,
                    "deadline_status": self._get_deadline_status(obj),
                    "risk_assessment": self._assess_institutional_risk(obj),
                    "impact_analysis": self._analyze_institutional_impact(obj),
                }
            )
        return data

    def _get_individual_data(self):
        """Enhanced individual data"""
        employees = self.employee_ids or self.env["hr.employee"].search([])
        data = []
        for employee in employees:
            goals = self.env["hr.appraisal.goal"].search(
                [
                    ("employee_id", "=", employee.id),
                    ("create_date", ">=", self.date_from),
                    ("create_date", "<=", self.date_to),
                ]
            )

            if goals:
                completed_goals = goals.filtered(lambda g: g.state == "final")
                avg_progress = sum(goal.progression for goal in goals) / len(goals)
                scored_goals = [g for g in goals if g.final_score]
                avg_score = (
                    sum(goal.final_score for goal in scored_goals) / len(scored_goals)
                    if scored_goals
                    else 0
                )
                completion_rate = len(completed_goals) / len(goals)

                # Performance trend
                recent_goals = goals.sorted("create_date", reverse=True)[:3]
                older_goals = goals.sorted("create_date")[:3]

                recent_avg = (
                    sum(g.progression for g in recent_goals) / len(recent_goals)
                    if recent_goals
                    else 0
                )
                older_avg = (
                    sum(g.progression for g in older_goals) / len(older_goals)
                    if older_goals
                    else 0
                )
                trend = recent_avg - older_avg

                data.append(
                    {
                        "employee": employee,
                        "goals_count": len(goals),
                        "avg_progress": avg_progress,
                        "avg_score": avg_score,
                        "completed_goals": len(completed_goals),
                        "completion_rate": completion_rate * 100,
                        "performance_trend": trend,
                        "department": (
                            employee.department_id.name
                            if employee.department_id
                            else ""
                        ),
                        "position": employee.job_title or "",
                        "performance_category": self._categorize_performance(
                            avg_score, avg_progress
                        ),
                        "development_needs": self._identify_development_needs(goals),
                    }
                )
        return data

    def _get_comparative_data(self):
        """Enhanced comparative data"""
        departments = self.env["hr.department"].search([])
        data = []
        for dept in departments:
            goals = self.env["hr.appraisal.goal"].search(
                [
                    ("department_id", "=", dept.id),
                    ("create_date", ">=", self.date_from),
                    ("create_date", "<=", self.date_to),
                ]
            )
            if goals:
                completed_goals = goals.filtered(lambda g: g.state == "final")
                scored_goals = [g for g in goals if g.final_score]
                avg_score = (
                    sum(goal.final_score for goal in scored_goals) / len(scored_goals)
                    if scored_goals
                    else 0
                )
                completion_rate = len(completed_goals) / len(goals)
                avg_progress = sum(goal.progression for goal in goals) / len(goals)

                data.append(
                    {
                        "department": dept.name,
                        "total_goals": len(goals),
                        "avg_score": avg_score,
                        "completion_rate": completion_rate,
                        "avg_progress": avg_progress,
                        "employee_count": len(dept.employee_ids),
                        "efficiency_score": self._calculate_efficiency_score(
                            completion_rate, avg_score, avg_progress
                        ),
                        "benchmark_comparison": self._compare_to_benchmark(
                            avg_score, completion_rate
                        ),
                    }
                )
        return sorted(data, key=lambda x: x["avg_score"], reverse=True)

    def _get_top_performers(self):
        """Get top performing employees and departments"""
        employees = self.env["hr.employee"].search([])
        top_employees = []

        for emp in employees:
            goals = self.env["hr.appraisal.goal"].search(
                [
                    ("employee_id", "=", emp.id),
                    ("create_date", ">=", self.date_from),
                    ("create_date", "<=", self.date_to),
                ]
            )

            if goals:
                # Get goals with final scores
                scored_goals = [g for g in goals if g.final_score]
                if scored_goals:
                    avg_score = sum(goal.final_score for goal in scored_goals) / len(
                        scored_goals
                    )
                    if avg_score >= 4.0:  # Top performers threshold
                        top_employees.append(
                            {
                                "employee": emp.name,
                                "department": (
                                    emp.department_id.name if emp.department_id else ""
                                ),
                                "avg_score": avg_score,
                                "goals_count": len(goals),
                            }
                        )

        return sorted(top_employees, key=lambda x: x["avg_score"], reverse=True)[:10]

    def _get_performance_trends(self):
        """Get performance trends over time"""
        # Monthly trends for the last 6 months
        trends = []
        for i in range(6):
            month_start = (datetime.now() - timedelta(days=30 * i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(
                days=1
            )

            goals = self.env["hr.appraisal.goal"].search(
                [("create_date", ">=", month_start), ("create_date", "<=", month_end)]
            )

            if goals:
                avg_progress = sum(g.progression for g in goals) / len(goals)
                scored_goals = [g for g in goals if g.final_score]
                avg_score = (
                    sum(g.final_score for g in scored_goals) / len(scored_goals)
                    if scored_goals
                    else 0
                )
                completion_rate = len(
                    goals.filtered(lambda g: g.state == "final")
                ) / len(goals)

                trends.append(
                    {
                        "month": month_start.strftime("%B %Y"),
                        "avg_progress": avg_progress,
                        "avg_score": avg_score,
                        "completion_rate": completion_rate * 100,
                        "goals_count": len(goals),
                    }
                )

        return list(reversed(trends))

    def _get_risk_analysis(self):
        """Identify performance risks"""
        risks = []

        # Departments at risk
        departments = self.env["hr.department"].search([])
        for dept in departments:
            goals = self.env["hr.appraisal.goal"].search(
                [
                    ("department_id", "=", dept.id),
                    ("create_date", ">=", self.date_from),
                    ("create_date", "<=", self.date_to),
                ]
            )

            if goals:
                avg_progress = sum(g.progression for g in goals) / len(goals)
                scored_goals = [g for g in goals if g.final_score]
                avg_score = (
                    sum(g.final_score for g in scored_goals) / len(scored_goals)
                    if scored_goals
                    else 0
                )

                if avg_progress < 50 or avg_score < 2.5:
                    risks.append(
                        {
                            "type": "department",
                            "name": dept.name,
                            "risk_level": "high" if avg_progress < 30 else "medium",
                            "issue": f"Low progress ({avg_progress:.1f}%) and score ({avg_score:.1f})",
                            "recommendation": "Schedule performance review and provide support",
                        }
                    )

        # Overdue objectives
        overdue_objs = self.env["hr.institutional.objective"].search(
            [("end_date", "<", fields.Date.today()), ("state", "=", "active")]
        )

        for obj in overdue_objs:
            risks.append(
                {
                    "type": "objective",
                    "name": obj.name,
                    "risk_level": "high",
                    "issue": f"Overdue by {(fields.Date.today() - obj.end_date).days} days",
                    "recommendation": "Review timeline and adjust if necessary",
                }
            )

        return risks

    def _get_completion_forecast(self):
        """Forecast completion rates"""
        current_date = fields.Date.today()
        end_of_period = self.date_to

        # Calculate current completion rate
        total_goals = self.env["hr.appraisal.goal"].search(
            [("create_date", ">=", self.date_from), ("create_date", "<=", self.date_to)]
        )

        completed_goals = total_goals.filtered(lambda g: g.state == "final")
        current_completion = (
            len(completed_goals) / len(total_goals) if total_goals else 0
        )

        # Simple linear forecast
        days_elapsed = (current_date - self.date_from).days
        total_days = (end_of_period - self.date_from).days

        if days_elapsed > 0 and total_days > 0:
            progress_rate = current_completion / (days_elapsed / total_days)
            forecasted_completion = min(progress_rate, 1.0) * 100
        else:
            forecasted_completion = current_completion * 100

        return {
            "current_completion": current_completion * 100,
            "forecasted_completion": forecasted_completion,
            "target_completion": 85,  # Assuming 85% target
            "gap": max(0, 85 - forecasted_completion),
            "on_track": forecasted_completion >= 85,
        }

    # Helper methods for enhanced analytics
    def _calculate_risk_level(self, progress, score, completion_rate):
        """Calculate risk level based on metrics"""
        if progress < 30 or score < 2.0 or completion_rate < 0.3:
            return "high"
        elif progress < 60 or score < 3.0 or completion_rate < 0.6:
            return "medium"
        else:
            return "low"

    def _get_department_recommendations(self, progress, score, completion_rate):
        """Generate recommendations for departments"""
        recommendations = []

        if progress < 50:
            recommendations.append("Increase focus on progress tracking and support")
        if score < 3.0:
            recommendations.append("Provide additional training and resources")
        if completion_rate < 0.5:
            recommendations.append("Review goal setting and timeline management")

        return recommendations

    def _get_deadline_status(self, objective):
        """Get deadline status for institutional objectives"""
        days_left = (objective.end_date - fields.Date.today()).days

        if days_left < 0:
            return "overdue"
        elif days_left <= 7:
            return "urgent"
        elif days_left <= 30:
            return "warning"
        else:
            return "on_track"

    def _assess_institutional_risk(self, objective):
        """Assess risk level for institutional objectives"""
        progress = objective.progress
        days_left = (objective.end_date - fields.Date.today()).days

        if progress < 30 and days_left < 30:
            return "critical"
        elif progress < 50 or days_left < 15:
            return "high"
        elif progress < 70:
            return "medium"
        else:
            return "low"

    def _analyze_institutional_impact(self, objective):
        """Analyze impact of institutional objectives"""
        return {
            "departments_affected": len(objective.department_objective_ids),
            "employees_impacted": objective.total_individual_objectives,
            "kpi_coverage": len(objective.kpi_line_ids),
            "progress_consistency": (
                "consistent" if objective.progress > 70 else "variable"
            ),
        }

    def _categorize_performance(self, score, progress):
        """Categorize employee performance"""
        if score >= 4.0 and progress >= 80:
            return "excellent"
        elif score >= 3.0 and progress >= 60:
            return "good"
        elif score >= 2.0 and progress >= 40:
            return "average"
        else:
            return "needs_improvement"

    def _identify_development_needs(self, goals):
        """Identify development needs based on goals"""
        needs = []
        low_scoring_goals = goals.filtered(
            lambda g: g.final_score and g.final_score < 3.0
        )

        if low_scoring_goals:
            needs.append("Additional training in specific areas")

        incomplete_goals = goals.filtered(lambda g: g.progression < 50)
        if incomplete_goals:
            needs.append("Time management and prioritization skills")

        return needs

    def _calculate_efficiency_score(self, completion_rate, avg_score, avg_progress):
        """Calculate efficiency score for departments"""
        return (
            completion_rate * 0.4 + (avg_score / 5) * 0.3 + (avg_progress / 100) * 0.3
        ) * 100

    def _compare_to_benchmark(self, avg_score, completion_rate):
        """Compare to organizational benchmarks"""
        benchmark_score = 3.5  # Assuming organizational benchmark
        benchmark_completion = 0.8  # Assuming 80% completion benchmark

        score_gap = avg_score - benchmark_score
        completion_gap = completion_rate - benchmark_completion

        if score_gap >= 0.5 and completion_gap >= 0.1:
            return "above_benchmark"
        elif score_gap >= 0 and completion_gap >= 0:
            return "at_benchmark"
        else:
            return "below_benchmark"

    # Summary methods for report sections
    def _get_department_summary(self, departments_data):
        """Generate department summary statistics"""
        if not departments_data:
            return {}

        return {
            "total_departments": len(departments_data),
            "avg_progress": sum(d["avg_progress"] for d in departments_data)
            / len(departments_data),
            "avg_score": sum(d["avg_score"] for d in departments_data)
            / len(departments_data),
            "total_goals": sum(d["goals_count"] for d in departments_data),
            "completed_goals": sum(d["completed_goals"] for d in departments_data),
            "high_risk_departments": len(
                [d for d in departments_data if d["risk_level"] == "high"]
            ),
        }

    def _get_institutional_summary(self, institutional_data):
        """Generate institutional summary statistics"""
        if not institutional_data:
            return {}

        return {
            "total_objectives": len(institutional_data),
            "avg_progress": sum(d["progress"] for d in institutional_data)
            / len(institutional_data),
            "avg_score": sum(d["avg_score"] for d in institutional_data)
            / len(institutional_data),
            "total_departments_involved": sum(
                d["departments_count"] for d in institutional_data
            ),
            "total_individuals_impacted": sum(
                d["total_individuals"] for d in institutional_data
            ),
            "overdue_objectives": len(
                [d for d in institutional_data if d["deadline_status"] == "overdue"]
            ),
        }

    def _get_individual_summary(self, individuals_data):
        """Generate individual summary statistics"""
        if not individuals_data:
            return {}

        return {
            "total_employees": len(individuals_data),
            "avg_progress": sum(d["avg_progress"] for d in individuals_data)
            / len(individuals_data),
            "avg_score": sum(d["avg_score"] for d in individuals_data)
            / len(individuals_data),
            "total_goals": sum(d["goals_count"] for d in individuals_data),
            "completed_goals": sum(d["completed_goals"] for d in individuals_data),
            "top_performers": len(
                [
                    d
                    for d in individuals_data
                    if d["performance_category"] == "excellent"
                ]
            ),
        }

    def _get_comparative_summary(self, comparative_data):
        """Generate comparative summary statistics"""
        if not comparative_data:
            return {}

        return {
            "total_departments": len(comparative_data),
            "avg_score": sum(d["avg_score"] for d in comparative_data)
            / len(comparative_data),
            "avg_completion_rate": sum(d["completion_rate"] for d in comparative_data)
            / len(comparative_data),
            "avg_progress": sum(d["avg_progress"] for d in comparative_data)
            / len(comparative_data),
            "best_performing": (
                comparative_data[0]["department"] if comparative_data else ""
            ),
            "needs_attention": [
                d["department"] for d in comparative_data if d["avg_score"] < 3.0
            ],
        }
