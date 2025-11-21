"""CLI for managing feature flags."""

import argparse
import logging
import os
import sys

# Add server to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from feature_flags import FeatureFlag, get_feature_manager

logger = logging.getLogger(__name__)


def list_flags():
    """List all feature flags and their current states."""
    manager = get_feature_manager()
    flags = manager.get_all_flags()

    print("Feature Flags Status:")
    print("=" * 40)

    for flag_name, enabled in flags.items():
        status = "ENABLED" if enabled else "DISABLED"
        print(f"{flag_name:<25} {status}")

    print()
    safety_status = manager.get_safety_status()
    print("Safety Status:")
    print(f"Emergency Mode: {'YES' if safety_status['emergency_mode'] else 'NO'}")
    print(f"Database Writes: {'YES' if safety_status['database_writes_enabled'] else 'NO'}")
    print(f"Slack Commands: {'YES' if safety_status['slack_commands_enabled'] else 'NO'}")


def enable_flag(flag_name: str, persist: bool = False):
    """Enable a feature flag."""
    try:
        flag = FeatureFlag(flag_name)
        manager = get_feature_manager()
        manager.enable_flag(flag, persist=persist)
        print(f"✓ Enabled feature flag: {flag_name}")

        if persist:
            print("✓ Changes persisted to config file")

    except ValueError:
        print(f"✗ Unknown feature flag: {flag_name}")
        print("Available flags:")
        for flag in FeatureFlag:
            print(f"  - {flag.value}")
        sys.exit(1)


def disable_flag(flag_name: str, persist: bool = False):
    """Disable a feature flag."""
    try:
        flag = FeatureFlag(flag_name)
        manager = get_feature_manager()
        manager.disable_flag(flag, persist=persist)
        print(f"✓ Disabled feature flag: {flag_name}")

        if persist:
            print("✓ Changes persisted to config file")

    except ValueError:
        print(f"✗ Unknown feature flag: {flag_name}")
        print("Available flags:")
        for flag in FeatureFlag:
            print(f"  - {flag.value}")
        sys.exit(1)


def emergency_shutdown():
    """Activate emergency mode."""
    manager = get_feature_manager()

    print("⚠️  ACTIVATING EMERGENCY SHUTDOWN")
    print("This will disable all non-essential features!")

    # In CLI mode, require confirmation
    if not sys.stdin.isatty():
        print("✗ Emergency shutdown requires interactive terminal")
        sys.exit(1)

    confirm = input("Type 'EMERGENCY' to confirm: ").strip()
    if confirm != "EMERGENCY":
        print("✗ Emergency shutdown cancelled")
        sys.exit(0)

    manager.emergency_shutdown()
    print("✓ Emergency mode activated")
    print("✓ All non-essential features disabled")
    print("✓ Changes persisted to config")


def reset_flags():
    """Reset all flags to default values."""
    print("⚠️  RESETTING ALL FEATURE FLAGS TO DEFAULTS")

    # Require confirmation
    confirm = input("Type 'RESET' to confirm: ").strip()
    if confirm != "RESET":
        print("✗ Reset cancelled")
        sys.exit(0)

    # Delete config file to reset to defaults
    config_path = os.getenv("FC_FEATURE_CONFIG_PATH")
    if config_path and os.path.exists(config_path):
        os.remove(config_path)
        print(f"✓ Deleted config file: {config_path}")

    # Create new manager to load defaults
    global _feature_manager
    from feature_flags import _feature_manager

    _feature_manager = None  # Force reload

    manager = get_feature_manager()
    print("✓ Feature flags reset to defaults")

    # Show current state
    list_flags()


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Manage FlowCoach feature flags",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                          # Show all flags
  %(prog)s enable project_audit          # Enable audit feature
  %(prog)s disable project_rewrite       # Disable rewrite feature
  %(prog)s enable --persist ai_suggestions  # Enable and save
  %(prog)s emergency                     # Emergency shutdown
  %(prog)s reset                         # Reset all to defaults

Environment Variables:
  FC_FEATURE_CONFIG_PATH                 # Path to feature config file
  FC_FEATURE_<FLAG_NAME>=true/false      # Set individual flags

Available Flags:
"""
        + "\n".join(f"  - {flag.value}" for flag in FeatureFlag),
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    subparsers.add_parser("list", help="List all feature flags")

    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable a feature flag")
    enable_parser.add_argument("flag", help="Flag name to enable")
    enable_parser.add_argument(
        "--persist", action="store_true", help="Persist changes to config file"
    )

    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable a feature flag")
    disable_parser.add_argument("flag", help="Flag name to disable")
    disable_parser.add_argument(
        "--persist", action="store_true", help="Persist changes to config file"
    )

    # Emergency command
    subparsers.add_parser("emergency", help="Activate emergency shutdown mode")

    # Reset command
    subparsers.add_parser("reset", help="Reset all flags to defaults")

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s: %(message)s"  # Quiet by default for CLI
    )

    # Handle commands
    try:
        if args.command == "list" or args.command is None:
            list_flags()

        elif args.command == "enable":
            enable_flag(args.flag, persist=args.persist)

        elif args.command == "disable":
            disable_flag(args.flag, persist=args.persist)

        elif args.command == "emergency":
            emergency_shutdown()

        elif args.command == "reset":
            reset_flags()

        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n✗ Operation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        logger.error(f"CLI error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
