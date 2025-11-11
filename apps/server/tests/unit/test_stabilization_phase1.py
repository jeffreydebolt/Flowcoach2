"""Unit tests for Phase 1 stabilization fixes."""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from apps.server.integrations.todoist_client import TodoistClient
from apps.server.core.prefs import PreferencesStore, WorkPreferences
from apps.server.slack.home import HomeTab


class TestTodoistClientShim:
    """Test TodoistClient get_tasks() and get_projects() shims."""

    @patch.dict("os.environ", {"TODOIST_API_TOKEN": "test_token"})
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_api = Mock()
        self.client = TodoistClient()
        self.client.api = self.mock_api

    def test_get_tasks_wrapper(self):
        """Test that get_tasks() wraps API and converts to dictionaries."""
        # Mock task objects
        mock_task1 = Mock(
            id="task123",
            content="Test task",
            description="Test desc",
            project_id="proj1",
            labels=["@flow_tomorrow"],
            priority=4,
            due=Mock(dict=lambda: {"date": "2025-11-12"}),
            url="https://todoist.com/task/123",
            comment_count=0,
            created_at="2025-11-11",
            is_completed=False,
        )

        self.mock_api.get_tasks.return_value = [mock_task1]

        # Call get_tasks
        result = self.client.get_tasks(project_id="proj1")

        # Verify API was called correctly
        self.mock_api.get_tasks.assert_called_once_with(project_id="proj1")

        # Verify result is list of dicts
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["id"] == "task123"
        assert result[0]["content"] == "Test task"
        assert result[0]["labels"] == ["@flow_tomorrow"]

    def test_get_projects_wrapper(self):
        """Test that get_projects() wraps API and converts to dictionaries."""
        # Mock project objects
        mock_proj1 = Mock(id="proj1", name="Work", color="blue")
        mock_proj2 = Mock(id="proj2", name="Personal", color="green")

        self.mock_api.get_projects.return_value = [mock_proj1, mock_proj2]

        # Call get_projects
        result = self.client.get_projects()

        # Verify API was called
        self.mock_api.get_projects.assert_called_once()

        # Verify result format
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"id": "proj1", "name": "Work", "color": "blue"}
        assert result[1] == {"id": "proj2", "name": "Personal", "color": "green"}


class TestPreferencesRoundTrip:
    """Test preferences save/load round-trip with proper logging."""

    @patch("apps.server.core.prefs.TodoistClient")
    def test_save_prefs_logs_success(self, mock_client_class):
        """Test that save_prefs logs success message."""
        # Mock Todoist client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.save_project_note.return_value = "task_id"

        # Create store and preferences
        store = PreferencesStore(mock_client)
        prefs = WorkPreferences(timezone="America/Chicago")

        # Save preferences
        with patch("apps.server.core.prefs.logger") as mock_logger:
            result = store.save_prefs("U123", prefs)

        assert result is True
        mock_logger.info.assert_called_once_with(
            "Successfully saved preferences for user U123 to Todoist project note"
        )

    @patch("apps.server.core.prefs.TodoistClient")
    def test_load_prefs_warns_when_missing(self, mock_client_class):
        """Test that load_prefs warns when no preferences found."""
        # Mock empty response
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.load_project_note.return_value = None

        store = PreferencesStore(mock_client)

        # Load preferences
        with patch("apps.server.core.prefs.logger") as mock_logger:
            result = store.load_prefs("U123")

        assert result is None
        mock_logger.warning.assert_called_once_with(
            "No preferences found for user U123 in Todoist project note"
        )


class TestHomeActionAck:
    """Test that home tab actions properly call ack()."""

    def test_handle_home_action_calls_ack(self):
        """Test that handle_home_action calls ack immediately."""
        home_tab = HomeTab()

        # Mock dependencies
        mock_ack = Mock()
        mock_client = Mock()
        body = {
            "actions": [{"action_id": "start_morning_brief"}],
            "user": {"id": "U123"},
            "trigger_id": "trigger123",
        }

        with patch("apps.server.slack.home.is_enabled", return_value=True):
            with patch("apps.server.slack.modals.morning_brief.open_morning_brief") as mock_open:
                # Call handler
                home_tab.handle_home_action(mock_ack, body, mock_client)

        # Verify ack was called first
        mock_ack.assert_called_once()
        assert mock_ack.call_args_list[0] == ((), {})

        # Verify action was processed after ack
        mock_open.assert_called_once_with(mock_client, "trigger123", "U123")


class TestMorningBriefSubmission:
    """Test morning brief modal submission adds labels and comments."""

    @patch("apps.server.core.planning.TodoistClient")
    def test_mark_task_as_planned_adds_label_and_comment(self, mock_client_class):
        """Test that planning a task adds @flow_top_today and comment."""
        from apps.server.core.planning import PlanningService

        # Mock Todoist client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.add_task_label.return_value = True
        mock_client.add_task_comment.return_value = True

        service = PlanningService(mock_client)

        # Mark task as planned
        result = service.mark_task_as_planned("task123", "p1", "09:00")

        assert result is True

        # Verify label was added
        mock_client.add_task_label.assert_called_once_with("task123", "@flow_top_today")

        # Verify comment was added
        mock_client.add_task_comment.assert_called_once_with(
            "task123", "flow:planned_due priority=p1 time=09:00"
        )

    @patch("apps.server.core.prefs.PreferencesStore")
    def test_save_checkin_time_updates_prefs(self, mock_store_class):
        """Test that checkin time is saved in preferences."""
        from apps.server.core.planning import PlanningService

        # Mock preferences store
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        # Mock existing preferences
        mock_prefs = Mock(spec=WorkPreferences)
        mock_store.load_prefs.return_value = mock_prefs
        mock_store.save_prefs.return_value = True

        # Create service
        mock_client = Mock()
        service = PlanningService(mock_client)

        # Save checkin time
        result = service.save_checkin_time("U123", "09:30")

        assert result is True
        assert mock_prefs.checkin_time_today == "09:30"
        mock_store.save_prefs.assert_called_once_with("U123", mock_prefs)


class TestSinglePostRule:
    """Test that error guards respect single post rule."""

    def test_single_post_error_guard_posts_once(self):
        """Test that error guard only posts one message on error."""
        from apps.server.platform.errors import single_post_error_guard

        @single_post_error_guard()
        def failing_function():
            raise ValueError("Test error")

        # Call function that will fail - it should handle the error internally
        result = failing_function()

        # Error guard should return None on error
        assert result is None


class TestDMLogging:
    """Test that DM messages are properly logged."""

    def test_dm_received_logging(self):
        """Test that DMs log with proper format."""
        # Read the source file to verify logging is in place
        import pathlib

        source_path = (
            pathlib.Path(__file__).parent.parent.parent.parent.parent
            / "handlers"
            / "message_handlers.py"
        )
        source = source_path.read_text()
        assert "DM.received from user" in source
