#!/usr/bin/env python3
"""Simple bot to test Socket Mode without all the complex imports."""

import logging
import os
import signal
import sys

# Bootstrap environment
from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Configure simple logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Handle shutdown gracefully."""
    logger.info("Shutting down...")
    sys.exit(0)


def main():
    """Run a simple test bot."""
    signal.signal(signal.SIGINT, signal_handler)

    # Get tokens
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not bot_token or not app_token:
        logger.error("Missing tokens")
        return 1

    # Create app
    app = App(token=bot_token)

    # Add simple message handler for testing
    @app.message("test")
    def handle_test(message, say):
        say(f"Socket Mode is working! Received: {message['text']}")

    @app.message("gtd")
    def handle_gtd(message, say):
        # Test GTD formatting
        from core.gtd_protection import gtd_protector

        formatted = gtd_protector.format_with_gtd_fallback(message["text"])
        say(f"GTD formatted: {formatted}")

    # Create socket mode handler with conservative settings
    try:
        logger.info("Creating Socket Mode handler...")
        handler = SocketModeHandler(
            app=app,
            app_token=app_token,
            ping_interval=300,  # 5 minutes
        )

        logger.info("Starting Socket Mode handler...")
        handler.start()

    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Socket Mode failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
