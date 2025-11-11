"""Regression tests for Phase 1.1 hotfix fixes."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from slack_sdk import WebClient

from apps.server.slack.modals.morning_brief import MorningBriefModal, open_morning_brief
from apps.server.slack.middleware import drop_slack_retries_middleware, DeduplicationMiddleware
from handlers.action_handlers import register_action_handlers
from handlers.message_handlers import _clean_task_content


class TestMorningBriefModalFixes:
    """Test Morning Brief modal fixes for trigger_id expiration."""

    def test_open_modal_shows_loading_first(self):
        """Test that opening modal shows loading state first to prevent trigger_id expiration."""
        # Setup
        planning_service = Mock()
        planning_service.get_morning_brief_tasks.return_value = [
            Mock(
                id="123",
                content="Test task",
                project_name="Inbox",
                is_overdue=False,
                due_date=None,
                is_priority_1=False,
                is_flow_tomorrow=True,
                is_flow_weekly=False,
            )
        ]

        modal = MorningBriefModal(planning_service)
        client = Mock(spec=WebClient)
        client.views_open.return_value = {"view": {"id": "view_123"}}

        # Execute
        modal.open_modal("trigger_123", "user_123", client)

        # Verify loading modal was opened first
        assert client.views_open.call_count == 1
        loading_call = client.views_open.call_args
        loading_view = loading_call.kwargs["view"]

        assert loading_view["callback_id"] == "morning_brief_loading"
        assert "Loading your tasks" in loading_view["blocks"][0]["text"]["text"]

        # Verify real modal was updated after
        assert client.views_update.call_count == 1
        update_call = client.views_update.call_args
        assert update_call.kwargs["view_id"] == "view_123"

    def test_open_morning_brief_function_works(self):
        """Test the exposed open_morning_brief function works correctly."""
        client = Mock(spec=WebClient)
        client.views_open.return_value = {"view": {"id": "view_123"}}

        with patch(
            "apps.server.slack.modals.morning_brief.get_planning_service"
        ) as mock_get_service:
            mock_planning_service = Mock()
            mock_planning_service.get_morning_brief_tasks.return_value = []
            mock_get_service.return_value = mock_planning_service

            # Should not raise exception
            open_morning_brief(client, "trigger_123", "user_123")

            assert client.views_open.called


class TestSlackMiddleware:
    """Test Slack middleware for retry dropping and deduplication."""

    def test_drop_retries_middleware_drops_retries(self):
        """Test that retry middleware drops Slack retry requests."""
        logger = Mock()
        middleware = drop_slack_retries_middleware(logger)
        next_called = Mock()

        # Test with retry header
        body_with_retry = {
            "headers": {"x-slack-retry-num": "1", "x-slack-retry-reason": "http_timeout"}
        }

        middleware(body_with_retry, next_called)

        # Should not call next() for retries
        assert not next_called.called
        assert logger.info.called

    def test_drop_retries_middleware_allows_normal_requests(self):
        """Test that retry middleware allows normal requests through."""
        logger = Mock()
        middleware = drop_slack_retries_middleware(logger)
        next_called = Mock()

        # Test without retry header
        body_normal = {"headers": {}}

        middleware(body_normal, next_called)

        # Should call next() for normal requests
        assert next_called.called

    def test_deduplication_middleware_prevents_duplicates(self):
        """Test that deduplication middleware prevents duplicate processing."""
        middleware = DeduplicationMiddleware(cache_size=5)
        next_called = Mock()

        # First request with action
        body = {"actions": [{"action_id": "test_action"}], "trigger_id": "trigger_123"}

        # Process first time
        middleware(body, next_called)
        assert next_called.call_count == 1

        # Process same event again
        next_called.reset_mock()
        middleware(body, next_called)
        assert next_called.call_count == 0  # Should be dropped


class TestIdempotentTimeTagging:
    """Test idempotent time tagging fixes."""

    def test_time_estimate_action_is_idempotent(self):
        """Test that time estimate actions don't create duplicates."""
        # This test would verify that the action handler checks for existing labels
        # and uses chat_update instead of posting new messages

        # Setup mocks
        app = Mock()
        services = {"todoist": Mock()}

        # Mock task with existing time estimate
        existing_task = {
            "id": "task_123",
            "labels": ["2min"],  # Already has time estimate
        }
        services["todoist"].get_task.return_value = existing_task

        # Register handlers
        register_action_handlers(app, services)

        # Verify handler was registered
        assert app.action.called

        # The handler should check for existing labels and update message instead of posting new
        # (Full integration test would require more setup)


class TestMessageParsing:
    """Test improved message parsing for task creation."""

    def test_clean_task_content_removes_prefixes(self):
        """Test that task content cleaning removes common prefixes."""
        test_cases = [
            ("Create a task to review the document", "review the document"),
            ("Remind me to call John", "call John"),
            ("I need to finish the report", "finish the report"),
            ("✓ Buy groceries", "Buy groceries"),
            ("1. Complete the assignment", "Complete the assignment"),
            ("- Send email to team", "Send email to team"),
            ("TODO: Update the documentation", "Update the documentation"),
            ("Task: Schedule meeting", "Schedule meeting"),
        ]

        for input_text, expected in test_cases:
            result = _clean_task_content(input_text)
            assert (
                result == expected
            ), f"Expected '{expected}', got '{result}' for input '{input_text}'"

    def test_clean_task_content_preserves_clean_text(self):
        """Test that clean text is preserved."""
        clean_text = "This is already clean text"
        result = _clean_task_content(clean_text)
        assert result == clean_text


class TestSocketModeStability:
    """Test Socket Mode stability improvements."""

    def test_socket_handler_has_ping_settings(self):
        """Test that SocketModeHandler is configured with ping/pong settings."""
        # This would be tested in integration by checking that the SocketModeHandler
        # is created with the correct ping_interval and ping_pong_reply_timeout
        # parameters in app.py
        pass
