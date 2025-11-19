"""Typed Todoist client wrapper with retry and metadata support."""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task

logger = logging.getLogger(__name__)


@dataclass
class TaskFilter:
    """Filter criteria for task queries."""

    project_id: Optional[str] = None
    label_names: Optional[List[str]] = None
    due_date: Optional[str] = None
    completed: bool = False


class TodoistRetryError(Exception):
    """Raised when retries are exhausted."""

    pass


class TodoistClient:
    """
    Typed wrapper for Todoist API with retry logic and metadata support.

    Provides:
    - Task filtering and labeling
    - Comment-based metadata storage
    - Project note storage for preferences
    - Human-friendly priority mapping (P1-P4 ↔ Todoist 4-1)
    - Retry with exponential backoff
    """

    def __init__(self, api_token: Optional[str] = None):
        """Initialize Todoist client."""
        self.api_token = api_token or os.getenv("TODOIST_API_TOKEN")
        if not self.api_token:
            raise ValueError("TODOIST_API_TOKEN environment variable required")

        self.api = TodoistAPI(self.api_token)
        self._flowcoach_project_id: Optional[str] = None

    def _retry_with_backoff(self, func, max_retries: int = 3) -> Any:
        """Execute function with exponential backoff on rate limits."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e

                # Handle rate limiting (429)
                if hasattr(e, "status_code") and e.status_code == 429:
                    backoff_time = min(2**attempt, 60)  # Max 60s backoff
                    logger.warning(
                        f"Rate limited, backing off {backoff_time}s (attempt {attempt + 1})"
                    )
                    time.sleep(backoff_time)
                    continue

                # For other errors, don't retry on last attempt
                if attempt == max_retries - 1:
                    break

                # Brief backoff for other errors
                time.sleep(0.5)

        raise TodoistRetryError(f"Failed after {max_retries} attempts: {last_exception}")

    def get_tasks_by_filter(self, task_filter: TaskFilter) -> List[Dict[str, Any]]:
        """Get tasks matching the filter criteria."""

        def _get_tasks():
            # Build filter string
            filter_parts = []
            if task_filter.project_id:
                filter_parts.append(f"#{task_filter.project_id}")
            if task_filter.label_names:
                for label in task_filter.label_names:
                    filter_parts.append(f"@{label}")
            if task_filter.due_date:
                filter_parts.append(f"due: {task_filter.due_date}")

            filter_str = " & ".join(filter_parts) if filter_parts else None

            tasks = self.api.get_tasks(filter=filter_str)
            return [self._task_to_dict(task) for task in tasks]

        return self._retry_with_backoff(_get_tasks)

    def add_task_labels(self, task_id: str, label_names: List[str]) -> bool:
        """Add labels to a task."""

        def _add_labels():
            task = self.api.get_task(task_id)
            current_labels = task.labels or []
            new_labels = list(set(current_labels + label_names))

            self.api.update_task(task_id, labels=new_labels)
            return True

        return self._retry_with_backoff(_add_labels)

    def remove_task_labels(self, task_id: str, label_names: List[str]) -> bool:
        """Remove labels from a task."""

        def _remove_labels():
            task = self.api.get_task(task_id)
            current_labels = task.labels or []
            new_labels = [label for label in current_labels if label not in label_names]

            self.api.update_task(task_id, labels=new_labels)
            return True

        return self._retry_with_backoff(_remove_labels)

    def add_task_comment(self, task_id: str, content: str) -> str:
        """Add a comment to a task. Returns comment ID."""

        def _add_comment():
            comment = self.api.add_comment(content=content, task_id=task_id)
            return comment.id

        return self._retry_with_backoff(_add_comment)

    def create_subtask(self, parent_task_id: str, content: str, **kwargs) -> str:
        """Create a subtask under the given parent. Returns task ID."""

        def _create_subtask():
            # Get parent task to inherit project
            parent = self.api.get_task(parent_task_id)

            task = self.api.add_task(
                content=content, project_id=parent.project_id, parent_id=parent_task_id, **kwargs
            )
            return task.id

        return self._retry_with_backoff(_create_subtask)

    def get_tasks(self, **kwargs) -> List[Dict[str, Any]]:
        """Get tasks from Todoist. Wrapper for API compatibility."""

        def _get_tasks():
            tasks = self.api.get_tasks(**kwargs)
            # Convert Task objects to dictionaries
            return [self._task_to_dict(task) for task in tasks]

        return self._retry_with_backoff(_get_tasks)

    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects from Todoist."""

        def _get_projects():
            projects = self.api.get_projects()
            # Convert Project objects to dictionaries
            return [{"id": p.id, "name": p.name, "color": p.color} for p in projects]

        return self._retry_with_backoff(_get_projects)

    def get_completed_today(self) -> List[Dict[str, Any]]:
        """Get tasks completed today."""

        def _get_completed():
            # Note: This might need the premium API for historical data
            # For now, we'll return empty list and implement via tracking
            logger.warning("get_completed_today requires premium API or tracking")
            return []

        return self._retry_with_backoff(_get_completed)

    def get_flowcoach_project(self) -> Optional[str]:
        """Get or create the FlowCoach project for metadata storage."""
        if self._flowcoach_project_id:
            return self._flowcoach_project_id

        def _get_or_create_project():
            projects = self.api.get_projects()

            # Look for existing FlowCoach project
            for project in projects:
                if project.name == "FlowCoach":
                    self._flowcoach_project_id = project.id
                    return project.id

            # Create new FlowCoach project
            project = self.api.add_project(name="FlowCoach", color="blue")
            self._flowcoach_project_id = project.id
            return project.id

        return self._retry_with_backoff(_get_or_create_project)

    def save_project_note(self, content: str) -> str:
        """Save content as a pinned task in FlowCoach project."""
        project_id = self.get_flowcoach_project()

        def _save_note():
            # Look for existing preferences task
            tasks = self.api.get_tasks(project_id=project_id)
            prefs_task = None

            for task in tasks:
                if task.content.startswith("FlowCoach Preferences"):
                    prefs_task = task
                    break

            if prefs_task:
                # Update existing task description/content
                self.api.update_task(prefs_task.id, description=content)
                return prefs_task.id
            else:
                # Create new preferences task
                task = self.api.add_task(
                    content="FlowCoach Preferences (Do not delete)",
                    project_id=project_id,
                    description=content,
                    priority=4,  # High priority to keep it at top
                )
                return task.id

        return self._retry_with_backoff(_save_note)

    def load_project_note(self) -> Optional[str]:
        """Load content from the pinned FlowCoach preferences task."""
        project_id = self.get_flowcoach_project()

        def _load_note():
            tasks = self.api.get_tasks(project_id=project_id)

            for task in tasks:
                if task.content.startswith("FlowCoach Preferences"):
                    return task.description or ""

            return None

        return self._retry_with_backoff(_load_note)

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert Task object to dictionary."""
        due_dict = None
        if task.due:
            # Handle different versions of Due object
            if hasattr(task.due, "dict"):
                due_dict = task.due.dict()
            elif hasattr(task.due, "__dict__"):
                due_dict = task.due.__dict__
            else:
                # Fallback - try to extract date manually
                due_dict = {
                    "date": getattr(task.due, "date", None),
                    "string": getattr(task.due, "string", None),
                    "datetime": getattr(task.due, "datetime", None),
                    "timezone": getattr(task.due, "timezone", None),
                }

        return {
            "id": task.id,
            "content": task.content,
            "description": task.description or "",
            "project_id": task.project_id,
            "labels": task.labels or [],
            "priority": task.priority,
            "due": due_dict,
            "url": task.url,
            "comment_count": task.comment_count,
            "created_at": task.created_at,
            "is_completed": task.is_completed,
        }

    def add_task_label(self, task_id: str, label: str) -> bool:
        """Add a label to a task."""

        def _add_label():
            # Get current task to preserve existing labels
            task = self.api.get_task(task_id)
            current_labels = task.labels or []

            # Add new label if not already present
            if label not in current_labels:
                new_labels = current_labels + [label]
                self.api.update_task(task_id, labels=new_labels)

            return True

        try:
            return self._retry_with_backoff(_add_label)
        except Exception as e:
            logger.error(f"Failed to add label {label} to task {task_id}: {e}")
            return False

    def set_priority_human(self, task_id: str, p_human: int) -> bool:
        """
        Set task priority using human-friendly numbering (P1-P4).

        Args:
            task_id: Task ID to update
            p_human: Human priority (1=highest, 4=lowest)

        Returns:
            True if successful

        Note:
            Converts P1-P4 to Todoist priorities 4-1 (inverted scale)
        """
        # Clamp to valid range and invert for Todoist
        p_human = max(1, min(4, p_human))
        p_todoist = 5 - p_human

        def _set_priority():
            self.api.update_task(task_id=task_id, priority=p_todoist)
            return True

        try:
            return self._retry_with_backoff(_set_priority)
        except Exception as e:
            logger.error(f"Failed to set priority for task {task_id}: {e}")
            return False

    def get_priority_human(self, p_todoist: int) -> int:
        """
        Convert Todoist priority to human-friendly numbering.

        Args:
            p_todoist: Todoist priority (1-4, where 4=highest)

        Returns:
            Human priority (1-4, where 1=highest)
        """
        # Todoist: 1=low, 2=normal, 3=high, 4=urgent
        # Human: P1=urgent, P2=high, P3=normal, P4=low
        return 5 - p_todoist

    def get_open_flow_top_today_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all open tasks with flow_top_today label for a user."""

        def _get_tasks():
            # For now, we get ALL flow_top_today tasks since we don't have user mapping
            # In production, you'd filter by user's projects or a user-specific label
            tasks = self.api.get_tasks(filter="@flow_top_today")
            return [self._task_to_dict(task) for task in tasks if not task.is_completed]

        return self._retry_with_backoff(_get_tasks)

    def clear_label_from_task(self, task_id: str, label: str) -> None:
        """Remove a specific label from a task."""

        def _clear_label():
            task = self.api.get_task(task_id)
            current_labels = task.labels or []
            new_labels = [lbl for lbl in current_labels if lbl != label]
            self.api.update_task(task_id, labels=new_labels)

        self._retry_with_backoff(_clear_label)

    def update_task(self, task_id: str, payload: Dict[str, Any]) -> None:
        """Update a task with the given payload."""

        def _update():
            # Handle priority conversion if present
            if "priority" in payload:
                # Convert human priority (1-4) to Todoist priority (4-1)
                human_priority = payload["priority"]
                payload["priority"] = 5 - human_priority

            # Handle labels - merge with existing if present
            if "labels" in payload:
                task = self.api.get_task(task_id)
                current_labels = task.labels or []
                new_labels = list(set(current_labels + payload["labels"]))
                payload["labels"] = new_labels

            self.api.update_task(task_id, **payload)

        self._retry_with_backoff(_update)
