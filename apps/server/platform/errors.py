"""Error handling with single-post rule for Slack interactions."""

from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from typing import Any

from .logging import get_logger, new_correlation_id, set_correlation_id

logger = get_logger(__name__)

# Context variable to track if we've already posted an error to Slack
error_posted: ContextVar[bool] = ContextVar("error_posted", default=False)


class FlowCoachError(Exception):
    """Base exception for FlowCoach application."""

    def __init__(
        self,
        message: str,
        user_id: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize FlowCoach error."""
        super().__init__(message)
        self.user_id = user_id
        self.action = action
        self.details = details or {}


class TodoistIntegrationError(FlowCoachError):
    """Error in Todoist integration."""

    pass


class PreferencesError(FlowCoachError):
    """Error in preferences handling."""

    pass


class FeatureFlagError(FlowCoachError):
    """Error related to feature flags."""

    pass


def single_post_error_guard(slack_client=None, fallback_channel: str | None = None):
    """
    Decorator to ensure only one error message is posted to Slack per interaction.

    Args:
        slack_client: Slack client instance for posting messages
        fallback_channel: Channel to post to if user_id not available
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set correlation ID if not already set
            if not hasattr(wrapper, "_correlation_id_set"):
                set_correlation_id(new_correlation_id())
                wrapper._correlation_id_set = True

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error with context
                error_details = {
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()) if kwargs else [],
                    "error_type": type(e).__name__,
                }

                user_id = getattr(e, "user_id", None)
                action = getattr(e, "action", None)

                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    extra_fields=error_details,
                    user_id=user_id,
                    action=action,
                )

                # Post to Slack only if we haven't already posted an error
                if slack_client and not error_posted.get():
                    try:
                        _post_error_to_slack(slack_client, e, user_id, fallback_channel)
                        error_posted.set(True)
                    except Exception as slack_error:
                        logger.error(f"Failed to post error to Slack: {slack_error}")

                # Re-raise the original exception
                raise

        return wrapper

    return decorator


def _post_error_to_slack(
    slack_client, error: Exception, user_id: str | None, fallback_channel: str | None
) -> None:
    """Post error message to Slack (internal function)."""
    # Determine where to post
    channel = user_id or fallback_channel
    if not channel:
        logger.warning("No channel available for Slack error posting")
        return

    # Create user-friendly error message
    if isinstance(error, FlowCoachError):
        message = f":warning: {str(error)}"
    else:
        message = ":warning: Sorry, I encountered an error. Please try again in a moment."

    # Post the message
    try:
        slack_client.chat_postMessage(channel=channel, text=message)
        logger.info(f"Posted error message to Slack channel {channel}")
    except Exception as e:
        logger.error(f"Failed to post to Slack: {e}")
        raise


def handle_todoist_error(func: Callable) -> Callable:
    """Decorator specifically for Todoist integration errors."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert to TodoistIntegrationError with context
            user_id = kwargs.get("user_id") or (args[1] if len(args) > 1 else None)
            raise TodoistIntegrationError(
                f"Todoist integration failed: {str(e)}", user_id=user_id, action=func.__name__
            ) from e

    return wrapper


def handle_preferences_error(func: Callable) -> Callable:
    """Decorator specifically for preferences errors."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert to PreferencesError with context
            user_id = kwargs.get("user_id") or (args[1] if len(args) > 1 else None)
            raise PreferencesError(
                f"Preferences operation failed: {str(e)}", user_id=user_id, action=func.__name__
            ) from e

    return wrapper


def reset_error_context() -> None:
    """Reset error context (for testing or new interactions)."""
    error_posted.set(False)
