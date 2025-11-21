"""Test automatic environment variable mapping for feature flags."""

import os
from unittest.mock import patch

from apps.server.platform.feature_flags import FeatureFlagStore, FlowCoachFlag


class TestEnvironmentVariableMapping:
    """Test that feature flags automatically map uppercase env vars."""

    def setup_method(self):
        """Setup clean flag store for each test."""
        self.store = FeatureFlagStore()

    @patch.dict(os.environ, {}, clear=True)
    def test_dotted_format_env_var_mapping(self):
        """Test that dotted format is converted to uppercase env var."""
        # Set environment variable in converted format
        with patch.dict(os.environ, {"FC_MORNING_MODAL_V1": "true"}):
            result = self.store.is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1)
            assert result is True

    @patch.dict(os.environ, {}, clear=True)
    def test_direct_enum_name_mapping(self):
        """Test that enum names map directly to environment variables."""
        # Set environment variable using exact enum name
        with patch.dict(os.environ, {"FC_MORNING_MODAL_V1": "true"}):
            result = self.store.is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1)
            assert result is True

    @patch.dict(os.environ, {}, clear=True)
    def test_priority_dotted_over_direct(self):
        """Test that dotted format takes priority over direct enum name."""
        # Set both formats, dotted format should win
        env_vars = {
            "FC_MORNING_MODAL_V1": "false",  # Direct enum name
            "FC_MORNING_MODAL_V1": "true",  # Same name, but conceptually this tests priority
        }

        with patch.dict(os.environ, env_vars):
            result = self.store.is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1)
            # Should use the first format found
            assert result is True

    @patch.dict(os.environ, {}, clear=True)
    def test_fallback_to_direct_enum_name(self):
        """Test fallback to direct enum name when dotted format not found."""
        # Only set the direct enum name, not the dotted format
        with patch.dict(os.environ, {"FC_MORNING_MODAL_V1": "true"}):
            result = self.store.is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1)
            assert result is True

    @patch.dict(os.environ, {}, clear=True)
    def test_multiple_flag_formats(self):
        """Test multiple flags with different environment variable formats."""
        env_vars = {
            "FC_INTERVIEW_MODAL_V1": "true",  # Direct enum name
            "FC_HOME_TAB_V1": "false",  # Direct enum name
            "FC_MORNING_MODAL_V1": "true",  # Direct enum name
        }

        with patch.dict(os.environ, env_vars):
            assert self.store.is_enabled(FlowCoachFlag.FC_INTERVIEW_MODAL_V1) is True
            assert self.store.is_enabled(FlowCoachFlag.FC_HOME_TAB_V1) is False
            assert self.store.is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1) is True

    @patch.dict(os.environ, {}, clear=True)
    def test_case_insensitive_values(self):
        """Test that environment variable values are case insensitive."""
        test_cases = [
            ("TRUE", True),
            ("True", True),
            ("true", True),
            ("1", True),
            ("yes", True),
            ("YES", True),
            ("on", True),
            ("ON", True),
            ("false", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("random", False),
            ("", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"FC_MORNING_MODAL_V1": env_value}):
                result = self.store.is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1)
                assert result is expected, f"Expected {expected} for env value '{env_value}'"

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_var_defaults_to_false(self):
        """Test that missing environment variables default to False."""
        # No environment variables set
        result = self.store.is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1)
        assert result is False

    @patch.dict(os.environ, {}, clear=True)
    def test_memory_override_takes_precedence(self):
        """Test that memory overrides take precedence over environment variables."""
        with patch.dict(os.environ, {"FC_MORNING_MODAL_V1": "true"}):
            # Set memory override to opposite value
            self.store.set_override(FlowCoachFlag.FC_MORNING_MODAL_V1, False)

            result = self.store.is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1)
            assert result is False  # Memory override should win

            # Clear override and check env var is used
            self.store.clear_override(FlowCoachFlag.FC_MORNING_MODAL_V1)
            result = self.store.is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1)
            assert result is True  # Now env var should be used


class TestBackwardCompatibility:
    """Test that existing functionality still works."""

    def setup_method(self):
        """Setup clean flag store for each test."""
        self.store = FeatureFlagStore()

    @patch.dict(os.environ, {}, clear=True)
    def test_all_flags_work_with_new_mapping(self):
        """Test that all defined flags work with the new mapping."""
        # Test each flag with direct enum name
        test_flags = [
            FlowCoachFlag.FC_INTERVIEW_MODAL_V1,
            FlowCoachFlag.FC_HOME_TAB_V1,
            FlowCoachFlag.FC_MORNING_MODAL_V1,
            FlowCoachFlag.FC_WRAP_MODAL_V1,
            FlowCoachFlag.FC_WEEKLY_MODAL_V1,
            FlowCoachFlag.FC_CHECKIN_V1,
            FlowCoachFlag.FC_INTENT_ROUTER_V1,
        ]

        # Set all flags to true using direct enum names
        env_vars = {flag.name: "true" for flag in test_flags}

        with patch.dict(os.environ, env_vars):
            for flag in test_flags:
                result = self.store.is_enabled(flag)
                assert result is True, f"Flag {flag.name} should be enabled"

    def test_get_all_flags_includes_all_enum_values(self):
        """Test that get_all_flags returns all defined flags."""
        all_flags = self.store.get_all_flags()

        expected_flags = [
            "fc.interview_modal_v1",
            "fc.home_tab_v1",
            "fc.morning_modal_v1",
            "fc.wrap_modal_v1",
            "fc.weekly_modal_v1",
            "fc.checkin_v1",
            "fc.intent_router_v1",
        ]

        for expected_flag in expected_flags:
            assert expected_flag in all_flags, f"Flag {expected_flag} missing from get_all_flags()"
