#!/usr/bin/env python3
"""
FlowCoach Setup Verification Script

Checks if development and production environments are properly configured.
"""

import sys
from pathlib import Path


def check_file(path, description):
    """Check if a file exists and show status."""
    if Path(path).exists():
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ {description}")
        return False


def check_env_vars(env_file, environment):
    """Check if required environment variables are set in file."""
    print(f"\n📋 {environment.title()} Environment ({env_file}):")

    if not Path(env_file).exists():
        print(f"❌ {env_file} not found")
        return False

    # Read env file and check for required variables
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
        "SLACK_SIGNING_SECRET",
        "CLAUDE_API_KEY",
        "TODOIST_API_TOKEN",
    ]

    found_vars = []
    with open(env_file) as f:
        content = f.read()
        for var in required_vars:
            if (
                f"{var}=" in content
                and f"{var}=xoxb-YOUR" not in content
                and f"{var}=xapp-YOUR" not in content
            ):
                found_vars.append(var)

    for var in required_vars:
        if var in found_vars:
            print(f"  ✅ {var}")
        else:
            print(f"  ❌ {var} (missing or placeholder)")

    return len(found_vars) == len(required_vars)


def main():
    """Check FlowCoach setup."""

    print("🔍 FlowCoach Setup Verification")
    print("=" * 40)

    # Check basic files
    print("\n📁 Core Files:")
    files_ok = True
    files_ok &= check_file("app.py", "Main application file")
    files_ok &= check_file("config/__init__.py", "Configuration module")
    files_ok &= check_file("core/gtd_protection.py", "GTD protection system")
    files_ok &= check_file("tests/test_gtd_protection.py", "GTD tests")

    # Check environment configurations
    prod_ok = check_env_vars(".env", "production")
    dev_ok = check_env_vars(".env.dev", "development")

    # Check databases
    print("\n🗄️  Databases:")
    prod_db = check_file("flowcoach.db", "Production database (flowcoach.db)")
    dev_db = check_file("flowcoach_dev.db", "Development database (flowcoach_dev.db)")

    # Summary
    print("\n📊 Setup Status:")
    print(f"  Core files: {'✅' if files_ok else '❌'}")
    print(f"  Production config: {'✅' if prod_ok else '❌'}")
    print(f"  Development config: {'✅' if dev_ok else '❌'}")

    if prod_ok and dev_ok and files_ok:
        print("\n🎉 Setup Complete!")
        print("  • Development: python3 run_dev.py")
        print("  • Production:  python3 run_prod.py")
        return 0
    else:
        print("\n⚠️  Setup Issues Found:")
        if not files_ok:
            print("  • Missing core files")
        if not prod_ok:
            print("  • Production config incomplete (.env)")
        if not dev_ok:
            print("  • Development config incomplete (.env.dev)")
            print("  • See SLACK_DEV_SETUP.md for instructions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
