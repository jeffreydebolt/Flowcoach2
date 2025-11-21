#!/usr/bin/env python3
"""
Socket Mode fix with connection management and proper cleanup.
"""

import logging
import os
import signal
import sys
import time

# Bootstrap environment
from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


class ManagedSocketModeHandler:
    """Wrapper for SocketModeHandler with better connection management."""

    def __init__(self, app: App, app_token: str):
        self.app = app
        self.app_token = app_token
        self.handler: SocketModeHandler | None = None
        self.running = False
        self.retry_count = 0
        self.max_retries = 3
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start Socket Mode with retry logic."""
        while self.retry_count < self.max_retries and not self.running:
            try:
                self.logger.info(
                    f"Attempting to start Socket Mode (attempt {self.retry_count + 1}/{self.max_retries})"
                )

                # Close any existing handler first
                if self.handler:
                    self.logger.info("Closing existing handler...")
                    self.handler.close()
                    time.sleep(2)  # Give time for cleanup

                # Create new handler with conservative settings
                self.handler = SocketModeHandler(
                    app=self.app,
                    app_token=self.app_token,
                    ping_interval=300,  # 5 minutes
                    auto_reconnect_enabled=True,
                    trace_enabled=False,
                )

                # Add custom error handling
                self._add_error_handling()

                self.logger.info("Starting Socket Mode handler...")
                self.running = True
                self.handler.start()

                # If we get here without exception, reset retry count
                self.retry_count = 0

            except Exception as e:
                self.logger.error(f"Socket Mode failed: {e}")
                self.running = False
                self.retry_count += 1

                if "too_many_websockets" in str(e) or "too_many_websockets" in str(e).lower():
                    self.logger.warning("Too many websockets error - waiting 30s before retry...")
                    time.sleep(30)
                else:
                    self.logger.warning(f"Retrying in {5 * self.retry_count} seconds...")
                    time.sleep(5 * self.retry_count)

        if self.retry_count >= self.max_retries:
            self.logger.error("Max retries exceeded, giving up")
            return False

        return True

    def _add_error_handling(self):
        """Add custom error handling to the Socket Mode handler."""
        if not self.handler:
            return

        original_on_close = getattr(self.handler.client, "on_close", None)
        original_on_error = getattr(self.handler.client, "on_error", None)

        def custom_on_close(data):
            self.logger.info(f"Socket Mode connection closed: {data}")
            if "too_many_websockets" in str(data):
                self.logger.warning("Connection closed due to too many websockets")
                self.running = False
            if original_on_close:
                original_on_close(data)

        def custom_on_error(data):
            self.logger.error(f"Socket Mode error: {data}")
            if original_on_error:
                original_on_error(data)

        # Override handlers
        self.handler.client.on_close = custom_on_close
        self.handler.client.on_error = custom_on_error

    def close(self):
        """Clean shutdown of Socket Mode handler."""
        self.running = False
        if self.handler:
            self.logger.info("Closing Socket Mode handler...")
            self.handler.close()
            self.handler = None


def main():
    """Main function with improved Socket Mode management."""

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Get tokens
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not bot_token or not app_token:
        logger.error("Missing Slack tokens")
        return 1

    logger.info("Creating Slack app...")
    app = App(token=bot_token)

    # Test auth before trying Socket Mode
    try:
        auth_result = app.client.auth_test()
        logger.info(f"✓ Slack auth successful for bot: {auth_result.get('bot_id')}")
    except Exception as e:
        logger.error(f"✗ Slack auth failed: {e}")
        return 1

    # Add simple test handlers
    @app.message("test")
    def handle_test(message, say):
        logger.info("Received test message!")
        say("✓ Socket Mode is working!")

    @app.message("gtd")
    def handle_gtd_test(message, say):
        try:
            from core.gtd_protection import gtd_protector

            text = message.get("text", "").replace("gtd", "").strip()
            if text:
                formatted = gtd_protector.format_with_gtd_fallback(text)
                say(f"GTD formatted: {formatted}")
            else:
                say("Send `gtd <text>` to test GTD formatting")
        except Exception as e:
            logger.error(f"GTD test failed: {e}")
            say(f"GTD test failed: {e}")

    # Create managed handler
    manager = ManagedSocketModeHandler(app, app_token)

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        manager.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start Socket Mode
    logger.info("=== Starting FlowCoach Socket Mode Test ===")
    success = manager.start()

    if not success:
        logger.error("Failed to establish Socket Mode connection")
        return 1

    logger.info("=== Socket Mode Running - Send 'test' or 'gtd <text>' to verify ===")

    # Keep alive
    try:
        while manager.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        manager.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
