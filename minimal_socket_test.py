#!/usr/bin/env python3
"""Absolute minimal Socket Mode test to isolate connection cycling issue."""

import logging
import os
import signal
import sys

# Bootstrap environment
from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Minimal logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Run absolute minimal Socket Mode test."""

    # Get tokens
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not bot_token or not app_token:
        logger.error("Missing tokens")
        return 1

    logger.info(f"Bot token: {bot_token[:12]}...")
    logger.info(f"App token: {app_token[:12]}...")

    # Create minimal app with no middleware
    app = App(token=bot_token)

    # Add single test handler
    @app.message("ping")
    def handle_ping(message, say):
        logger.info("Received ping message!")
        say("pong")

    # Create Socket Mode handler with absolute minimal config
    logger.info("Creating Socket Mode handler...")
    handler = SocketModeHandler(
        app=app,
        app_token=app_token,
        # No additional parameters
    )

    # Setup signal handler
    def signal_handler(signum, frame):
        logger.info("Shutting down...")
        handler.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting Socket Mode handler...")
    try:
        handler.start()
    except Exception as e:
        logger.error(f"Socket Mode failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
