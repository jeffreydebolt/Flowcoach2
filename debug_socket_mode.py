#!/usr/bin/env python3
"""Debug Socket Mode connection issues."""

import os
from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)


def debug_socket_mode():
    """Debug what's wrong with Socket Mode."""

    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    print(f"Bot token: {bot_token[:12]}..." if bot_token else "Missing bot token")
    print(f"App token: {app_token[:12]}..." if app_token else "Missing app token")

    # Test basic auth first
    client = WebClient(token=bot_token)
    try:
        response = client.auth_test()
        print(f"✓ Bot auth works - {response['bot_id']}")
    except Exception as e:
        print(f"✗ Bot auth failed: {e}")
        return

    # Test app token
    try:
        app = App(token=bot_token)
        print("✓ App created successfully")

        # Try to create socket mode handler with minimal config
        handler = SocketModeHandler(
            app=app,
            app_token=app_token,
            ping_interval=120,  # Longer ping interval
            trace_enabled=False,  # Disable trace to reduce noise
        )
        print("✓ SocketModeHandler created")

        # Don't actually start it, just test creation

    except Exception as e:
        print(f"✗ Socket Mode setup failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_socket_mode()
