"""Tests for TodoistClient get_tasks() shim implementation."""

import pytest
from unittest.mock import Mock, patch
from apps.server.integrations.todoist_client import TodoistClient


class TestTodoistClientShim:
    """Test TodoistClient wrapper methods for Phase 1 compatibility."""

    def test_get_tasks_method_exists(self):
        """Test that get_tasks() method exists and is callable."""
        client = TodoistClient("fake_token")
        assert hasattr(client, "get_tasks")
        assert callable(client.get_tasks)

    def test_get_projects_method_exists(self):
        """Test that get_projects() method exists and is callable."""
        client = TodoistClient("fake_token")
        assert hasattr(client, "get_projects")
        assert callable(client.get_projects)

    @patch("apps.server.integrations.todoist_client.TodoistAPI")
    def test_get_tasks_calls_api_and_converts(self, mock_api_class):
        """Test that get_tasks() calls the API and converts results."""
        # Setup mock
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        # Mock task object from todoist-python
        mock_task = Mock()
        mock_task.id = "123"
        mock_task.content = "Test task"
        mock_task.project_id = "456"
        mock_task.labels = ["label1", "label2"]
        mock_task.priority = 2
        mock_task.due = None
        mock_api.get_tasks.return_value = [mock_task]

        client = TodoistClient("fake_token")

        # Execute
        result = client.get_tasks(project_id="456")

        # Verify
        mock_api.get_tasks.assert_called_once_with(project_id="456")
        assert len(result) == 1
        assert result[0]["id"] == "123"
        assert result[0]["content"] == "Test task"
        assert result[0]["project_id"] == "456"
        assert result[0]["labels"] == ["label1", "label2"]

    @patch("apps.server.integrations.todoist_client.TodoistAPI")
    def test_get_projects_calls_api_and_converts(self, mock_api_class):
        """Test that get_projects() calls the API and converts results."""
        # Setup mock
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        # Mock project object from todoist-python
        mock_project = Mock()
        mock_project.id = "789"
        mock_project.name = "Test Project"
        mock_project.color = "blue"
        mock_api.get_projects.return_value = [mock_project]

        client = TodoistClient("fake_token")

        # Execute
        result = client.get_projects()

        # Verify
        mock_api.get_projects.assert_called_once()
        assert len(result) == 1
        assert result[0]["id"] == "789"
        assert result[0]["name"] == "Test Project"
        assert result[0]["color"] == "blue"

    @patch("apps.server.integrations.todoist_client.TodoistAPI")
    def test_task_conversion_handles_due_date(self, mock_api_class):
        """Test that task conversion properly handles due dates."""
        # Setup mock
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        # Mock task with due date
        mock_task = Mock()
        mock_task.id = "123"
        mock_task.content = "Test task"
        mock_task.project_id = "456"
        mock_task.labels = []
        mock_task.priority = 1

        # Mock due date object
        mock_due = Mock()
        mock_due.date = "2023-12-01"
        mock_due.string = "Dec 1"
        mock_task.due = mock_due

        mock_api.get_tasks.return_value = [mock_task]

        client = TodoistClient("fake_token")
        result = client.get_tasks()

        assert result[0]["due"] == {"date": "2023-12-01", "string": "Dec 1"}

    @patch("apps.server.integrations.todoist_client.TodoistAPI")
    def test_task_conversion_handles_no_due_date(self, mock_api_class):
        """Test that task conversion handles tasks without due dates."""
        # Setup mock
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        # Mock task without due date
        mock_task = Mock()
        mock_task.id = "123"
        mock_task.content = "Test task"
        mock_task.project_id = "456"
        mock_task.labels = []
        mock_task.priority = 1
        mock_task.due = None

        mock_api.get_tasks.return_value = [mock_task]

        client = TodoistClient("fake_token")
        result = client.get_tasks()

        assert result[0]["due"] is None
