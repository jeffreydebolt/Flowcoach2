"""
Todoist service for FlowCoach.

This module provides a service for interacting with the Todoist API.
"""

import logging
import re
from typing import Any

from todoist_api_python.api import TodoistAPI


class TodoistService:
    """Service for interacting with Todoist API."""

    def __init__(self, api_token: str):
        """
        Initialize the Todoist service.

        Args:
            api_token: Todoist API token
        """
        self.logger = logging.getLogger(__name__)
        self.api_token = api_token

        # Initialize API client
        try:
            self.api = TodoistAPI(api_token)
            self.logger.info("Todoist API initialized successfully")

            # Test connection (Convert to list before len)
            projects = list(self.api.get_projects())
            self.logger.info(f"Todoist connection successful - found {len(projects)} projects")
        except Exception as e:
            self.logger.error(f"Failed to initialize Todoist API: {e}")
            raise

        # Cache for projects, labels, etc.
        self._projects = None
        self._labels = None

    def add_task(self, content: str, **kwargs) -> dict[str, Any]:
        """
        Add a task to Todoist.

        Args:
            content: Task content
            **kwargs: Additional task parameters (due_date, priority, etc.)

        Returns:
            Created task object
        """
        self.logger.info(f"Adding task: '{content}' with kwargs: {kwargs}")

        try:
            # Log API token status (masked)
            token_status = "present" if self.api_token else "missing"
            self.logger.info(f"API token status: {token_status}")

            # Create task
            task = self.api.add_task(content=content, **kwargs)
            self.logger.info(f"Task created successfully: {task.id}")

            # Convert to dictionary for consistent return format
            task_dict = {
                "id": task.id,
                "content": task.content,
                "due": task.due.date if task.due else None,
                "priority": task.priority,
                "url": task.url,
            }
            self.logger.info(f"Returning task data: {task_dict}")
            return task_dict

        except Exception as e:
            self.logger.error(f"Error creating task: {str(e)}", exc_info=True)
            raise

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task object or None if not found
        """
        try:
            task = self.api.get_task(task_id)

            # Convert to dictionary for consistent return format
            return {
                "id": task.id,
                "content": task.content,
                "due": task.due.date if task.due else None,
                "priority": task.priority,
                "url": task.url,
                "labels": task.labels,
            }
        except Exception as e:
            self.logger.error(f"Error getting task {task_id}: {e}")
            return None

    def update_task(self, task_id: str, **kwargs) -> dict[str, Any] | None:
        """
        Update a task.

        Args:
            task_id: Task ID
            **kwargs: Task properties to update

        Returns:
            Updated task object or None if update failed
        """
        try:
            self.api.update_task(task_id=task_id, **kwargs)

            # Get the updated task
            return self.get_task(task_id)
        except Exception as e:
            self.logger.error(f"Error updating task {task_id}: {e}")
            return None

    def complete_task(self, task_id: str) -> bool:
        """
        Complete a task.

        Args:
            task_id: Task ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.api.close_task(task_id=task_id)
            self.logger.info(f"Task {task_id} completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error completing task {task_id}: {e}")
            return False

    def get_tasks(self, filter_string: str | None = None) -> list[dict[str, Any]]:
        """
        Get tasks based on a filter string.

        Args:
            filter_string: Todoist filter query string

        Returns:
            List of task objects
        """
        try:
            tasks = self.api.get_tasks(filter=filter_string)

            # Convert to dictionaries for consistent return format
            return [
                {
                    "id": task.id,
                    "content": task.content,
                    "due": task.due.date if task.due else None,
                    "priority": task.priority,
                    "url": task.url,
                    "labels": task.labels,
                }
                for task in tasks
            ]
        except Exception as e:
            self.logger.error(f"Error getting tasks with filter '{filter_string}': {e}")
            return []

    def get_projects(self) -> list[dict[str, Any]]:
        """
        Get all projects.

        Returns:
            List of project objects
        """
        if self._projects is None:
            try:
                # Convert to list before iterating
                projects = list(self.api.get_projects())

                # Convert to dictionaries for consistent return format
                self._projects = [
                    {"id": project.id, "name": project.name, "color": project.color}
                    for project in projects
                ]
            except Exception as e:
                self.logger.error(f"Error getting projects: {e}")
                self._projects = []

        return self._projects

    def get_labels(self) -> list[dict[str, Any]]:
        """
        Get all labels.

        Returns:
            List of label objects
        """
        if self._labels is None:
            try:
                # Convert to list before iterating
                labels = list(self.api.get_labels())

                # Convert to dictionaries for consistent return format
                self._labels = [
                    {"id": label.id, "name": label.name, "color": label.color} for label in labels
                ]
            except Exception as e:
                self.logger.error(f"Error getting labels: {e}")
                self._labels = []

        return self._labels

    def get_or_create_label(self, label_name: str) -> str | None:
        """
        Get a label by name or create it if it doesn't exist.

        Args:
            label_name: Label name

        Returns:
            Label ID or None if creation failed
        """
        self.logger.info(f"Getting or creating label: {label_name}")

        # Refresh labels cache
        labels = self.get_labels()
        self.logger.info(f"Current labels in cache: {labels}")

        # Check if label exists
        for label in labels:
            if label["name"].lower() == label_name.lower():
                self.logger.info(f"Found existing label: {label}")
                return label["id"]

        # Create label if it doesn't exist
        try:
            self.logger.info(f"Creating new label: {label_name}")
            label = self.api.add_label(name=label_name)

            # Update cache
            self._labels = None

            self.logger.info(f"Successfully created label with ID: {label.id}")
            return label.id
        except Exception as e:
            self.logger.error(f"Error creating label '{label_name}': {e}")
            return None

    def get_tasks_by_label(self, label_name: str) -> list[dict[str, Any]]:
        """
        Get tasks with a specific label.

        Args:
            label_name: Label name

        Returns:
            List of task objects
        """
        try:
            filter_string = f"@{label_name}"
            return self.get_tasks(filter_string)
        except Exception as e:
            self.logger.error(f"Error getting tasks with label '{label_name}': {e}")
            return []

    def get_tasks_without_time_estimate(self) -> list[dict[str, Any]]:
        """
        Get tasks without a time estimate label.

        Returns:
            List of task objects
        """
        try:
            # Get all tasks
            all_tasks = self.get_tasks()

            # Filter out tasks with time estimate labels
            time_estimate_labels = ["2min", "10min", "30+min"]

            return [
                task
                for task in all_tasks
                if not any(label in time_estimate_labels for label in task.get("labels", []))
            ]
        except Exception as e:
            self.logger.error(f"Error getting tasks without time estimate: {e}")
            return []

    def add_task_with_gtd_processing(self, content: str, **kwargs) -> dict[str, Any] | None:
        """
        Add a task with GTD processing (action verb, clarity, etc.).

        This is a placeholder for the GTD processing functionality.
        In a real implementation, this would use OpenAI or similar to format the task.

        Args:
            content: Task content
            **kwargs: Additional task parameters

        Returns:
            Created task object
        """
        # Extract time estimate if present in the content
        time_estimate = self._extract_time_estimate(content)

        # Remove any existing time estimate from content
        processed_content = re.sub(
            r"\b(2|two|10|ten|30\+?|thirty\+?)\s*min\b|\b(quick|fast|short|medium|long|big)\b",
            "",
            content,
            flags=re.IGNORECASE,
        ).strip()

        # Add time estimate in square brackets if found
        if time_estimate:
            processed_content = f"[{time_estimate}] {processed_content}"

        # Check if content starts with an action verb
        first_word = processed_content.split()[0].lower() if processed_content.split() else ""

        # Common action verbs
        action_verbs = [
            "call",
            "email",
            "write",
            "draft",
            "create",
            "design",
            "develop",
            "review",
            "edit",
            "update",
            "research",
            "schedule",
            "book",
            "buy",
            "order",
            "prepare",
            "plan",
            "organize",
            "clean",
            "fix",
            "install",
        ]

        # If first word is not an action verb, try to add one
        if first_word not in action_verbs and not first_word.endswith("e"):
            # Simple heuristic: add "Complete" as a default action verb
            processed_content = f"Complete {processed_content}"

        # Create the task
        self.logger.info(f"Creating task with content: {processed_content}")
        return self.add_task(processed_content, **kwargs)

    def _extract_time_estimate(self, content: str) -> str | None:
        """
        Extract time estimate from content.

        Args:
            content: Task content

        Returns:
            Time estimate or None if not found
        """
        content_lower = content.lower()

        # Define patterns for time estimates
        patterns = {
            "2min": [r"\b2\s*min", r"\btwo\s*min", r"\bquick\b", r"\bfast\b", r"\bshort\b"],
            "10min": [r"\b10\s*min", r"\bten\s*min", r"\bmedium\b"],
            "30+min": [r"\b30\+?\s*min", r"\bthirty\+?\s*min", r"\blong\b", r"\bbig\b"],
        }

        # First check if there's already a time estimate in square brackets
        bracket_match = re.search(r"\[(2min|10min|30\+min)\]", content)
        if bracket_match:
            return bracket_match.group(1)

        # Then check for other patterns
        for estimate, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, content_lower):
                    return estimate

        return None

    def refresh_cache(self) -> None:
        """Refresh all cached data."""
        self._projects = None
        self._labels = None
        self.logger.info("Todoist cache refreshed")

    def create_project(self, name: str, **kwargs) -> dict[str, Any] | None:
        """
        Create a new project in Todoist.

        Args:
            name: Project name
            **kwargs: Additional project parameters (color, parent_id, etc.)

        Returns:
            Created project object or None if creation failed
        """
        self.logger.info(f"Creating project: '{name}' with kwargs: {kwargs}")

        try:
            # Create project
            project = self.api.add_project(name=name, **kwargs)
            self.logger.info(f"Project created successfully: {project.id}")

            # Clear projects cache
            self._projects = None

            # Convert to dictionary for consistent return format
            project_dict = {
                "id": project.id,
                "name": project.name,
                "color": project.color,
                "parent_id": project.parent_id if hasattr(project, "parent_id") else None,
                "order": project.order if hasattr(project, "order") else None,
                "url": project.url if hasattr(project, "url") else None,
            }
            self.logger.info(f"Returning project data: {project_dict}")
            return project_dict

        except Exception as e:
            self.logger.error(f"Error creating project: {str(e)}", exc_info=True)
            return None
