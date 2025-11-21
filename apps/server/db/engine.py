"""Database engine abstraction for FlowCoach."""

import logging
import os
import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Optional imports for PostgreSQL and Supabase
try:
    import psycopg
    from psycopg import OperationalError as PsycopgOperationalError

    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    PsycopgOperationalError = Exception

try:
    from supabase import Client, create_client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


class DatabaseConnection(Protocol):
    """Protocol for database connections."""

    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute a query with parameters."""
        ...

    def commit(self) -> None:
        """Commit the current transaction."""
        ...

    def rollback(self) -> None:
        """Rollback the current transaction."""
        ...

    def close(self) -> None:
        """Close the connection."""
        ...


class DatabaseEngine(ABC):
    """Abstract base class for database engines."""

    @abstractmethod
    def get_connection(self) -> DatabaseConnection:
        """Get a database connection."""
        pass

    @abstractmethod
    def execute_migration(self, migration_sql: str) -> None:
        """Execute a migration."""
        pass

    @abstractmethod
    def check_health(self) -> bool:
        """Check if database is healthy."""
        pass

    @property
    @abstractmethod
    def driver_name(self) -> str:
        """Get the driver name."""
        pass


class SQLiteEngine(DatabaseEngine):
    """SQLite database engine."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("FC_DB_PATH", "./flowcoach.db")
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database schema."""
        with self.get_connection() as conn:
            # Create tables from Sprint 1
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS weekly_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    week_start DATE NOT NULL,
                    outcomes TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, week_start)
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    impact INTEGER NOT NULL,
                    urgency INTEGER NOT NULL,
                    energy TEXT NOT NULL,
                    total_score INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    severity TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload TEXT,
                    user_id TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS morning_brief_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    task_content TEXT NOT NULL,
                    surfaced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'surfaced'
                )
            """
            )

            # New Sprint 2 table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_momentum (
                    project_id TEXT PRIMARY KEY,
                    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    momentum_score INTEGER DEFAULT 100,
                    status TEXT DEFAULT 'active',
                    outcome_defined BOOLEAN DEFAULT FALSE,
                    due_date DATE NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get SQLite connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def execute_migration(self, migration_sql: str) -> None:
        """Execute a migration on SQLite."""
        with self.get_connection() as conn:
            conn.executescript(migration_sql)
            conn.commit()

    def check_health(self) -> bool:
        """Check SQLite health."""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except Exception as e:
            logger.error(f"SQLite health check failed: {e}")
            return False

    @property
    def driver_name(self) -> str:
        return "sqlite"


class PostgreSQLEngine(DatabaseEngine):
    """PostgreSQL database engine."""

    def __init__(self, db_url: str = None):
        if not PSYCOPG_AVAILABLE:
            raise ImportError(
                "psycopg package required for PostgreSQL support. Install with: pip install psycopg[binary]"
            )

        self.db_url = db_url or os.getenv("FC_DB_URL")
        if not self.db_url:
            raise ValueError("FC_DB_URL required for PostgreSQL driver")

        # Test connection
        self._test_connection()

    def _test_connection(self):
        """Test PostgreSQL connection."""
        try:
            with psycopg.connect(self.db_url) as conn:
                conn.execute("SELECT 1")
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get PostgreSQL connection with context manager."""
        conn = psycopg.connect(self.db_url)
        try:
            yield conn
        finally:
            conn.close()

    def execute_migration(self, migration_sql: str) -> None:
        """Execute a migration on PostgreSQL."""
        with self.get_connection() as conn:
            conn.execute(migration_sql)
            conn.commit()

    def check_health(self) -> bool:
        """Check PostgreSQL health."""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

    @property
    def driver_name(self) -> str:
        return "postgres"


class SupabaseEngine(DatabaseEngine):
    """Supabase database engine (PostgreSQL with REST API)."""

    def __init__(self, url: str = None, service_key: str = None):
        if not SUPABASE_AVAILABLE:
            raise ImportError(
                "supabase package required for Supabase support. Install with: pip install supabase"
            )

        self.url = url or os.getenv("SUPABASE_URL")
        self.service_key = service_key or os.getenv("SUPABASE_SERVICE_KEY")

        if not self.url or not self.service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required for Supabase driver")

        self.client: Client = create_client(self.url, self.service_key)

        # For SQL operations, we'll use the underlying PostgreSQL connection
        # This is a simplified implementation - in production you might want to use the REST API
        self.pg_url = self._build_postgres_url()
        self.pg_engine = PostgreSQLEngine(self.pg_url)

    def _build_postgres_url(self) -> str:
        """Build PostgreSQL URL from Supabase credentials."""
        # Extract database info from Supabase URL
        # This is a simplified approach - in production, you'd get this from Supabase settings
        host = self.url.replace("https://", "").replace("http://", "")
        # Note: This is a placeholder - actual implementation would need proper Supabase DB credentials
        return f"postgresql://postgres:{self.service_key}@db.{host}:5432/postgres"

    @contextmanager
    def get_connection(self):
        """Get connection via PostgreSQL engine."""
        with self.pg_engine.get_connection() as conn:
            yield conn

    def execute_migration(self, migration_sql: str) -> None:
        """Execute migration via PostgreSQL engine."""
        self.pg_engine.execute_migration(migration_sql)

    def check_health(self) -> bool:
        """Check Supabase health."""
        try:
            # Test REST API
            result = self.client.table("weekly_outcomes").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return self.pg_engine.check_health()

    @property
    def driver_name(self) -> str:
        return "supabase"


def get_db_engine() -> DatabaseEngine:
    """
    Get database engine based on FC_DB_DRIVER environment variable.

    Returns:
        DatabaseEngine instance
    """
    driver = os.getenv("FC_DB_DRIVER", "sqlite").lower()

    if driver == "sqlite":
        return SQLiteEngine()
    elif driver == "postgres":
        return PostgreSQLEngine()
    elif driver == "supabase":
        return SupabaseEngine()
    else:
        raise ValueError(
            f"Unsupported database driver: {driver}. Use 'sqlite', 'postgres', or 'supabase'"
        )


# Global database engine instance
_db_engine: DatabaseEngine | None = None


def get_db() -> DatabaseEngine:
    """
    Get global database engine instance (singleton).

    Returns:
        DatabaseEngine instance
    """
    global _db_engine
    if _db_engine is None:
        _db_engine = get_db_engine()
        logger.info(f"Initialized database engine: {_db_engine.driver_name}")
    return _db_engine


def reset_db_engine():
    """Reset global database engine (for testing)."""
    global _db_engine
    _db_engine = None
