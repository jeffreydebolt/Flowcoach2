#!/usr/bin/env python3
"""
FlowCoach Development Mode Runner

This script sets up the development environment and runs FlowCoach with:
- Development Slack app tokens (.env.dev)
- Development database (flowcoach_dev.db)
- Debug logging
- All feature flags enabled for testing

Usage:
    python3 run_dev.py
"""

import os
import sys


def main():
    """Run FlowCoach in development mode."""

    print("🔧 FlowCoach Development Mode")
    print("=" * 40)

    # Set development environment
    os.environ["FLOWCOACH_ENV"] = "development"

    # Verify development configuration exists
    if not os.path.exists(".env.dev"):
        print("❌ Error: .env.dev file not found!")
        print("\n📋 Setup Instructions:")
        print("1. Follow SLACK_DEV_SETUP.md to create development Slack app")
        print("2. Update .env.dev with your development tokens")
        print("3. Run this script again")
        return 1

    print("✅ Development environment configured")
    print("📂 Loading config from: .env.dev")
    print("🗄️  Using database: flowcoach_dev.db")
    print("📊 Log level: DEBUG")
    print()

    # Import and run the main app
    try:
        from app import main as app_main

        print("🚀 Starting FlowCoach development server...")
        print("💬 Bot name in Slack: 'FlowCoach Dev'")
        print("🔗 Socket Mode: Development app token")
        print()
        return app_main()

    except KeyboardInterrupt:
        print("\n⏹️  Development server stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Development server failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
