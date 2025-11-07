"""Database retry logic for handling SQLite and PostgreSQL operational errors."""

import functools
import time
import logging
import sqlite3
from typing import TypeVar, Callable, Any, Optional

from .errors import log_event

# Optional PostgreSQL import
try:
    import psycopg
    from psycopg import OperationalError as PsycopgOperationalError
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    PsycopgOperationalError = Exception

logger = logging.getLogger(__name__)

T = TypeVar('T')


def db_retry(
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator for database operations supporting SQLite and PostgreSQL.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 0.1s)
        backoff: Multiplier for delay after each retry (default: 2.0)

    Returns:
        Decorated function with retry logic

    Handles:
        - SQLite: database locks, disk I/O errors
        - PostgreSQL: connection errors, temporary failures, deadlocks
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    last_exception = e
                    error_msg = str(e).lower()

                    # Check if it's a retryable SQLite error
                    if any(retryable in error_msg for retryable in [
                        'database is locked',
                        'database table is locked',
                        'disk i/o error',
                        'unable to open database file'
                    ]):
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"SQLite operation failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                                f"Retrying in {current_delay:.2f}s..."
                            )
                            time.sleep(current_delay)
                            current_delay *= backoff
                            continue

                    # Non-retryable error or final attempt - break and handle below
                    logger.error(f"SQLite error in {func.__name__}: {e}")
                    break
                except PsycopgOperationalError as e:
                    if not PSYCOPG_AVAILABLE:
                        # This shouldn't happen, but handle gracefully
                        logger.error(f"PostgreSQL error but psycopg not available in {func.__name__}: {e}")
                        raise

                    last_exception = e
                    error_msg = str(e).lower()

                    # Check if it's a retryable PostgreSQL error
                    if any(retryable in error_msg for retryable in [
                        'connection',
                        'timeout',
                        'server closed the connection',
                        'deadlock detected',
                        'could not serialize access',
                        'temporary failure',
                        'connection refused',
                        'no route to host',
                        'network is unreachable'
                    ]):
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"PostgreSQL operation failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                                f"Retrying in {current_delay:.2f}s..."
                            )
                            time.sleep(current_delay)
                            current_delay *= backoff
                            continue

                    # Non-retryable error or final attempt - break and handle below
                    logger.error(f"PostgreSQL error in {func.__name__}: {e}")
                    break
                except Exception as e:
                    # Non-database error - don't retry
                    logger.error(f"Non-database error in {func.__name__}: {e}")
                    raise

            # Log final failure
            error_type = "unknown"
            if isinstance(last_exception, sqlite3.OperationalError):
                error_type = "sqlite"
            elif PSYCOPG_AVAILABLE and isinstance(last_exception, PsycopgOperationalError):
                error_type = "postgresql"

            log_event(
                severity="error",
                action="db_retry_exhausted",
                payload={
                    "function": func.__name__,
                    "error": str(last_exception),
                    "attempts": max_attempts,
                    "error_type": error_type,
                    "kind": "db_error"
                }
            )

            # Re-raise the last database exception
            raise last_exception

        return wrapper
    return decorator


class DatabaseRetryMixin:
    """Mixin class to add retry logic to database operations."""

    @db_retry()
    def execute_with_retry(self, conn, query: str, params: tuple = ()) -> Any:
        """Execute a database query with retry logic."""
        cursor = conn.execute(query, params)
        return cursor

    @db_retry()
    def commit_with_retry(self, conn) -> None:
        """Commit a database transaction with retry logic."""
        conn.commit()

    @db_retry()
    def fetchone_with_retry(self, conn, query: str, params: tuple = ()) -> Optional[tuple]:
        """Fetch one row with retry logic."""
        cursor = conn.execute(query, params)
        return cursor.fetchone()

    @db_retry()
    def fetchall_with_retry(self, conn, query: str, params: tuple = ()) -> list:
        """Fetch all rows with retry logic."""
        cursor = conn.execute(query, params)
        return cursor.fetchall()


def with_db_retry(func: Callable[..., T]) -> Callable[..., T]:
    """
    Convenience decorator that applies db_retry with default settings.
    Use this for most database operations.
    """
    return db_retry()(func)
