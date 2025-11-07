"""Todoist API client wrapper."""

import os
from typing import List, Dict, Optional, Any
from todoist_api_python.api import TodoistAPI
from ..core.errors import retry, TodoistError, InvalidTokenError, handle_todoist_error, log_event
import logging

logger = logging.getLogger(__name__)


class TodoistClient:
    """Thin wrapper around Todoist API with retries and error handling."""

    def __init__(self, api_token: Optional[str] = None):
        """Initialize Todoist client."""
        self.api_token = api_token or os.getenv('TODOIST_API_TOKEN')
        if not self.api_token:
            from ..core.errors import MissingConfigError
            raise MissingConfigError(
                'TODOIST_API_TOKEN',
                'Get your API token from Todoist Settings > Integrations'
            )
        try:
            self.api = TodoistAPI(self.api_token)
        except Exception as e:
            raise InvalidTokenError('Todoist', 'Verify your TODOIST_API_TOKEN is correct')

    @retry(max_attempts=3, exceptions=(Exception,))
    @handle_todoist_error
    def get_tasks(self, project_id: Optional[str] = None, label: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch tasks with optional filters."""
        try:
            filter_str = ""
            if project_id:
                filter_str = f"#{project_id}"
            if label:
                filter_str += f" & @{label}" if filter_str else f"@{label}"

            tasks = self.api.get_tasks(filter=filter_str) if filter_str else self.api.get_tasks()
            return [task.to_dict() for task in tasks]
        except Exception as e:
            logger.error(f"Failed to fetch tasks: {e}")
            if "401" in str(e) or "unauthorized" in str(e).lower():
                raise InvalidTokenError('Todoist')
            raise TodoistError(f"Failed to fetch tasks: {e}")

    @retry(max_attempts=3, exceptions=(Exception,))
    @handle_todoist_error
    def get_projects(self) -> List[Dict[str, Any]]:
        """Fetch all projects."""
        try:
            projects = self.api.get_projects()
            return [project.to_dict() for project in projects]
        except Exception as e:
            logger.error(f"Failed to fetch projects: {e}")
            raise TodoistError(f"Failed to fetch projects: {e}")

    @retry(max_attempts=3, exceptions=(Exception,))
    @handle_todoist_error
    def get_labels(self) -> List[Dict[str, Any]]:
        """Fetch all labels."""
        try:
            labels = self.api.get_labels()
            return [label.to_dict() for label in labels]
        except Exception as e:
            logger.error(f"Failed to fetch labels: {e}")
            raise TodoistError(f"Failed to fetch labels: {e}")

    @retry(max_attempts=3, exceptions=(Exception,))
    @handle_todoist_error
    def get_sections(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch sections for a project."""
        try:
            sections = self.api.get_sections(project_id=project_id)
            return [section.to_dict() for section in sections]
        except Exception as e:
            logger.error(f"Failed to fetch sections: {e}")
            raise TodoistError(f"Failed to fetch sections: {e}")

    @retry(max_attempts=2, exceptions=(Exception,))
    def create_task(self, content: str, **kwargs) -> Dict[str, Any]:
        """Create a new task."""
        try:
            task = self.api.add_task(content=content, **kwargs)
            log_event("info", "task_created", {"task_id": task.id, "content": content})
            return task.to_dict()
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise TodoistError(f"Failed to create task: {e}")

    @retry(max_attempts=2, exceptions=(Exception,))
    def update_task(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """Update an existing task."""
        try:
            task = self.api.update_task(task_id=task_id, **kwargs)
            log_event("info", "task_updated", {"task_id": task_id, "updates": kwargs})
            return task.to_dict()
        except Exception as e:
            logger.error(f"Failed to update task: {e}")
            raise TodoistError(f"Failed to update task: {e}")

    @retry(max_attempts=2, exceptions=(Exception,))
    def complete_task(self, task_id: str) -> bool:
        """Mark task as complete."""
        try:
            self.api.close_task(task_id=task_id)
            log_event("info", "task_completed", {"task_id": task_id})
            return True
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")
            raise TodoistError(f"Failed to complete task: {e}")

    def ensure_label(self, name: str) -> str:
        """Return label_id, creating it if missing."""
        labels = self.get_labels()
        if labels is None:
            raise TodoistError("Failed to fetch labels")

        for label in labels:
            if label.get("name") == name:
                return label["id"]

        # Create new label
        try:
            new_label = self.api.add_label(name=name)
            log_event("info", "label_created", {"label_name": name, "label_id": new_label.id})
            return new_label.id
        except Exception as e:
            logger.error(f"Failed to create label {name}: {e}")
            raise TodoistError(f"Failed to create label: {e}")

    @retry(max_attempts=2, exceptions=(Exception,))
    def update_project(self, project_id: str, name: str = None, color: str = None) -> bool:
        """
        Update a project.

        Args:
            project_id: Project ID to update
            name: New project name (optional)
            color: New project color (optional)

        Returns:
            True if project was updated
        """
        try:
            # Build update parameters
            update_params = {}
            if name is not None:
                update_params['name'] = name
            if color is not None:
                update_params['color'] = color

            if not update_params:
                logger.warning("No update parameters provided for project")
                return False

            # Update project
            self.api.update_project(project_id=project_id, **update_params)

            log_event(
                "info",
                "project_updated",
                {
                    "project_id": project_id,
                    "updates": update_params
                }
            )

            logger.info(f"Updated project {project_id}: {update_params}")
            return True

        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            raise TodoistError(f"Failed to update project: {e}")
