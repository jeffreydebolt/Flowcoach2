"""Acceptance tests for FlowCoach Phase 0 - Interview + Prefs + Home Tab."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import time

from apps.server.core.prefs import WorkPreferences, EnergyWindow, PreferencesStore
from apps.server.platform.feature_flags import FlowCoachFlag, clear_all_overrides, set_override
from apps.server.integrations.todoist_client import TodoistClient
from apps.server.slack.home import HomeTab
from apps.server.slack.modals.interview import InterviewModal


class TestPrefsRoundTrip:
    """Test that preferences round-trip correctly through Todoist storage."""

    def setup_method(self):
        """Reset feature flags before each test."""
        clear_all_overrides()

    @patch("apps.server.core.prefs.TodoistClient")
    def test_prefs_roundtrip_in_todoist_note(self, mock_client_class):
        """Test that preferences can be saved and loaded from Todoist."""
        # Mock Todoist client
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Set up mock responses
        mock_client.save_project_note.return_value = "task_456"
        mock_client.load_project_note.return_value = None  # Will be set later

        # Create test preferences
        test_prefs = WorkPreferences(
            timezone="America/New_York",
            work_days="mon,tue,wed,thu,fri",
            morning_window_start="08:00",
            morning_window_end="10:00",
            wrap_window_start="17:00",
            wrap_window_end="19:00",
            quiet_hours_start="19:00",
            quiet_hours_end="08:00",
            energy_windows=[
                EnergyWindow("deep", "09:00", "11:00", 120),
                EnergyWindow("calls", "14:00", "15:30", 90),
            ],
        )

        # Save preferences
        store = PreferencesStore(mock_client)
        user_id = "U123456"
        success = store.save_prefs(user_id, test_prefs)
        assert success, "Should successfully save preferences"

        # Verify save was called with JSON data
        mock_client.save_project_note.assert_called_once()
        saved_content = mock_client.save_project_note.call_args[0][0]
        saved_data = json.loads(saved_content)

        assert saved_data["user_id"] == user_id
        assert saved_data["version"] == "1.0"
        assert "preferences" in saved_data

        # Mock the load operation
        mock_client.load_project_note.return_value = saved_content

        # Load preferences back
        loaded_prefs = store.load_prefs(user_id)
        assert loaded_prefs is not None, "Should load preferences"

        # Verify all fields match
        assert loaded_prefs.timezone == test_prefs.timezone
        assert loaded_prefs.work_days == test_prefs.work_days
        assert loaded_prefs.morning_window_start == test_prefs.morning_window_start
        assert loaded_prefs.wrap_window_end == test_prefs.wrap_window_end
        assert len(loaded_prefs.energy_windows) == 2
        assert loaded_prefs.energy_windows[0].name == "deep"
        assert loaded_prefs.energy_windows[0].start_time == "09:00"
        assert loaded_prefs.energy_windows[0].max_session_minutes == 120


class TestInterviewModal:
    """Test that interview modal saves valid preferences."""

    def setup_method(self):
        """Reset feature flags before each test."""
        clear_all_overrides()
        set_override(FlowCoachFlag.FC_INTERVIEW_MODAL_V1, True)

    @patch("apps.server.core.prefs.save_user_prefs")
    def test_interview_modal_saves_valid_prefs(self, mock_save_prefs):
        """Test that interview modal creates valid WorkPreferences."""
        mock_save_prefs.return_value = True

        # Mock Slack client
        mock_client = Mock()

        # Create interview handler
        interview = InterviewModal()

        # Simulate completed interview data
        final_data = {
            "timezone": "America/Chicago",
            "work_days": "mon,tue,wed,thu,fri",
            "morning_window_start": "07:30",
            "morning_window_end": "09:30",
            "wrap_window_start": "16:30",
            "wrap_window_end": "18:30",
            "quiet_hours_start": "18:30",
            "quiet_hours_end": "07:30",
            "energy_windows": [
                {"name": "deep", "start_time": "08:00", "duration_minutes": 90},
                {"name": "calls", "start_time": "13:00", "duration_minutes": 60},
                {"name": "admin", "start_time": "15:00", "duration_minutes": 30},
            ],
        }

        # Test preference creation
        prefs = interview._create_preferences(final_data)

        # Verify preferences are valid
        assert isinstance(prefs, WorkPreferences)
        assert prefs.timezone == "America/Chicago"
        assert prefs.work_days == "mon,tue,wed,thu,fri"
        assert prefs.morning_window_start == "07:30"
        assert len(prefs.energy_windows) == 3

        # Test energy window calculations
        deep_window = prefs.energy_windows[0]
        assert deep_window.name == "deep"
        assert deep_window.start_time == "08:00"
        assert deep_window.end_time == "09:30"  # 08:00 + 90 minutes
        assert deep_window.max_session_minutes == 90


class TestHomeTab:
    """Test that home tab renders correctly."""

    def setup_method(self):
        """Reset feature flags before each test."""
        clear_all_overrides()

    @patch("apps.server.core.prefs.PreferencesStore")
    def test_home_tab_renders_with_flags_off(self, mock_store_class):
        """Test that home tab renders basic version when flags are off."""
        # Mock the preferences store
        mock_store = Mock()
        mock_store.get_prefs_or_defaults.return_value = WorkPreferences()
        mock_store_class.return_value = mock_store

        # Mock Slack client
        mock_client = Mock()

        # Create home tab handler
        home_tab = HomeTab()

        # Render home tab
        user_id = "U123456"
        home_tab.render_home_tab(user_id, mock_client)

        # Verify client was called
        mock_client.views_publish.assert_called_once()

        # Get the view that was published
        call_args = mock_client.views_publish.call_args
        view = call_args[1]["view"]

        # Verify basic structure
        assert view["type"] == "home"
        assert "blocks" in view

        # Should contain dashboard header
        header_found = any(
            block.get("type") == "header"
            and "FlowCoach Dashboard" in block.get("text", {}).get("text", "")
            for block in view["blocks"]
        )
        assert header_found, "Should contain dashboard header"

        # Should contain available commands
        commands_found = any(
            block.get("type") == "section" and "/audit" in block.get("text", {}).get("text", "")
            for block in view["blocks"]
        )
        assert commands_found, "Should list available commands"

        # Should NOT contain Phase 1 buttons when flags are off
        action_blocks = [block for block in view["blocks"] if block.get("type") == "actions"]
        if action_blocks:
            elements = action_blocks[0].get("elements", [])
            morning_brief_button = any(
                elem.get("action_id") == "start_morning_brief" for elem in elements
            )
            assert not morning_brief_button, "Should not show morning brief button when flag is off"


class TestFeatureFlags:
    """Test that feature flags work correctly."""

    def setup_method(self):
        """Reset feature flags before each test."""
        clear_all_overrides()

    def test_feature_flags_default_off(self):
        """Test that all FlowCoach flags default to OFF."""
        from apps.server.platform.feature_flags import is_enabled, FlowCoachFlag

        # Test all Phase 0 flags are off by default
        assert not is_enabled(FlowCoachFlag.FC_INTERVIEW_MODAL_V1)
        assert not is_enabled(FlowCoachFlag.FC_HOME_TAB_V1)

        # Test future phase flags are off by default
        assert not is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1)
        assert not is_enabled(FlowCoachFlag.FC_WRAP_MODAL_V1)
        assert not is_enabled(FlowCoachFlag.FC_WEEKLY_MODAL_V1)
        assert not is_enabled(FlowCoachFlag.FC_CHECKIN_V1)
        assert not is_enabled(FlowCoachFlag.FC_INTENT_ROUTER_V1)

    def test_feature_flag_memory_overrides(self):
        """Test that memory overrides work for testing."""
        from apps.server.platform.feature_flags import (
            is_enabled,
            set_override,
            clear_override,
            FlowCoachFlag,
        )

        # Initially off
        assert not is_enabled(FlowCoachFlag.FC_INTERVIEW_MODAL_V1)

        # Enable via override
        set_override(FlowCoachFlag.FC_INTERVIEW_MODAL_V1, True)
        assert is_enabled(FlowCoachFlag.FC_INTERVIEW_MODAL_V1)

        # Clear override
        clear_override(FlowCoachFlag.FC_INTERVIEW_MODAL_V1)
        assert not is_enabled(FlowCoachFlag.FC_INTERVIEW_MODAL_V1)


class TestQuietHours:
    """Test that quiet hours are parsed and available correctly."""

    def test_quiet_hours_values_parsed_and_available(self):
        """Test that quiet hours from preferences are properly parsed."""
        # Create preferences with specific quiet hours
        prefs = WorkPreferences(
            quiet_hours_start="22:00", quiet_hours_end="06:00", timezone="America/New_York"
        )

        # Verify the values are stored correctly
        assert prefs.quiet_hours_start == "22:00"
        assert prefs.quiet_hours_end == "06:00"
        assert prefs.timezone == "America/New_York"

        # Test edge case - same day quiet hours
        prefs2 = WorkPreferences(quiet_hours_start="12:00", quiet_hours_end="14:00")
        assert prefs2.quiet_hours_start == "12:00"
        assert prefs2.quiet_hours_end == "14:00"

        # Test that we can work with the time strings
        start_hour, start_min = map(int, prefs.quiet_hours_start.split(":"))
        end_hour, end_min = map(int, prefs.quiet_hours_end.split(":"))

        assert start_hour == 22
        assert start_min == 0
        assert end_hour == 6
        assert end_min == 0
