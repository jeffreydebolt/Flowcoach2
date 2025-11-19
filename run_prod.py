#!/usr/bin/env python3
"""
FlowCoach Production Mode Runner

This script sets up the production environment and runs FlowCoach with:
- Production Slack app tokens (.env)
- Production database (flowcoach.db)
- Info logging
- Production feature flags

Usage:
    python3 run_prod.py
"""

import os
import sys


def main():
    """Run FlowCoach in production mode."""

    print("🚀 FlowCoach Production Mode")
    print("=" * 40)

    # Set production environment
    os.environ["FLOWCOACH_ENV"] = "production"

    # Verify production configuration exists
    if not os.path.exists(".env"):
        print("❌ Error: .env file not found!")
        print("\n📋 Setup Instructions:")
        print("1. Copy .env.example to .env")
        print("2. Update .env with your production tokens")
        print("3. Run this script again")
        return 1

    print("✅ Production environment configured")
    print("📂 Loading config from: .env")
    print("🗄️  Using database: flowcoach.db")
    print("📊 Log level: INFO")
    print()

    # Check if development mode might be running
    print("⚠️  Warning: Make sure no development instances are running!")
    print("   Development and production cannot run simultaneously.")
    print()

    # Import and run the main app
    try:
        from app import main as app_main

        print("🚀 Starting FlowCoach production server...")
        print("💬 Bot name in Slack: 'FlowCoach'")
        print("🔗 Socket Mode: Production app token")
        print()
        return app_main()

    except KeyboardInterrupt:
        print("\n⏹️  Production server stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Production server failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
