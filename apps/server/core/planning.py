"""Task selection logic for FlowCoach morning planning."""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass

from ..integrations.todoist_client import TodoistClient
from ..platform.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TaskCandidate:
    """A task candidate for morning planning."""

    id: str
    content: str
    project_name: str
    priority: int
    due_date: Optional[str]
    labels: List[str]
    is_overdue: bool
    is_priority_1: bool
    is_flow_tomorrow: bool
    is_flow_weekly: bool


class TaskSelector:
    """Selects tasks for morning brief modal."""

    def __init__(self, todoist_client: TodoistClient):
        """Initialize task selector with Todoist client."""
        self.todoist = todoist_client

    def get_morning_brief_tasks(self, user_id: str, is_monday: bool = False) -> List[TaskCandidate]:
        """Get tasks for morning brief modal.

        Args:
            user_id: Slack user ID
            is_monday: Whether today is Monday (includes weekly tasks)

        Returns:
            List of TaskCandidate objects for modal display
        """
        logger.info(
            f"Getting morning brief tasks for user {user_id}, is_monday={is_monday}",
            user_id=user_id,
        )

        try:
            # Get all tasks
            tasks = self.todoist.get_tasks()
            today = date.today()
            candidates = []

            for task in tasks:
                candidate = self._evaluate_task(task, today, is_monday)
                if candidate:
                    candidates.append(candidate)

            # Sort by priority: overdue > priority 1 > flow_tomorrow > flow_weekly
            candidates.sort(key=self._task_sort_key, reverse=True)

            # Limit to reasonable number for modal (max 10)
            limited_candidates = candidates[:10]

            logger.info(
                f"Selected {len(limited_candidates)} tasks for morning brief",
                user_id=user_id,
                extra_fields={"task_count": len(limited_candidates)},
            )

            return limited_candidates

        except Exception as e:
            logger.error(f"Failed to get morning brief tasks: {e}", user_id=user_id)
            return []

    def _evaluate_task(
        self, task: Dict[str, Any], today: date, is_monday: bool
    ) -> Optional[TaskCandidate]:
        """Evaluate if a task should be included in morning brief.

        Args:
            task: Task from Todoist API
            today: Today's date
            is_monday: Whether today is Monday

        Returns:
            TaskCandidate if task should be included, None otherwise
        """
        labels = [label.lower() for label in task.get("labels", [])]

        # Check inclusion criteria
        has_flow_tomorrow = "@flow_tomorrow" in labels
        has_flow_weekly = "@flow_weekly" in labels
        is_priority_1 = task.get("priority") == 4  # Todoist priority 4 = Priority 1
        is_overdue = self._is_overdue(task.get("due"), today)

        # Include task if it meets any criteria
        should_include = (
            has_flow_tomorrow or is_overdue or is_priority_1 or (is_monday and has_flow_weekly)
        )

        if not should_include:
            return None

        # Create candidate
        return TaskCandidate(
            id=task["id"],
            content=task["content"],
            project_name=self._get_project_name(task.get("project_id")),
            priority=task.get("priority", 1),
            due_date=task.get("due", {}).get("date") if task.get("due") else None,
            labels=task.get("labels", []),
            is_overdue=is_overdue,
            is_priority_1=is_priority_1,
            is_flow_tomorrow=has_flow_tomorrow,
            is_flow_weekly=has_flow_weekly,
        )

    def _is_overdue(self, due_info: Optional[Dict[str, Any]], today: date) -> bool:
        """Check if task is overdue."""
        if not due_info:
            return False

        due_date_str = due_info.get("date")
        if not due_date_str:
            return False

        try:
            # Parse date (format: YYYY-MM-DD)
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            return due_date < today
        except ValueError:
            return False

    def _get_project_name(self, project_id: Optional[str]) -> str:
        """Get project name from project ID."""
        if not project_id:
            return "Inbox"

        try:
            projects = self.todoist.get_projects()
            for project in projects:
                if project["id"] == project_id:
                    return project["name"]
            return "Unknown Project"
        except Exception:
            return "Unknown Project"

    def _task_sort_key(self, candidate: TaskCandidate) -> tuple:
        """Sort key for task priority (higher values = higher priority)."""
        return (
            candidate.is_overdue,
            candidate.is_priority_1,
            candidate.is_flow_tomorrow,
            candidate.is_flow_weekly,
            -candidate.priority,  # Negative because higher Todoist priority = lower number
        )


class PlanningService:
    """Service for task planning and updates."""

    def __init__(self, todoist_client: TodoistClient):
        """Initialize planning service."""
        self.todoist = todoist_client
        self.selector = TaskSelector(todoist_client)

    def get_morning_brief_tasks(self, user_id: str) -> List[TaskCandidate]:
        """Get tasks for morning brief - convenience method."""
        today = datetime.now()
        is_monday = today.weekday() == 0  # 0 = Monday
        return self.selector.get_morning_brief_tasks(user_id, is_monday)

    def mark_task_as_planned(self, task_id: str, priority_level: str, planned_time: str) -> bool:
        """Mark task as planned for today.

        Args:
            task_id: Todoist task ID
            priority_level: Priority level (p1/p2/p3) from modal
            planned_time: Time from modal (e.g., "09:00")

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            f"Marking task {task_id} as planned",
            extra_fields={"task_id": task_id, "priority": priority_level, "time": planned_time},
        )

        try:
            # Add @flow_top_today label
            success = self.todoist.add_task_label(task_id, "@flow_top_today")
            if not success:
                logger.error(
                    f"Failed to add @flow_top_today label to task {task_id}",
                    extra_fields={"task_id": task_id},
                )
                return False

            # Add flow:planned_due comment with priority and time
            comment_text = f"flow:planned_due priority={priority_level} time={planned_time}"
            success = self.todoist.add_task_comment(task_id, comment_text)
            if not success:
                logger.error(
                    f"Failed to add planning comment to task {task_id}",
                    extra_fields={"task_id": task_id},
                )
                return False

            logger.info(
                f"Successfully marked task {task_id} as planned", extra_fields={"task_id": task_id}
            )
            return True

        except Exception as e:
            logger.error(f"Failed to mark task as planned: {e}", extra_fields={"task_id": task_id})
            return False

    def save_checkin_time(self, user_id: str, checkin_time: str) -> bool:
        """Save flow:checkin time to user preferences.

        Args:
            user_id: Slack user ID
            checkin_time: Time when user completed morning brief (e.g., "09:30")

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            f"Saving checkin time for user {user_id}: {checkin_time}",
            user_id=user_id,
            extra_fields={"checkin_time": checkin_time},
        )

        try:
            # Load current preferences
            from ..core.prefs import PreferencesStore

            store = PreferencesStore(self.todoist)
            prefs = store.load_prefs(user_id)

            if not prefs:
                logger.warning(f"No preferences found for user {user_id}", user_id=user_id)
                return False

            # Update checkin time
            prefs.checkin_time_today = checkin_time

            # Save back to Todoist
            success = store.save_prefs(user_id, prefs)
            if success:
                logger.info(
                    f"Prefs.saved: checkin time {checkin_time} for user {user_id}",
                    user_id=user_id,
                    extra_fields={"checkin_time": checkin_time},
                )
            else:
                logger.error(f"Failed to save checkin time for user {user_id}", user_id=user_id)

            return success

        except Exception as e:
            logger.error(f"Failed to save checkin time: {e}", user_id=user_id)
            return False
