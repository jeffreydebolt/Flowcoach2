"""Feature flag system for FlowCoach."""

import json
import logging
import os
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class FeatureFlag(Enum):
    """Enumeration of available feature flags."""

    # Core features
    PROJECT_MOMENTUM = "project_momentum"
    PROJECT_AUDIT = "project_audit"
    PROJECT_REWRITE = "project_rewrite"

    # Advanced features
    AI_SUGGESTIONS = "ai_suggestions"
    CALENDAR_INTEGRATION = "calendar_integration"
    ADVANCED_SCORING = "advanced_scoring"

    # Safety and rollback
    EMERGENCY_MODE = "emergency_mode"
    SLACK_COMMANDS = "slack_commands"
    DATABASE_WRITES = "database_writes"


class FeatureFlagManager:
    """Manages feature flags for FlowCoach."""

    def __init__(self):
        self._flags = {}
        self._load_flags()

    def _load_flags(self):
        """Load feature flags from environment and config."""
        # Default flags (production-safe defaults)
        defaults = {
            # Core features enabled by default
            FeatureFlag.PROJECT_MOMENTUM.value: True,
            FeatureFlag.PROJECT_AUDIT.value: True,
            FeatureFlag.PROJECT_REWRITE.value: True,
            # Advanced features disabled by default
            FeatureFlag.AI_SUGGESTIONS.value: False,
            FeatureFlag.CALENDAR_INTEGRATION.value: False,
            FeatureFlag.ADVANCED_SCORING.value: False,
            # Safety flags
            FeatureFlag.EMERGENCY_MODE.value: False,
            FeatureFlag.SLACK_COMMANDS.value: True,
            FeatureFlag.DATABASE_WRITES.value: True,
        }

        # Start with defaults
        self._flags = defaults.copy()

        # Load from environment variables (FC_FEATURE_<FLAG_NAME>)
        for flag in FeatureFlag:
            env_var = f"FC_FEATURE_{flag.value.upper()}"
            env_value = os.getenv(env_var)

            if env_value is not None:
                # Parse boolean from env var
                if env_value.lower() in ("true", "1", "on", "yes"):
                    self._flags[flag.value] = True
                elif env_value.lower() in ("false", "0", "off", "no"):
                    self._flags[flag.value] = False
                else:
                    logger.warning(f"Invalid boolean value for {env_var}: {env_value}")

        # Load from config file if present
        config_path = os.getenv("FC_FEATURE_CONFIG_PATH")
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    config_flags = json.load(f)

                # Update flags with config values
                for flag_name, flag_value in config_flags.items():
                    if flag_name in [f.value for f in FeatureFlag]:
                        self._flags[flag_name] = bool(flag_value)
                    else:
                        logger.warning(f"Unknown feature flag in config: {flag_name}")

                logger.info(f"Loaded feature flags from config: {config_path}")

            except Exception as e:
                logger.error(f"Failed to load feature flag config from {config_path}: {e}")

        # Emergency mode overrides
        if self._flags.get(FeatureFlag.EMERGENCY_MODE.value, False):
            logger.warning("EMERGENCY MODE ENABLED - Disabling non-essential features")
            self._flags[FeatureFlag.AI_SUGGESTIONS.value] = False
            self._flags[FeatureFlag.CALENDAR_INTEGRATION.value] = False
            self._flags[FeatureFlag.ADVANCED_SCORING.value] = False
            self._flags[FeatureFlag.PROJECT_REWRITE.value] = False

        logger.info(f"Feature flags loaded: {self._flags}")

    def is_enabled(self, flag: FeatureFlag) -> bool:
        """Check if a feature flag is enabled."""
        return self._flags.get(flag.value, False)

    def enable_flag(self, flag: FeatureFlag, persist: bool = False):
        """Enable a feature flag."""
        self._flags[flag.value] = True
        logger.info(f"Enabled feature flag: {flag.value}")

        if persist:
            self._persist_flags()

    def disable_flag(self, flag: FeatureFlag, persist: bool = False):
        """Disable a feature flag."""
        self._flags[flag.value] = False
        logger.info(f"Disabled feature flag: {flag.value}")

        if persist:
            self._persist_flags()

    def get_all_flags(self) -> dict[str, bool]:
        """Get all feature flags and their states."""
        return self._flags.copy()

    def _persist_flags(self):
        """Persist current flags to config file if path is set."""
        config_path = os.getenv("FC_FEATURE_CONFIG_PATH")
        if not config_path:
            logger.warning("No FC_FEATURE_CONFIG_PATH set, cannot persist flags")
            return

        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(self._flags, f, indent=2)

            logger.info(f"Persisted feature flags to: {config_path}")

        except Exception as e:
            logger.error(f"Failed to persist feature flags: {e}")

    def emergency_shutdown(self):
        """Enable emergency mode - disables all non-essential features."""
        logger.critical("EMERGENCY SHUTDOWN ACTIVATED")

        # Keep only essential features
        essential_flags = [
            FeatureFlag.EMERGENCY_MODE,
            FeatureFlag.SLACK_COMMANDS,  # Keep basic commands working
        ]

        for flag in FeatureFlag:
            if flag not in essential_flags:
                self._flags[flag.value] = False

        self._flags[FeatureFlag.EMERGENCY_MODE.value] = True

        # Persist emergency state
        self._persist_flags()

    def get_safety_status(self) -> dict[str, Any]:
        """Get safety-related status information."""
        return {
            "emergency_mode": self.is_enabled(FeatureFlag.EMERGENCY_MODE),
            "database_writes_enabled": self.is_enabled(FeatureFlag.DATABASE_WRITES),
            "slack_commands_enabled": self.is_enabled(FeatureFlag.SLACK_COMMANDS),
            "core_features_enabled": [
                flag.value
                for flag in [
                    FeatureFlag.PROJECT_MOMENTUM,
                    FeatureFlag.PROJECT_AUDIT,
                    FeatureFlag.PROJECT_REWRITE,
                ]
                if self.is_enabled(flag)
            ],
            "experimental_features_enabled": [
                flag.value
                for flag in [
                    FeatureFlag.AI_SUGGESTIONS,
                    FeatureFlag.CALENDAR_INTEGRATION,
                    FeatureFlag.ADVANCED_SCORING,
                ]
                if self.is_enabled(flag)
            ],
        }


# Global feature flag manager instance
_feature_manager = None


def get_feature_manager() -> FeatureFlagManager:
    """Get the global feature flag manager instance."""
    global _feature_manager
    if _feature_manager is None:
        _feature_manager = FeatureFlagManager()
    return _feature_manager


def is_feature_enabled(flag: FeatureFlag) -> bool:
    """Convenience function to check if a feature is enabled."""
    return get_feature_manager().is_enabled(flag)


def require_feature(flag: FeatureFlag):
    """Decorator to require a feature flag for a function."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not is_feature_enabled(flag):
                raise RuntimeError(f"Feature {flag.value} is disabled")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def safe_feature(flag: FeatureFlag, fallback_value=None):
    """Decorator to safely handle disabled features with fallback."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not is_feature_enabled(flag):
                logger.info(f"Feature {flag.value} disabled, returning fallback")
                return fallback_value
            return func(*args, **kwargs)

        return wrapper

    return decorator
