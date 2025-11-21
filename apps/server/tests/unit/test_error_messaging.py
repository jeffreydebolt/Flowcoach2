"""Unit tests for improved error messaging."""

import json
import unittest

from apps.server.core.errors import (
    FlowCoachError,
    InvalidTokenError,
    MissingConfigError,
    SlackError,
    TodoistError,
    format_console_error,
    format_user_error,
    get_slack_fallback_message,
)


class TestFlowCoachErrors(unittest.TestCase):
    """Test FlowCoach custom error classes."""

    def test_base_flowcoach_error(self):
        """Test base FlowCoach error functionality."""
        error = FlowCoachError(
            "Test error message", user_hint="This is a helpful hint", error_code="TEST_ERROR"
        )

        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.user_hint, "This is a helpful hint")
        self.assertEqual(error.error_code, "TEST_ERROR")

    def test_missing_config_error(self):
        """Test MissingConfigError formatting."""
        error = MissingConfigError("TODOIST_API_TOKEN")

        self.assertIn("TODOIST_API_TOKEN", str(error))
        self.assertIn("Add TODOIST_API_TOKEN to your .env file", error.user_hint)
        self.assertEqual(error.error_code, "CONFIG_MISSING")

        # Test with description
        error_with_desc = MissingConfigError("SLACK_BOT_TOKEN", "Required for Slack integration")
        self.assertIn("Required for Slack integration", error_with_desc.user_hint)

    def test_invalid_token_error(self):
        """Test InvalidTokenError formatting."""
        error = InvalidTokenError("Todoist")

        self.assertIn("Invalid or expired Todoist token", str(error))
        self.assertIn("Check your Todoist API token in .env file", error.user_hint)
        self.assertEqual(error.error_code, "TOKEN_INVALID")

        # Test with custom hint
        error_custom = InvalidTokenError("Slack", "Try regenerating your token")
        self.assertEqual(error_custom.user_hint, "Try regenerating your token")

    def test_todoist_error_status_codes(self):
        """Test TodoistError with different status codes."""
        # 401 Unauthorized
        error_401 = TodoistError("Unauthorized", status_code=401)
        self.assertIn("Check TODOIST_API_TOKEN", error_401.user_hint)
        self.assertEqual(error_401.error_code, "TODOIST_AUTH")

        # 403 Forbidden
        error_403 = TodoistError("Forbidden", status_code=403)
        self.assertIn("check your subscription", error_403.user_hint)
        self.assertEqual(error_403.error_code, "TODOIST_FORBIDDEN")

        # 429 Rate Limited
        error_429 = TodoistError("Rate limited", status_code=429)
        self.assertIn("try again later", error_429.user_hint)
        self.assertEqual(error_429.error_code, "TODOIST_RATE_LIMIT")

        # Generic error
        error_generic = TodoistError("Unknown error")
        self.assertIn("Check your Todoist configuration", error_generic.user_hint)
        self.assertEqual(error_generic.error_code, "TODOIST_ERROR")

    def test_slack_error_types(self):
        """Test SlackError with different Slack error types."""
        # Token revoked
        error_revoked = SlackError("Token revoked", slack_error="token_revoked")
        self.assertIn("regenerate SLACK_BOT_TOKEN", error_revoked.user_hint)
        self.assertEqual(error_revoked.error_code, "SLACK_TOKEN_REVOKED")

        # Account inactive
        error_inactive = SlackError("Account inactive", slack_error="account_inactive")
        self.assertIn("workspace status", error_inactive.user_hint)
        self.assertEqual(error_inactive.error_code, "SLACK_ACCOUNT_INACTIVE")

        # Channel not found
        error_channel = SlackError("Channel not found", slack_error="channel_not_found")
        self.assertIn("FC_ACTIVE_USERS", error_channel.user_hint)
        self.assertEqual(error_channel.error_code, "SLACK_CHANNEL_NOT_FOUND")

        # Not authenticated
        error_auth = SlackError("Not authenticated", slack_error="not_authed")
        self.assertIn("SLACK_BOT_TOKEN", error_auth.user_hint)
        self.assertEqual(error_auth.error_code, "SLACK_AUTH")

        # Generic error
        error_generic = SlackError("Unknown error")
        self.assertIn("Check your Slack configuration", error_generic.user_hint)
        self.assertEqual(error_generic.error_code, "SLACK_ERROR")


