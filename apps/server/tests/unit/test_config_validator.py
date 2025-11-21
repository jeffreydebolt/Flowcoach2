"""Unit tests for configuration validation."""

import unittest
from unittest.mock import patch

from apps.server.core.config_validator import (
    ConfigValidator,
    ValidationResult,
    validate_startup_config,
)


class TestConfigValidator(unittest.TestCase):
    """Test configuration validation functionality."""

    def test_valid_minimal_config(self):
        """Test validation with minimal valid configuration."""
        env_vars = {
            "TODOIST_API_TOKEN": "test-todoist-token",
            "CLAUDE_API_KEY": "test-claude-key",
        }

        result = ConfigValidator.validate_config(env_vars)

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.required_missing), 0)
        self.assertTrue(len(result.optional_missing) > 0)  # Should have optional missing

    def test_missing_required_keys(self):
        """Test validation with missing required keys."""
        env_vars = {
            "CLAUDE_API_KEY": "test-claude-key",
            # Missing TODOIST_API_TOKEN
        }

        result = ConfigValidator.validate_config(env_vars)

        self.assertFalse(result.is_valid)
        self.assertIn("TODOIST_API_TOKEN", result.required_missing)
        self.assertEqual(len(result.required_missing), 1)

    def test_empty_values_treated_as_missing(self):
        """Test that empty string values are treated as missing."""
        env_vars = {
            "TODOIST_API_TOKEN": "",  # Empty string
            "CLAUDE_API_KEY": "   ",  # Whitespace only
        }

        result = ConfigValidator.validate_config(env_vars)

        self.assertFalse(result.is_valid)
        self.assertIn("TODOIST_API_TOKEN", result.required_missing)
        self.assertIn("CLAUDE_API_KEY", result.required_missing)
        self.assertEqual(len(result.required_missing), 2)

    def test_complete_valid_config(self):
        """Test validation with complete configuration."""
        env_vars = {
            # Required
            "TODOIST_API_TOKEN": "test-todoist-token",
            "CLAUDE_API_KEY": "test-claude-key",
            # Optional
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_APP_TOKEN": "xapp-test-token",
            "FC_DEFAULT_PROJECT": "123456789",
            "FC_ACTIVE_USERS": "U123456,U789012",
            "FC_DEFAULT_TIMEZONE": "America/Denver",
            "FC_DB_PATH": "./test.db",
            "FC_LABEL_MODE": "labels",
            "FC_TIME_BUCKETS": "2min:5,10min:15,30plus:999",
            "LOG_LEVEL": "info",
        }

        result = ConfigValidator.validate_config(env_vars)

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.required_missing), 0)
        self.assertEqual(len(result.optional_missing), 0)
        self.assertEqual(len(result.warnings), 0)

    def test_slack_configuration_warnings(self):
        """Test Slack configuration validation warnings."""
        # Test SLACK_BOT_TOKEN without FC_ACTIVE_USERS
        env_vars = {
            "TODOIST_API_TOKEN": "test-token",
            "CLAUDE_API_KEY": "test-key",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            # Missing FC_ACTIVE_USERS
        }

        result = ConfigValidator.validate_config(env_vars)

        self.assertTrue(result.is_valid)
        self.assertTrue(any("FC_ACTIVE_USERS not set" in warning for warning in result.warnings))

        # Test SLACK_APP_TOKEN without SLACK_BOT_TOKEN
        env_vars = {
            "TODOIST_API_TOKEN": "test-token",
            "CLAUDE_API_KEY": "test-key",
            "SLACK_APP_TOKEN": "xapp-test-token",
            # Missing SLACK_BOT_TOKEN
        }

        result = ConfigValidator.validate_config(env_vars)

        self.assertTrue(result.is_valid)
        self.assertTrue(any("SLACK_BOT_TOKEN missing" in warning for warning in result.warnings))

    def test_time_buckets_validation(self):
        """Test time buckets format validation."""
        # Valid format
        env_vars = {
            "TODOIST_API_TOKEN": "test-token",
            "CLAUDE_API_KEY": "test-key",
            "FC_TIME_BUCKETS": "2min:5,10min:15,30plus:999",
        }

        result = ConfigValidator.validate_config(env_vars)
        self.assertTrue(result.is_valid)

        # Invalid format - no colon
        env_vars["FC_TIME_BUCKETS"] = "2min_5,10min_15"
        result = ConfigValidator.validate_config(env_vars)
        self.assertTrue(
            any("FC_TIME_BUCKETS format invalid" in warning for warning in result.warnings)
        )

        # Invalid format - non-numeric minutes
        env_vars["FC_TIME_BUCKETS"] = "2min:abc,10min:15"
        result = ConfigValidator.validate_config(env_vars)
        self.assertTrue(
            any("FC_TIME_BUCKETS format invalid" in warning for warning in result.warnings)
        )

    def test_timezone_validation(self):
        """Test timezone validation."""
        valid_timezones = [
            "America/Denver",
            "Europe/London",
            "Asia/Tokyo",
            "Pacific/Auckland",
            "UTC",
            "GMT",
        ]

        for timezone in valid_timezones:
            with self.subTest(timezone=timezone):
                env_vars = {
                    "TODOIST_API_TOKEN": "test-token",
                    "CLAUDE_API_KEY": "test-key",
                    "FC_DEFAULT_TIMEZONE": timezone,
                }

                result = ConfigValidator.validate_config(env_vars)
                timezone_warnings = [
                    w for w in result.warnings if "FC_DEFAULT_TIMEZONE may be invalid" in w
                ]
                self.assertEqual(
                    len(timezone_warnings),
                    0,
                    f"Valid timezone {timezone} should not generate warnings",
                )

        # Invalid timezone
        env_vars = {
            "TODOIST_API_TOKEN": "test-token",
            "CLAUDE_API_KEY": "test-key",
            "FC_DEFAULT_TIMEZONE": "Invalid/Timezone",
        }

        result = ConfigValidator.validate_config(env_vars)
        self.assertTrue(
            any("FC_DEFAULT_TIMEZONE may be invalid" in warning for warning in result.warnings)
        )

    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ["debug", "info", "warning", "error", "DEBUG", "INFO"]

        for level in valid_levels:
            with self.subTest(level=level):
                env_vars = {
                    "TODOIST_API_TOKEN": "test-token",
                    "CLAUDE_API_KEY": "test-key",
                    "LOG_LEVEL": level,
                }

                result = ConfigValidator.validate_config(env_vars)
                log_warnings = [w for w in result.warnings if "LOG_LEVEL invalid" in w]
                self.assertEqual(
                    len(log_warnings), 0, f"Valid log level {level} should not generate warnings"
                )

        # Invalid log level
        env_vars = {
            "TODOIST_API_TOKEN": "test-token",
            "CLAUDE_API_KEY": "test-key",
            "LOG_LEVEL": "invalid_level",
        }

        result = ConfigValidator.validate_config(env_vars)
        self.assertTrue(any("LOG_LEVEL invalid" in warning for warning in result.warnings))

    def test_validation_result_properties(self):
        """Test ValidationResult helper properties."""
        # No warnings
        result = ValidationResult(
            is_valid=True, required_missing=[], optional_missing=[], warnings=[]
        )
        self.assertFalse(result.has_warnings)

        # Has optional missing
        result = ValidationResult(
            is_valid=True, required_missing=[], optional_missing=["SLACK_BOT_TOKEN"], warnings=[]
        )
        self.assertTrue(result.has_warnings)

        # Has warnings
        result = ValidationResult(
            is_valid=True, required_missing=[], optional_missing=[], warnings=["Test warning"]
        )
        self.assertTrue(result.has_warnings)

    @patch("builtins.print")
    def test_print_validation_report(self, mock_print):
        """Test that validation report prints correctly."""
        result = ValidationResult(
            is_valid=False,
            required_missing=["TODOIST_API_TOKEN"],
            optional_missing=["SLACK_BOT_TOKEN"],
            warnings=["Test warning"],
        )

        ConfigValidator.print_validation_report(result)

        # Check that print was called
        self.assertTrue(mock_print.called)

        # Check that appropriate messages are in the output
        all_output = " ".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("Configuration has required errors", all_output)
        self.assertIn("TODOIST_API_TOKEN", all_output)
        self.assertIn("Test warning", all_output)

    @patch("apps.server.core.config_validator.ConfigValidator.validate_and_report")
    def test_validate_startup_config(self, mock_validate_and_report):
        """Test validate_startup_config function."""
        # Test successful validation
        mock_validate_and_report.return_value = ValidationResult(
            is_valid=True, required_missing=[], optional_missing=[], warnings=[]
        )

        result = validate_startup_config()
        self.assertTrue(result)

        # Test failed validation
        mock_validate_and_report.return_value = ValidationResult(
            is_valid=False, required_missing=["TODOIST_API_TOKEN"], optional_missing=[], warnings=[]
        )

        result = validate_startup_config()
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
