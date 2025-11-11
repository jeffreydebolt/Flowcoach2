"""Feature flag system for incremental rollout.

Environment Variable Mapping:
- Supports automatic mapping from uppercase env vars to dotted flag names
- FC_MORNING_MODAL_V1 → fc.morning_modal_v1
- Also supports the converted format: FC_MORNING_MODAL_V1 (from fc.morning_modal_v1)
- Memory overrides always take precedence for testing
"""

import os
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class FlowCoachFlag(Enum):
    """FlowCoach v1 feature flags for BMAD implementation."""

    # Phase 0: Interview + Prefs
    FC_INTERVIEW_MODAL_V1 = "fc.interview_modal_v1"
    FC_HOME_TAB_V1 = "fc.home_tab_v1"

    # Phase 1: Morning Brief Modal
    FC_MORNING_MODAL_V1 = "fc.morning_modal_v1"

    # Phase 2: Wrap Modal
    FC_WRAP_MODAL_V1 = "fc.wrap_modal_v1"

    # Phase 3: Weekly Review Modal
    FC_WEEKLY_MODAL_V1 = "fc.weekly_modal_v1"

    # Phase 4: Check-in System
    FC_CHECKIN_V1 = "fc.checkin_v1"

    # Phase 5: Intent Router
    FC_INTENT_ROUTER_V1 = "fc.intent_router_v1"


class FeatureFlagStore:
    """
    Feature flag store with environment variable backing.

    Supports in-memory overrides for testing.
    """

    def __init__(self):
        """Initialize feature flag store."""
        self._memory_overrides: Dict[str, bool] = {}

    def is_enabled(self, flag: FlowCoachFlag) -> bool:
        """Check if a feature flag is enabled."""
        flag_name = flag.value

        # Check memory override first (for testing)
        if flag_name in self._memory_overrides:
            result = self._memory_overrides[flag_name]
            logger.debug(f"Feature flag {flag_name} = {result} (memory override)")
            return result

        # Check environment variable - try both formats
        # 1. Standard dotted format converted to uppercase: fc.morning_modal_v1 -> FC_MORNING_MODAL_V1
        env_name = flag_name.upper().replace(".", "_")
        env_value = os.getenv(env_name)

        # 2. If not found, try the uppercase environment variable name directly
        if env_value is None:
            # Map from FlowCoachFlag enum name: FC_MORNING_MODAL_V1 -> FC_MORNING_MODAL_V1
            enum_name = flag.name
            env_value = os.getenv(enum_name)

        # Default to false if not found
        if env_value is None:
            env_value = "false"

        env_value = env_value.lower()
        result = env_value in ("true", "1", "yes", "on")

        logger.debug(f"Feature flag {flag_name} = {result} (env: {env_name}={env_value})")
        return result

    def set_override(self, flag: FlowCoachFlag, enabled: bool) -> None:
        """Set memory override for testing."""
        self._memory_overrides[flag.value] = enabled
        logger.debug(f"Set feature flag override: {flag.value} = {enabled}")

    def clear_override(self, flag: FlowCoachFlag) -> None:
        """Clear memory override."""
        if flag.value in self._memory_overrides:
            del self._memory_overrides[flag.value]
            logger.debug(f"Cleared feature flag override: {flag.value}")

    def clear_all_overrides(self) -> None:
        """Clear all memory overrides."""
        self._memory_overrides.clear()
        logger.debug("Cleared all feature flag overrides")

    def get_all_flags(self) -> Dict[str, bool]:
        """Get status of all feature flags (for debugging)."""
        result = {}
        for flag in FlowCoachFlag:
            result[flag.value] = self.is_enabled(flag)
        return result


# Global feature flag store
_flag_store = FeatureFlagStore()


def is_enabled(flag: FlowCoachFlag) -> bool:
    """Check if a feature flag is enabled (convenience function)."""
    return _flag_store.is_enabled(flag)


def set_override(flag: FlowCoachFlag, enabled: bool) -> None:
    """Set memory override for testing (convenience function)."""
    _flag_store.set_override(flag, enabled)


def clear_override(flag: FlowCoachFlag) -> None:
    """Clear memory override (convenience function)."""
    _flag_store.clear_override(flag)


def clear_all_overrides() -> None:
    """Clear all memory overrides (convenience function)."""
    _flag_store.clear_all_overrides()


def get_all_flags() -> Dict[str, bool]:
    """Get status of all feature flags (convenience function)."""
    return _flag_store.get_all_flags()


def require_flag(flag: FlowCoachFlag):
    """Decorator to require a feature flag for a function."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not is_enabled(flag):
                logger.warning(f"Function {func.__name__} blocked by feature flag {flag.value}")
                return None
            return func(*args, **kwargs)

        return wrapper

    return decorator
