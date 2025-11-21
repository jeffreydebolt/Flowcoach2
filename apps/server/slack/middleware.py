"""Slack middleware for retry handling and deduplication."""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def drop_slack_retries_middleware(logger: logging.Logger):
    """Middleware to drop Slack retry requests.

    Slack retries requests when it doesn't receive a response within 3 seconds.
    This can cause duplicate processing. This middleware drops retries.

    Args:
        logger: Logger instance for debugging

    Returns:
        Middleware function for Slack Bolt
    """

    def middleware(body: dict[str, Any], next: Callable[[], None]) -> None:
        """Check for Slack retry header and drop if present."""
        # Get headers from the request context
        headers = body.get("headers", {})

        # Check for retry header
        retry_num = headers.get("x-slack-retry-num")
        retry_reason = headers.get("x-slack-retry-reason")

        if retry_num:
            logger.info(f"Dropping Slack retry #{retry_num} (reason: {retry_reason})")
            # Don't call next() - this drops the request
            return

        # Not a retry, process normally
        next()

    return middleware


class DeduplicationMiddleware:
    """Middleware to prevent duplicate processing of Slack events."""

    def __init__(self, cache_size: int = 100):
        """Initialize deduplication middleware.

        Args:
            cache_size: Maximum number of event IDs to cache
        """
        self.cache_size = cache_size
        self.processed_events: dict[str, bool] = {}

    def __call__(self, body: dict[str, Any], next: Callable[[], None]) -> None:
        """Check if event was already processed."""
        # Extract event ID or action ID
        event_id = self._extract_event_id(body)

        if event_id and event_id in self.processed_events:
            logger.info(f"Dropping duplicate event: {event_id}")
            return

        # Mark as processed
        if event_id:
            self.processed_events[event_id] = True

            # Trim cache if too large
            if len(self.processed_events) > self.cache_size:
                # Remove oldest entries (dict preserves insertion order in Python 3.7+)
                to_remove = len(self.processed_events) - self.cache_size
                for key in list(self.processed_events.keys())[:to_remove]:
                    del self.processed_events[key]

        # Process the event
        next()

    def _extract_event_id(self, body: dict[str, Any]) -> str | None:
        """Extract a unique ID from the event body."""
        # For events
        if "event" in body and "event_id" in body:
            return body["event_id"]

        # For actions (button clicks, etc)
        if "actions" in body and body["actions"]:
            action = body["actions"][0]
            action_id = action.get("action_id", "")
            trigger_id = body.get("trigger_id", "")
            return f"{action_id}:{trigger_id}"

        # For view submissions
        if "view" in body:
            view = body["view"]
            callback_id = view.get("callback_id", "")
            view_id = view.get("id", "")
            return f"{callback_id}:{view_id}"

        return None
