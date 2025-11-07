"""Error handling and resilience utilities."""

import functools
import time
import logging
from typing import TypeVar, Callable, Any, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


class FlowCoachError(Exception):
    """Base exception for FlowCoach errors."""

    def __init__(self, message: str, user_hint: str = None, error_code: str = None):
        """
        Initialize FlowCoach error.

        Args:
            message: Technical error message
            user_hint: User-friendly hint for fixing the issue
            error_code: Error code for categorization
        """
        super().__init__(message)
        self.user_hint = user_hint
        self.error_code = error_code


class MissingConfigError(FlowCoachError):
    """Configuration is missing or invalid."""

    def __init__(self, config_key: str, description: str = None):
        message = f"Missing required configuration: {config_key}"
        hint = f"Add {config_key} to your .env file"
        if description:
            hint += f" - {description}"
        super().__init__(message, user_hint=hint, error_code="CONFIG_MISSING")


class InvalidTokenError(FlowCoachError):
    """API token is invalid or expired."""

    def __init__(self, service: str, hint: str = None):
        message = f"Invalid or expired {service} token"
        default_hint = f"Check your {service} API token in .env file"
        user_hint = hint or default_hint
        super().__init__(message, user_hint=user_hint, error_code="TOKEN_INVALID")


class TodoistError(FlowCoachError):
    """Todoist API related errors."""

    def __init__(self, message: str, status_code: int = None):
        if status_code == 401:
            hint = "Check TODOIST_API_TOKEN in your .env file"
            error_code = "TODOIST_AUTH"
        elif status_code == 403:
            hint = "Todoist API access forbidden - check your subscription"
            error_code = "TODOIST_FORBIDDEN"
        elif status_code == 429:
            hint = "Todoist API rate limit reached - try again later"
            error_code = "TODOIST_RATE_LIMIT"
        else:
            hint = "Check your Todoist configuration and internet connection"
            error_code = "TODOIST_ERROR"

        super().__init__(message, user_hint=hint, error_code=error_code)


class SlackError(FlowCoachError):
    """Slack API related errors."""

    def __init__(self, message: str, slack_error: str = None):
        if slack_error == "token_revoked":
            hint = "Slack token has been revoked - regenerate SLACK_BOT_TOKEN"
            error_code = "SLACK_TOKEN_REVOKED"
        elif slack_error == "account_inactive":
            hint = "Slack account is inactive - check your workspace status"
            error_code = "SLACK_ACCOUNT_INACTIVE"
        elif slack_error == "channel_not_found":
            hint = "Slack channel/user not found - check FC_ACTIVE_USERS configuration"
            error_code = "SLACK_CHANNEL_NOT_FOUND"
        elif slack_error == "not_authed":
            hint = "Check SLACK_BOT_TOKEN in your .env file"
            error_code = "SLACK_AUTH"
        else:
            hint = "Check your Slack configuration and bot permissions"
            error_code = "SLACK_ERROR"

        super().__init__(message, user_hint=hint, error_code=error_code)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )

            # Log to events
            log_event(
                severity="error",
                action=f"{func.__name__}_failed",
                payload={
                    "error": str(last_exception),
                    "attempts": max_attempts,
                    "args": str(args)[:200],  # Truncate for safety
                    "kwargs": str(kwargs)[:200]
                }
            )

            raise last_exception

        return wrapper
    return decorator


def log_event(severity: str, action: str, payload: dict) -> None:
    """Log structured event for monitoring."""
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "severity": severity,
        "action": action,
        "payload": payload
    }
    # For now, just log to file. In production, this could go to database or monitoring service
    logger.info(f"EVENT: {json.dumps(event)}")


def format_user_error(error: FlowCoachError) -> str:
    """
    Format a FlowCoach error for user-friendly display.

    Args:
        error: FlowCoach error instance

    Returns:
        Formatted error message with hint
    """
    if error.user_hint:
        return f"❌ {str(error)}\n💡 {error.user_hint}"
    else:
        return f"❌ {str(error)}"


def format_console_error(error: FlowCoachError) -> str:
    """
    Format a FlowCoach error for console output.

    Args:
        error: FlowCoach error instance

    Returns:
        Formatted error message for console
    """
    message = f"ERROR: {str(error)}"
    if error.error_code:
        message += f" (Code: {error.error_code})"
    if error.user_hint:
        message += f"\nSUGGESTION: {error.user_hint}"
    return message


def get_slack_fallback_message(error: Exception) -> dict:
    """
    Generate a Slack fallback message for errors.

    Args:
        error: Exception that occurred

    Returns:
        Slack message blocks for error fallback
    """
    if isinstance(error, FlowCoachError):
        error_text = format_user_error(error)
    else:
        error_text = f"❌ Something went wrong: {str(error)}\n💡 Check your configuration and try again"

    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": error_text
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "If this problem persists, check the logs for more details"
                    }
                ]
            }
        ]
    }


def handle_todoist_error(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to handle Todoist API errors gracefully."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Todoist error in {func.__name__}: {str(e)}")
            log_event(
                severity="error",
                action=f"todoist_{func.__name__}_error",
                payload={"error": str(e)}
            )
            # Return None to indicate failure - caller should handle fallback
            return None
    return wrapper


def handle_slack_error(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to handle Slack API errors gracefully."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Slack error in {func.__name__}: {str(e)}")
            log_event(
                severity="error",
                action=f"slack_{func.__name__}_error",
                payload={"error": str(e)}
            )
            # Return None to indicate failure - caller should handle fallback
            return None
    return wrapper
