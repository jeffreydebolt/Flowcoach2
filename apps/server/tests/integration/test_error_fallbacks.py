"""Integration tests for error fallback messaging."""

import json
import unittest
from unittest.mock import MagicMock, Mock, patch

from apps.server.core.errors import (
    InvalidTokenError,
    MissingConfigError,
    TodoistError,
    get_slack_fallback_message,
)
from apps.server.slack.messages import MessageBuilder


class TestSlackErrorFallbacks(unittest.TestCase):
    """Test error fallback messages in Slack integration."""

    def setUp(self):
        """Set up test environment."""
        # Mock file system for MessageBuilder
        self.mock_phrases = {
            "morning_brief": {"intros": ["Good morning!"], "outros": ["Have a great day!"]}
        }

        self.mock_template = {
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "{intro}"}}]
        }

    @patch("apps.server.slack.messages.Path")
    @patch("builtins.open")
    def test_message_builder_fallback_integration(self, mock_open_func, mock_path):
        """Test that MessageBuilder can handle error scenarios gracefully."""
        # Mock file system
        mock_path.return_value.parent.parent = Mock()

        def mock_open_side_effect(*args, **kwargs):
            if "phrases.json" in str(args[0]):
                return MagicMock(read=Mock(return_value=json.dumps(self.mock_phrases)))
            else:
                return MagicMock(read=Mock(return_value=json.dumps(self.mock_template)))

        mock_open_func.side_effect = mock_open_side_effect

        # Create builder
        builder = MessageBuilder()

        # Test fallback messages
        fallback_types = ["todoist", "no_tasks", "general"]

        for fallback_type in fallback_types:
            with self.subTest(fallback_type=fallback_type):
                message = builder.build_fallback_message(fallback_type)

                # Should have valid structure
                self.assertIn("blocks", message)
                self.assertIsInstance(message["blocks"], list)
                self.assertTrue(len(message["blocks"]) > 0)

                # Should be JSON serializable
                json.dumps(message)

    def test_slack_fallback_message_structure(self):
        """Test that Slack fallback messages have correct structure."""
        test_errors = [
            MissingConfigError("TODOIST_API_TOKEN"),
            InvalidTokenError("Slack"),
            TodoistError("API Error", status_code=401),
            Exception("Generic error"),
        ]

        for error in test_errors:
            with self.subTest(error=type(error).__name__):
                message = get_slack_fallback_message(error)

                # Check structure
                self.assertIn("blocks", message)
                self.assertIsInstance(message["blocks"], list)
                self.assertEqual(len(message["blocks"]), 2)

                # Check first block (error message)
                error_block = message["blocks"][0]
                self.assertEqual(error_block["type"], "section")
                self.assertIn("text", error_block)
                self.assertEqual(error_block["text"]["type"], "mrkdwn")

                # Check second block (context)
                context_block = message["blocks"][1]
                self.assertEqual(context_block["type"], "context")
                self.assertIn("elements", context_block)

                # Should be JSON serializable
                json.dumps(message)

    @patch("apps.server.jobs.morning_brief.WebClient")
    @patch("apps.server.jobs.morning_brief.TodoistClient")
    @patch("apps.server.jobs.morning_brief.get_dal")
    def test_morning_brief_error_handling(self, mock_dal, mock_todoist_class, mock_slack_class):
        """Test that morning brief handles errors gracefully with user-friendly messages."""
        from apps.server.jobs.morning_brief import MorningBriefJob

        # Setup mocks
        mock_slack = Mock()
        mock_slack_class.return_value = mock_slack
        mock_slack.users_info.return_value = {"user": {"tz": "America/Denver"}}

        # Make Todoist client raise a configuration error
        mock_todoist_class.side_effect = MissingConfigError("TODOIST_API_TOKEN")

        mock_dal_instance = Mock()
        mock_dal.return_value = mock_dal_instance

        # Create job and try to send morning brief
        try:
            job = MorningBriefJob()
            # This should fail during initialization due to missing config
            self.fail("Expected MissingConfigError to be raised")
        except MissingConfigError as e:
            # Verify error has helpful information
            self.assertIn("TODOIST_API_TOKEN", str(e))
            self.assertIn("Add TODOIST_API_TOKEN to your .env file", e.user_hint)

    def test_error_message_user_friendliness(self):
        """Test that error messages are user-friendly and actionable."""
        # Test configuration errors
        config_error = MissingConfigError("SLACK_BOT_TOKEN", "Required for Slack integration")
        slack_msg = get_slack_fallback_message(config_error)

        message_text = slack_msg["blocks"][0]["text"]["text"]
        self.assertIn("💡", message_text)  # Should have helpful hint
        self.assertIn("Add SLACK_BOT_TOKEN", message_text)  # Should mention specific fix

        # Test API errors
        api_error = TodoistError("Unauthorized", status_code=401)
        api_msg = get_slack_fallback_message(api_error)

        api_text = api_msg["blocks"][0]["text"]["text"]
        self.assertIn("💡", api_text)  # Should have helpful hint
        self.assertIn("Check TODOIST_API_TOKEN", api_text)  # Should mention specific fix

        # Test that generic errors get generic but helpful messages
        generic_error = ValueError("Something broke")
        generic_msg = get_slack_fallback_message(generic_error)

        generic_text = generic_msg["blocks"][0]["text"]["text"]
        self.assertIn("💡", generic_text)  # Should still have helpful hint
        self.assertIn("configuration", generic_text)  # Should suggest checking config

    def test_error_codes_for_monitoring(self):
        """Test that errors include codes for monitoring and debugging."""
        errors_with_codes = [
            (MissingConfigError("TEST_TOKEN"), "CONFIG_MISSING"),
            (InvalidTokenError("TestService"), "TOKEN_INVALID"),
            (TodoistError("Auth failed", status_code=401), "TODOIST_AUTH"),
            (TodoistError("Rate limited", status_code=429), "TODOIST_RATE_LIMIT"),
        ]

        for error, expected_code in errors_with_codes:
            with self.subTest(error=type(error).__name__):
                self.assertEqual(error.error_code, expected_code)

    def test_console_error_formatting(self):
        """Test that console error formatting includes helpful information."""
        from apps.server.core.errors import format_console_error

        error = TodoistError("API request failed", status_code=403)
        console_output = format_console_error(error)

        # Should include all relevant information
        self.assertIn("ERROR:", console_output)
        self.assertIn("API request failed", console_output)
        self.assertIn("Code: TODOIST_FORBIDDEN", console_output)
        self.assertIn("SUGGESTION:", console_output)
        self.assertIn("subscription", console_output)  # Hint about subscription

    @patch("apps.server.core.errors.logger")
    def test_error_logging_integration(self, mock_logger):
        """Test that errors are properly logged for debugging."""
        from apps.server.core.errors import log_event

        # Test logging an error event
        error = InvalidTokenError("Todoist")

        log_event(
            "error",
            "token_validation_failed",
            {
                "error_code": error.error_code,
                "error_message": str(error),
                "user_hint": error.user_hint,
            },
        )

        # Verify logger was called
        mock_logger.info.assert_called()

        # Check that logged data contains useful information
        logged_call = mock_logger.info.call_args[0][0]
        self.assertIn("EVENT:", logged_call)
        self.assertIn("token_validation_failed", logged_call)
        self.assertIn("TOKEN_INVALID", logged_call)


if __name__ == "__main__":
    unittest.main()
