"""Integration tests for feature flags across the system."""

import json
import os
import tempfile

# Test imports
from apps.server.core.feature_flags import FeatureFlag, get_feature_manager
from apps.server.core.momentum import MomentumTracker
from apps.server.health import HealthChecker


def test_feature_flag_basic_functionality():
    """Test basic feature flag operations."""
    print("Testing basic feature flag functionality...")

    manager = get_feature_manager()

    # Test getting all flags
    flags = manager.get_all_flags()
    assert isinstance(flags, dict)
    assert len(flags) > 0
    print(f"✓ Loaded {len(flags)} feature flags")

    # Test enabling/disabling flags
    original_state = manager.is_enabled(FeatureFlag.AI_SUGGESTIONS)

    manager.enable_flag(FeatureFlag.AI_SUGGESTIONS)
    assert manager.is_enabled(FeatureFlag.AI_SUGGESTIONS) == True

    manager.disable_flag(FeatureFlag.AI_SUGGESTIONS)
    assert manager.is_enabled(FeatureFlag.AI_SUGGESTIONS) == False

    # Restore original state
    if original_state:
        manager.enable_flag(FeatureFlag.AI_SUGGESTIONS)

    print("✓ Feature flag enable/disable works")


def test_database_write_protection():
    """Test that database write protection works."""
    print("Testing database write protection...")

    manager = get_feature_manager()
    tracker = MomentumTracker()

    # Ensure database writes are initially enabled
    manager.enable_flag(FeatureFlag.DATABASE_WRITES)

    # Test with database writes enabled (should work in memory/test mode)
    result = tracker.update_project_momentum("test_project", is_deep_work=True)
    # Note: This might still return False if no actual database, but decorator should allow the call
    print(f"✓ Update with DB writes enabled: {result}")

    # Disable database writes
    manager.disable_flag(FeatureFlag.DATABASE_WRITES)

    # Test with database writes disabled (should return False)
    result = tracker.update_project_momentum("test_project", is_deep_work=True)
    assert result == False
    print("✓ Database write protection active")

    # Re-enable for cleanup
    manager.enable_flag(FeatureFlag.DATABASE_WRITES)


def test_emergency_mode():
    """Test emergency mode functionality."""
    print("Testing emergency mode...")

    manager = get_feature_manager()

    # Store original states
    original_rewrite = manager.is_enabled(FeatureFlag.PROJECT_REWRITE)
    original_ai = manager.is_enabled(FeatureFlag.AI_SUGGESTIONS)

    # Activate emergency mode
    manager.emergency_shutdown()

    # Check that non-essential features are disabled
    assert manager.is_enabled(FeatureFlag.EMERGENCY_MODE) == True
    assert manager.is_enabled(FeatureFlag.PROJECT_REWRITE) == False
    assert manager.is_enabled(FeatureFlag.AI_SUGGESTIONS) == False

    # Essential features should still work
    assert manager.is_enabled(FeatureFlag.SLACK_COMMANDS) == True

    print("✓ Emergency mode activated correctly")

    # Restore original states (reset emergency mode)
    manager.disable_flag(FeatureFlag.EMERGENCY_MODE)
    if original_rewrite:
        manager.enable_flag(FeatureFlag.PROJECT_REWRITE)
    if original_ai:
        manager.enable_flag(FeatureFlag.AI_SUGGESTIONS)


def test_feature_flag_persistence():
    """Test feature flag persistence to config file."""
    print("Testing feature flag persistence...")

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_config_path = f.name

    try:
        # Set config path
        os.environ["FC_FEATURE_CONFIG_PATH"] = temp_config_path

        # Create new manager to use the temp config
        from apps.server.core.feature_flags import FeatureFlagManager

        test_manager = FeatureFlagManager()

        # Enable a flag with persistence
        test_manager.enable_flag(FeatureFlag.AI_SUGGESTIONS, persist=True)

        # Check that config file was created
        assert os.path.exists(temp_config_path)

        # Check config file contents
        with open(temp_config_path) as f:
            config = json.load(f)

        assert config.get("ai_suggestions") == True
        print("✓ Feature flag persistence works")

    finally:
        # Cleanup
        if "FC_FEATURE_CONFIG_PATH" in os.environ:
            del os.environ["FC_FEATURE_CONFIG_PATH"]
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)


def test_health_check_integration():
    """Test that health check includes feature flag status."""
    print("Testing health check integration...")

    health_checker = HealthChecker()
    health_status = health_checker.get_health_status()

    # Check that feature flags are included
    assert hasattr(health_status, "feature_flags")
    assert isinstance(health_status.feature_flags, dict)
    assert len(health_status.feature_flags) > 0

    # Check that safety status is available
    manager = get_feature_manager()
    safety_status = manager.get_safety_status()

    assert "emergency_mode" in safety_status
    assert "database_writes_enabled" in safety_status
    assert "slack_commands_enabled" in safety_status

    print("✓ Health check includes feature flags")


def test_environment_variable_override():
    """Test that environment variables can override feature flags."""
    print("Testing environment variable override...")

    # Set environment variable
    os.environ["FC_FEATURE_AI_SUGGESTIONS"] = "true"

    try:
        # Create new manager to pick up env var
        from apps.server.core.feature_flags import FeatureFlagManager

        test_manager = FeatureFlagManager()

        # Check that AI suggestions is enabled due to env var
        assert test_manager.is_enabled(FeatureFlag.AI_SUGGESTIONS) == True
        print("✓ Environment variable override works")

    finally:
        # Cleanup
        if "FC_FEATURE_AI_SUGGESTIONS" in os.environ:
            del os.environ["FC_FEATURE_AI_SUGGESTIONS"]


def run_all_tests():
    """Run all integration tests."""
    print("=" * 50)
    print("FlowCoach Feature Flags Integration Tests")
    print("=" * 50)
    print()

    tests = [
        test_feature_flag_basic_functionality,
        test_database_write_protection,
        test_emergency_mode,
        test_feature_flag_persistence,
        test_health_check_integration,
        test_environment_variable_override,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            print(f"✓ {test_func.__name__} PASSED")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
        print()

    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    # Bootstrap environment
    from apps.server.core.env_bootstrap import bootstrap_env

    bootstrap_env()

    success = run_all_tests()
    exit(0 if success else 1)