class TestErrorFormatting(unittest.TestCase):
    """Test error formatting utilities."""

    def test_format_user_error(self):
        """Test user-friendly error formatting."""
        # Error with hint
        error_with_hint = FlowCoachError("Something went wrong", user_hint="Try this solution")

        formatted = format_user_error(error_with_hint)
        self.assertIn("❌", formatted)
        self.assertIn("💡", formatted)
        self.assertIn("Something went wrong", formatted)
        self.assertIn("Try this solution", formatted)

        # Error without hint
        error_no_hint = FlowCoachError("Simple error")
        formatted_no_hint = format_user_error(error_no_hint)
        self.assertIn("❌", formatted_no_hint)
        self.assertNotIn("💡", formatted_no_hint)
        self.assertIn("Simple error", formatted_no_hint)

    def test_format_console_error(self):
        """Test console error formatting."""
        error = FlowCoachError(
            "Console error", user_hint="Console hint", error_code="CONSOLE_ERROR"
        )

        formatted = format_console_error(error)
        self.assertIn("ERROR:", formatted)
        self.assertIn("Console error", formatted)
        self.assertIn("Code: CONSOLE_ERROR", formatted)
        self.assertIn("SUGGESTION:", formatted)
        self.assertIn("Console hint", formatted)

        # Test without error code
        error_no_code = FlowCoachError("Error without code", user_hint="Hint")
        formatted_no_code = format_console_error(error_no_code)
        self.assertNotIn("Code:", formatted_no_code)
        self.assertIn("SUGGESTION:", formatted_no_code)

    def test_get_slack_fallback_message(self):
        """Test Slack fallback message generation."""
        # FlowCoach error
        flowcoach_error = MissingConfigError("TEST_TOKEN")
        message = get_slack_fallback_message(flowcoach_error)

        self.assertIn("blocks", message)
        self.assertEqual(len(message["blocks"]), 2)

        # Check message content
        message_text = message["blocks"][0]["text"]["text"]
        self.assertIn("❌", message_text)
        self.assertIn("💡", message_text)
        self.assertIn("TEST_TOKEN", message_text)

        # Check context
        context_text = message["blocks"][1]["elements"][0]["text"]
        self.assertIn("check the logs", context_text)

        # Generic error
        generic_error = ValueError("Generic error")
        generic_message = get_slack_fallback_message(generic_error)

        generic_text = generic_message["blocks"][0]["text"]["text"]
        self.assertIn("❌", generic_text)
        self.assertIn("Something went wrong", generic_text)
        self.assertIn("Generic error", generic_text)

    def test_slack_message_json_serializable(self):
        """Test that Slack fallback messages are JSON serializable."""
        error = TodoistError("Test error", status_code=401)
        message = get_slack_fallback_message(error)

        # Should not raise an exception
        json_str = json.dumps(message)

        # Should be able to parse back
        parsed = json.loads(json_str)
        self.assertEqual(parsed, message)


class TestErrorInheritance(unittest.TestCase):
    """Test error class inheritance and compatibility."""

    def test_error_inheritance(self):
        """Test that all custom errors inherit from appropriate base classes."""
        # All should be FlowCoach errors
        self.assertIsInstance(MissingConfigError("TEST"), FlowCoachError)
        self.assertIsInstance(InvalidTokenError("TEST"), FlowCoachError)
        self.assertIsInstance(TodoistError("TEST"), FlowCoachError)
        self.assertIsInstance(SlackError("TEST"), FlowCoachError)

        # All should be standard exceptions
        self.assertIsInstance(MissingConfigError("TEST"), Exception)
        self.assertIsInstance(InvalidTokenError("TEST"), Exception)
        self.assertIsInstance(TodoistError("TEST"), Exception)
        self.assertIsInstance(SlackError("TEST"), Exception)

    def test_error_catching(self):
        """Test that errors can be caught appropriately."""
        # Test catching specific error
        with self.assertRaises(MissingConfigError):
            raise MissingConfigError("TEST_TOKEN")

        # Test catching base FlowCoach error
        with self.assertRaises(FlowCoachError):
            raise TodoistError("Test error")

        # Test catching generic exception
        with self.assertRaises(Exception):
            raise SlackError("Test error")

    def test_error_attributes_preserved(self):
        """Test that error attributes are preserved when caught."""
        try:
            raise InvalidTokenError("TestService", "Custom hint")
        except FlowCoachError as e:
            self.assertEqual(e.user_hint, "Custom hint")
            self.assertEqual(e.error_code, "TOKEN_INVALID")

        try:
            raise TodoistError("Test message", status_code=429)
        except TodoistError as e:
            self.assertIn("try again later", e.user_hint)
            self.assertEqual(e.error_code, "TODOIST_RATE_LIMIT")


if __name__ == "__main__":
    unittest.main()
