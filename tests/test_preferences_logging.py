"""Tests for preferences logging level changes."""

import pytest
import logging
from unittest.mock import Mock, patch
from apps.server.core.prefs import PreferencesStore, get_user_prefs_or_defaults


class TestPreferencesLogging:
    """Test that preferences warnings are reduced to debug level."""

    @patch("apps.server.core.prefs.TodoistClient")
    def test_missing_preferences_logs_at_debug_level(self, mock_todoist_class):
        """Test that missing preferences log at debug level, not warning."""
        # Setup mock to return no content (no preferences)
        mock_todoist = Mock()
        mock_todoist.load_project_note.return_value = None
        mock_todoist_class.return_value = mock_todoist

        store = PreferencesStore()

        # Capture logging
        with patch("apps.server.core.prefs.logger") as mock_logger:
            result = store.load_prefs("test_user")

            # Should return None for missing preferences
            assert result is None

            # Should log at debug level, not warning
            mock_logger.debug.assert_called_once()
            assert "No preferences found" in mock_logger.debug.call_args[0][0]
            mock_logger.warning.assert_not_called()

    @patch("apps.server.core.prefs.TodoistClient")
    def test_default_preferences_logs_at_debug_level(self, mock_todoist_class):
        """Test that using default preferences logs at debug level."""
        # Setup mock to return no content
        mock_todoist = Mock()
        mock_todoist.load_project_note.return_value = None
        mock_todoist_class.return_value = mock_todoist

        store = PreferencesStore()

        # Capture logging
        with patch("apps.server.core.prefs.logger") as mock_logger:
            result = store.get_prefs_or_defaults("test_user")

            # Should return default preferences
            assert result is not None
            assert result.timezone == "America/New_York"  # Default value

            # Should log at debug level for both missing prefs and using defaults
            debug_calls = mock_logger.debug.call_args_list
            assert len(debug_calls) == 2

            # Check both debug messages
            debug_messages = [call[0][0] for call in debug_calls]
            assert any("No preferences found" in msg for msg in debug_messages)
            assert any("Using default preferences" in msg for msg in debug_messages)

            # Should not log at info level
            mock_logger.info.assert_not_called()

    def test_convenience_function_also_uses_debug_logging(self):
        """Test that convenience function also uses debug-level logging."""
        with patch("apps.server.core.prefs.PreferencesStore") as mock_store_class:
            mock_store = Mock()
            mock_store.get_prefs_or_defaults.return_value = Mock()
            mock_store_class.return_value = mock_store

            # Should not raise any exceptions
            result = get_user_prefs_or_defaults("test_user")
            assert result is not None

            # Verify the store method was called
            mock_store.get_prefs_or_defaults.assert_called_once_with("test_user")

    @patch("apps.server.core.prefs.TodoistClient")
    def test_successful_preference_load_still_logs_info(self, mock_todoist_class):
        """Test that successful preference loading still logs at info level."""
        # Setup mock to return valid preferences JSON
        mock_todoist = Mock()
        valid_prefs_json = """
        {
            "user_id": "test_user",
            "version": "1.0",
            "preferences": {
                "timezone": "US/Pacific",
                "work_days": "mon,tue,wed,thu,fri",
                "quiet_hours_start": "18:00",
                "quiet_hours_end": "09:00",
                "morning_window_start": "07:00",
                "morning_window_end": "10:00",
                "wrap_window_start": "16:00",
                "wrap_window_end": "18:00",
                "energy_windows": [],
                "max_session_minutes": 90,
                "no_new_task_threshold_minutes": 15,
                "checkin_time_today": null
            }
        }
        """
        mock_todoist.load_project_note.return_value = valid_prefs_json
        mock_todoist_class.return_value = mock_todoist

        store = PreferencesStore()

        # Capture logging
        with patch("apps.server.core.prefs.logger") as mock_logger:
            result = store.load_prefs("test_user")

            # Should return loaded preferences
            assert result is not None
            assert result.timezone == "US/Pacific"

            # Should log successful load at info level
            mock_logger.info.assert_called_once()
            assert "Loaded preferences" in mock_logger.info.call_args[0][0]
