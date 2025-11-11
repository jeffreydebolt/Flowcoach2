"""Project audit classification and logic."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..core.momentum import MomentumTracker, ProjectMomentum

logger = logging.getLogger(__name__)


@dataclass
class ProjectAuditItem:
    """Single project in audit report."""

    project_id: str
    project_name: str
    momentum_score: int
    status: str
    outcome_defined: bool
    due_date: Optional[datetime]
    category: str  # 'healthy', 'needs_definition', 'stalled'
    last_activity_days: int


class ProjectAuditor:
    """Handles project audit classification and recommendations."""

    def __init__(self):
        self.tracker = MomentumTracker()

    def classify_projects(
        self, projects: List[Dict[str, Any]]
    ) -> Dict[str, List[ProjectAuditItem]]:
        """
        Classify projects into audit categories.

        Args:
            projects: List of project dicts from Todoist API

        Returns:
            Dict with 'healthy', 'needs_definition', 'stalled' categories
        """
        categorized = {"healthy": [], "needs_definition": [], "stalled": []}

        for project in projects:
            project_id = str(project["id"])
            project_name = project["name"]

            # Get momentum data
            momentum = self.tracker.get_project_momentum(project_id)

            if momentum:
                momentum_score = momentum.momentum_score
                status = momentum.status
                outcome_defined = momentum.outcome_defined
                due_date = momentum.due_date

                # Calculate days since last activity
                days_idle = (datetime.now() - momentum.last_activity_at).days
            else:
                # No momentum data means new/inactive project
                momentum_score = 60  # New projects need definition, not stalled
                status = "active"
                outcome_defined = False
                due_date = None
                days_idle = 0

            # Determine category based on audit rules
            if status == "stalled" or momentum_score < 50:
                category = "stalled"
            elif not outcome_defined or not due_date:
                category = "needs_definition"
            else:
                # Healthy: outcome_defined && due_date && momentum>=50
                category = "healthy"

            audit_item = ProjectAuditItem(
                project_id=project_id,
                project_name=project_name,
                momentum_score=momentum_score,
                status=status,
                outcome_defined=outcome_defined,
                due_date=due_date,
                category=category,
                last_activity_days=days_idle,
            )

            categorized[category].append(audit_item)

        # Sort each category by momentum score (descending)
        for category in categorized:
            categorized[category].sort(key=lambda x: x.momentum_score, reverse=True)

        return categorized

    def get_audit_summary(
        self, categorized_projects: Dict[str, List[ProjectAuditItem]]
    ) -> Dict[str, Any]:
        """Generate audit summary statistics."""
        total_projects = sum(len(projects) for projects in categorized_projects.values())

        return {
            "total_projects": total_projects,
            "healthy_count": len(categorized_projects["healthy"]),
            "needs_definition_count": len(categorized_projects["needs_definition"]),
            "stalled_count": len(categorized_projects["stalled"]),
            "healthy_percentage": round(
                (len(categorized_projects["healthy"]) / max(1, total_projects)) * 100, 1
            ),
            "audit_timestamp": datetime.now().isoformat(),
        }

    def recommend_actions(self, project: ProjectAuditItem) -> List[str]:
        """
        Recommend actions for a project based on its audit category.

        Returns:
            List of recommended action strings
        """
        recommendations = []

        if project.category == "stalled":
            recommendations.append("Recommit: Boost momentum and add next action")
            recommendations.append("Pause: Put on hold until needed")
            recommendations.append("Rewrite: Redefine outcome and timeline")

        elif project.category == "needs_definition":
            recommendations.append("Rewrite: Define concrete outcome and due date")
            if project.momentum_score < 75:
                recommendations.append("Recommit: Add energy with next action")

        else:  # healthy
            if project.last_activity_days > 3:
                recommendations.append("Check-in: Add progress update or next action")
            else:
                recommendations.append("Keep going: Project is on track")

        return recommendations
