"""Configuration validation for FlowCoach startup."""

import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    required_missing: List[str]
    optional_missing: List[str]
    warnings: List[str]

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0 or len(self.optional_missing) > 0


class ConfigValidator:
    """Validates FlowCoach configuration at startup."""

    # Required configuration keys
    REQUIRED_KEYS = {
        'TODOIST_API_TOKEN': 'Todoist API token for task management',
        'CLAUDE_API_KEY': 'Anthropic Claude API key for AI processing (if using TypeScript CLI)',
    }

    # Optional configuration keys
    OPTIONAL_KEYS = {
        'SLACK_BOT_TOKEN': 'Slack bot token for daily briefs and interactions',
        'SLACK_APP_TOKEN': 'Slack app token for Socket Mode (if using interactive features)',
        'FC_DEFAULT_PROJECT': 'Default Todoist project ID for new tasks',
        'FC_ACTIVE_USERS': 'Comma-separated list of Slack user IDs for scheduled jobs',
        'FC_DEFAULT_TIMEZONE': 'Default timezone (e.g., America/Denver)',
        'FC_DB_PATH': 'SQLite database file path',
        'FC_LABEL_MODE': 'Time label mode: "labels" or "prefix"',
        'FC_TIME_BUCKETS': 'Custom time bucket configuration',
        'LOG_LEVEL': 'Logging level (debug, info, warning, error)',
    }

    @classmethod
    def validate_config(cls, env_vars: Optional[Dict[str, str]] = None) -> ValidationResult:
        """
        Validate configuration from environment variables.

        Args:
            env_vars: Dictionary of environment variables (default: os.environ)

        Returns:
            ValidationResult with validation status and details
        """
        if env_vars is None:
            env_vars = dict(os.environ)

        required_missing = []
        optional_missing = []
        warnings = []

        # Check required keys
        for key, description in cls.REQUIRED_KEYS.items():
            value = env_vars.get(key, '').strip()
            if not value:
                required_missing.append(key)

        # Check optional keys
        for key, description in cls.OPTIONAL_KEYS.items():
            value = env_vars.get(key, '').strip()
            if not value:
                optional_missing.append(key)

        # Specific validation logic
        warnings.extend(cls._validate_specific_configs(env_vars))

        is_valid = len(required_missing) == 0

        return ValidationResult(
            is_valid=is_valid,
            required_missing=required_missing,
            optional_missing=optional_missing,
            warnings=warnings
        )

    @classmethod
    def _validate_specific_configs(cls, env_vars: Dict[str, str]) -> List[str]:
        """Perform specific validation logic on configuration values."""
        warnings = []

        # Validate Slack configuration consistency
        slack_bot_token = env_vars.get('SLACK_BOT_TOKEN', '').strip()
        slack_app_token = env_vars.get('SLACK_APP_TOKEN', '').strip()
        active_users = env_vars.get('FC_ACTIVE_USERS', '').strip()

        if slack_bot_token and not active_users:
            warnings.append("SLACK_BOT_TOKEN provided but FC_ACTIVE_USERS not set. Jobs won't run for any users.")

        if slack_app_token and not slack_bot_token:
            warnings.append("SLACK_APP_TOKEN provided but SLACK_BOT_TOKEN missing. Socket Mode won't work.")

        # Validate time buckets format
        time_buckets = env_vars.get('FC_TIME_BUCKETS', '').strip()
        if time_buckets and not cls._is_valid_time_buckets_format(time_buckets):
            warnings.append(f"FC_TIME_BUCKETS format invalid: '{time_buckets}'. Expected format: 'bucket:minutes,bucket:minutes'")

        # Validate timezone
        timezone = env_vars.get('FC_DEFAULT_TIMEZONE', '').strip()
        if timezone and not cls._is_valid_timezone(timezone):
            warnings.append(f"FC_DEFAULT_TIMEZONE may be invalid: '{timezone}'. Using system default.")

        # Validate log level
        log_level = env_vars.get('LOG_LEVEL', '').strip().lower()
        if log_level and log_level not in ['debug', 'info', 'warning', 'error']:
            warnings.append(f"LOG_LEVEL invalid: '{log_level}'. Expected: debug, info, warning, error")

        return warnings

    @classmethod
    def _is_valid_time_buckets_format(cls, time_buckets: str) -> bool:
        """Validate time buckets configuration format."""
        try:
            pairs = time_buckets.split(',')
            for pair in pairs:
                if ':' not in pair:
                    return False
                bucket_name, max_minutes = pair.split(':', 1)
                int(max_minutes)  # Check if minutes is a valid integer
            return True
        except (ValueError, IndexError):
            return False

    @classmethod
    def _is_valid_timezone(cls, timezone: str) -> bool:
        """Basic timezone validation."""
        # Simple validation - check if it looks like a valid timezone
        common_formats = [
            'America/',
            'Europe/',
            'Asia/',
            'Pacific/',
            'UTC',
            'GMT'
        ]
        return any(timezone.startswith(fmt) for fmt in common_formats) or timezone in ['UTC', 'GMT']

    @classmethod
    def print_validation_report(cls, result: ValidationResult) -> None:
        """Print a formatted validation report to console."""
        print("\n" + "="*60)
        print("🔧 FlowCoach Configuration Validation")
        print("="*60)

        if result.is_valid:
            print("✅ Configuration is valid!")
        else:
            print("❌ Configuration has required errors:")
            for key in result.required_missing:
                description = cls.REQUIRED_KEYS.get(key, "Required configuration")
                print(f"   Missing: {key} - {description}")
            print(f"\n💡 Add missing keys to your .env file")

        if result.optional_missing:
            print(f"\n⚠️  Optional configuration missing ({len(result.optional_missing)} items):")
            for key in result.optional_missing:
                description = cls.OPTIONAL_KEYS.get(key, "Optional configuration")
                print(f"   {key} - {description}")

        if result.warnings:
            print(f"\n⚠️  Configuration warnings:")
            for warning in result.warnings:
                print(f"   {warning}")

        if result.is_valid and not result.has_warnings:
            print("\n🎉 All configuration looks great!")
        elif result.is_valid:
            print("\n✅ Ready to run (with warnings noted above)")
        else:
            print("\n❌ Please fix required configuration before running")

        print("="*60 + "\n")

    @classmethod
    def validate_and_report(cls, env_vars: Optional[Dict[str, str]] = None) -> ValidationResult:
        """
        Convenience method to validate and print report.

        Returns:
            ValidationResult
        """
        result = cls.validate_config(env_vars)
        cls.print_validation_report(result)
        return result


def validate_startup_config() -> bool:
    """
    Main entry point for startup validation.

    Returns:
        True if configuration is valid, False otherwise
    """
    result = ConfigValidator.validate_and_report()

    # Log the result
    if result.is_valid:
        if result.has_warnings:
            logger.warning(f"Configuration valid with {len(result.warnings)} warnings")
        else:
            logger.info("Configuration validation successful")
    else:
        logger.error(f"Configuration validation failed: {len(result.required_missing)} required keys missing")

    return result.is_valid


if __name__ == "__main__":
    # Allow running as standalone script
    import sys
    is_valid = validate_startup_config()
    sys.exit(0 if is_valid else 1)
