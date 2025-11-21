"""
Main application entry point for FlowCoach Slack bot.
"""

# Bootstrap environment variables in local mode
from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

import logging
import signal
import sys
import time

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import get_config
from handlers import register_handlers
from services import initialize_services

# Load configuration
config = get_config()

# Configure logging
log_level = config["app"]["log_level"]
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global handler for cleanup
socket_handler = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received shutdown signal ({signal.Signals(signum).name})")
    if socket_handler:
        logger.info("Closing Socket Mode connection...")
        socket_handler.close()
    logger.info("Exiting FlowCoach application.")
    sys.exit(0)


def main():
    """Main function to initialize and run the Slack bot."""
    logger.info("=== Starting FlowCoach Application ===")

    # Verify essential configuration
    if not config["slack"]["bot_token"] or not config["slack"]["app_token"]:
        logger.error("Missing required Slack tokens in configuration.")
        return 1
    if not config["todoist"]["api_token"]:
        logger.warning("Missing Todoist API token. Todoist features will be limited.")
    # Add checks for other critical configs as needed

    # Initialize services (Todoist, Calendar, OpenAI, etc.)
    logger.info("Initializing services...")
    services = initialize_services(config)
    if not services:
        logger.error("Failed to initialize essential services. Exiting.")
        return 1
    logger.info("Services initialized successfully.")

    # Initialize Slack app
    logger.info("Initializing Slack app...")
    try:
        app = App(token=config["slack"]["bot_token"])
    except Exception as e:
        logger.error(f"Failed to initialize Slack app: {e}", exc_info=True)
        return 1

    # Register middleware
    from apps.server.slack.middleware import DeduplicationMiddleware, drop_slack_retries_middleware

    logger.info("Registering middleware...")
    app.middleware(drop_slack_retries_middleware(logger))
    app.middleware(DeduplicationMiddleware())

    # Register handlers (message, command, action, event)
    logger.info("Registering handlers...")
    register_handlers(app, services)
    logger.info("Handlers registered successfully.")

    # Start Socket Mode handler
    global socket_handler
    logger.info("Starting Socket Mode handler...")
    try:
        socket_handler = SocketModeHandler(
            app,
            config["slack"]["app_token"],
            ping_interval=30,  # Send ping every 30 seconds
            ping_pong_reply_timeout=10,  # Wait 10 seconds for pong response
        )
        # Test connection
        logger.info("Testing Slack authentication...")
        auth_result = app.client.auth_test()
        logger.info(f"Slack auth successful for bot_id: {auth_result.get('bot_id')}")

        socket_handler.start()
    except Exception as e:
        logger.error(f"Failed to start Socket Mode handler: {e}", exc_info=True)
        return 1

    logger.info("=== FlowCoach Application Running ===")
    # Keep the main thread alive (SocketModeHandler runs in its own threads)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        sys.exit(main())
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if socket_handler:
            socket_handler.close()
