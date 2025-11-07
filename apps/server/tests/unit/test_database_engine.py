"""Tests for database engine abstraction."""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from apps.server.db.engine import (
    get_db_engine,
    get_db,
    reset_db_engine,
    SQLiteEngine,
    PostgreSQLEngine,
    SupabaseEngine
)


class TestSQLiteEngine:
    """Test SQLite database engine."""

    def test_sqlite_engine_init(self):
        """Test SQLite engine initialization."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            db_path = tmp.name

        try:
            engine = SQLiteEngine(db_path)
            assert engine.driver_name == "sqlite"
            assert engine.db_path == db_path
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_sqlite_engine_default_path(self):
        """Test SQLite engine uses default path when none provided."""
        with patch.dict(os.environ, {'FC_DB_PATH': './test.db'}):
            engine = SQLiteEngine()
            assert engine.db_path == './test.db'

    def test_sqlite_connection_context_manager(self):
        """Test SQLite connection context manager."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            db_path = tmp.name

        try:
            engine = SQLiteEngine(db_path)

            with engine.get_connection() as conn:
                # Test basic query execution
                cursor = conn.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_sqlite_migration_execution(self):
        """Test SQLite migration execution."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            db_path = tmp.name

        try:
            engine = SQLiteEngine(db_path)

            migration_sql = """
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                );
                INSERT INTO test_table (name) VALUES ('test');
            """

            engine.execute_migration(migration_sql)

            # Verify migration was applied
            with engine.get_connection() as conn:
                cursor = conn.execute("SELECT name FROM test_table")
                result = cursor.fetchone()
                assert result[0] == 'test'
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_sqlite_health_check(self):
        """Test SQLite health check."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            db_path = tmp.name

        try:
            engine = SQLiteEngine(db_path)
            assert engine.check_health() is True

            # Test with invalid path
            engine.db_path = "/invalid/path/db.sqlite"
            assert engine.check_health() is False
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestPostgreSQLEngine:
    """Test PostgreSQL database engine."""

    def test_postgresql_engine_requires_psycopg(self):
        """Test PostgreSQL engine requires psycopg package."""
        with patch('apps.server.db.engine.PSYCOPG_AVAILABLE', False):
            with pytest.raises(ImportError, match="psycopg package required"):
                PostgreSQLEngine("postgresql://test:test@localhost/test")

    def test_postgresql_engine_requires_url(self):
        """Test PostgreSQL engine requires database URL."""
        with patch('apps.server.db.engine.PSYCOPG_AVAILABLE', True), \
             patch.dict(os.environ, {}, clear=True):

            with pytest.raises(ValueError, match="FC_DB_URL required"):
                PostgreSQLEngine()

    @patch('apps.server.db.engine.PSYCOPG_AVAILABLE', True)
    @patch('apps.server.db.engine.psycopg', create=True)
    def test_postgresql_engine_init_with_url(self, mock_psycopg):
        """Test PostgreSQL engine initialization with URL."""
        mock_conn = MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn

        engine = PostgreSQLEngine("postgresql://test:test@localhost/test")
        assert engine.driver_name == "postgres"
        assert engine.db_url == "postgresql://test:test@localhost/test"

        # Verify connection was tested
        mock_psycopg.connect.assert_called_with("postgresql://test:test@localhost/test")

    @patch('apps.server.db.engine.PSYCOPG_AVAILABLE', True)
    @patch('apps.server.db.engine.psycopg', create=True)
    def test_postgresql_connection_context_manager(self, mock_psycopg):
        """Test PostgreSQL connection context manager."""
        mock_conn = MagicMock()
        mock_psycopg.connect.return_value = mock_conn

        engine = PostgreSQLEngine("postgresql://test:test@localhost/test")

        with engine.get_connection() as conn:
            assert conn == mock_conn

        mock_conn.close.assert_called_once()

    @patch('apps.server.db.engine.PSYCOPG_AVAILABLE', True)
    @patch('apps.server.db.engine.psycopg', create=True)
    def test_postgresql_migration_execution(self, mock_psycopg):
        """Test PostgreSQL migration execution."""
        # Mock for constructor test connection
        mock_test_conn = MagicMock()
        # Mock for migration execution
        mock_migration_conn = MagicMock()

        mock_psycopg.connect.side_effect = [mock_test_conn, mock_migration_conn]

        engine = PostgreSQLEngine("postgresql://test:test@localhost/test")

        migration_sql = "CREATE TABLE test (id SERIAL PRIMARY KEY);"
        engine.execute_migration(migration_sql)

        # Verify migration execution
        mock_migration_conn.execute.assert_called_with(migration_sql)
        mock_migration_conn.commit.assert_called_once()
        mock_migration_conn.close.assert_called_once()

    @patch('apps.server.db.engine.PSYCOPG_AVAILABLE', True)
    @patch('apps.server.db.engine.psycopg', create=True)
    def test_postgresql_health_check(self, mock_psycopg):
        """Test PostgreSQL health check."""
        # Mock for constructor test connection
        mock_test_conn = MagicMock()
        # Mock for health check
        mock_health_conn = MagicMock()

        mock_psycopg.connect.side_effect = [mock_test_conn, mock_health_conn]

        engine = PostgreSQLEngine("postgresql://test:test@localhost/test")

        # Test successful health check
        assert engine.check_health() is True
        mock_health_conn.execute.assert_called_with("SELECT 1")
        mock_health_conn.close.assert_called_once()

        # Test failed health check
        mock_failed_conn = MagicMock()
        mock_failed_conn.execute.side_effect = Exception("Connection failed")
        mock_psycopg.connect.return_value = mock_failed_conn

        assert engine.check_health() is False


class TestSupabaseEngine:
    """Test Supabase database engine."""

    def test_supabase_engine_requires_supabase_package(self):
        """Test Supabase engine requires supabase package."""
        with patch('apps.server.db.engine.SUPABASE_AVAILABLE', False):
            with pytest.raises(ImportError, match="supabase package required"):
                SupabaseEngine("https://test.supabase.co", "service_key")

    def test_supabase_engine_requires_credentials(self):
        """Test Supabase engine requires URL and service key."""
        with patch('apps.server.db.engine.SUPABASE_AVAILABLE', True), \
             patch.dict(os.environ, {}, clear=True):

            with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_KEY required"):
                SupabaseEngine()

    @patch('apps.server.db.engine.SUPABASE_AVAILABLE', True)
    @patch('apps.server.db.engine.create_client')
    @patch('apps.server.db.engine.PostgreSQLEngine')
    def test_supabase_engine_init(self, mock_pg_engine, mock_create_client):
        """Test Supabase engine initialization."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        engine = SupabaseEngine("https://test.supabase.co", "service_key")
        assert engine.driver_name == "supabase"
        assert engine.url == "https://test.supabase.co"
        assert engine.service_key == "service_key"

        # Verify Supabase client was created
        mock_create_client.assert_called_with("https://test.supabase.co", "service_key")

    @patch('apps.server.db.engine.SUPABASE_AVAILABLE', True)
    @patch('apps.server.db.engine.create_client')
    @patch('apps.server.db.engine.PostgreSQLEngine')
    def test_supabase_health_check_success(self, mock_pg_engine, mock_create_client):
        """Test successful Supabase health check."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Mock successful REST API call
        mock_result = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_result

        engine = SupabaseEngine("https://test.supabase.co", "service_key")
        assert engine.check_health() is True

    @patch('apps.server.db.engine.SUPABASE_AVAILABLE', True)
    @patch('apps.server.db.engine.create_client')
    @patch('apps.server.db.engine.PostgreSQLEngine')
    def test_supabase_health_check_fallback(self, mock_pg_engine, mock_create_client):
        """Test Supabase health check falls back to PostgreSQL."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Mock failed REST API call
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("API error")

        # Mock PostgreSQL engine health check
        mock_pg_instance = MagicMock()
        mock_pg_instance.check_health.return_value = True
        mock_pg_engine.return_value = mock_pg_instance

        engine = SupabaseEngine("https://test.supabase.co", "service_key")
        assert engine.check_health() is True
        mock_pg_instance.check_health.assert_called_once()


class TestDatabaseEngineFactory:
    """Test database engine factory functions."""

    def test_get_db_engine_sqlite_default(self):
        """Test get_db_engine returns SQLite by default."""
        with patch.dict(os.environ, {}, clear=True):
            engine = get_db_engine()
            assert isinstance(engine, SQLiteEngine)

    def test_get_db_engine_explicit_sqlite(self):
        """Test get_db_engine returns SQLite when explicitly set."""
        with patch.dict(os.environ, {'FC_DB_DRIVER': 'sqlite'}):
            engine = get_db_engine()
            assert isinstance(engine, SQLiteEngine)

    @patch('apps.server.db.engine.PSYCOPG_AVAILABLE', True)
    @patch('apps.server.db.engine.psycopg', create=True)
    def test_get_db_engine_postgresql(self, mock_psycopg):
        """Test get_db_engine returns PostgreSQL engine."""
        mock_conn = MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn

        with patch.dict(os.environ, {'FC_DB_DRIVER': 'postgres', 'FC_DB_URL': 'postgresql://test'}):
            engine = get_db_engine()
            assert isinstance(engine, PostgreSQLEngine)

    @patch('apps.server.db.engine.SUPABASE_AVAILABLE', True)
    @patch('apps.server.db.engine.create_client')
    @patch('apps.server.db.engine.PostgreSQLEngine')
    def test_get_db_engine_supabase(self, mock_pg_engine, mock_create_client):
        """Test get_db_engine returns Supabase engine."""
        with patch.dict(os.environ, {
            'FC_DB_DRIVER': 'supabase',
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'service_key'
        }):
            engine = get_db_engine()
            assert isinstance(engine, SupabaseEngine)

    def test_get_db_engine_invalid_driver(self):
        """Test get_db_engine raises error for invalid driver."""
        with patch.dict(os.environ, {'FC_DB_DRIVER': 'invalid'}):
            with pytest.raises(ValueError, match="Unsupported database driver: invalid"):
                get_db_engine()

    @patch('apps.server.db.engine.get_db_engine')
    def test_get_db_singleton(self, mock_get_engine):
        """Test get_db returns singleton instance."""
        mock_engine = MagicMock()
        mock_engine.driver_name = "test"
        mock_get_engine.return_value = mock_engine

        # Reset singleton
        reset_db_engine()

        # First call should create instance
        engine1 = get_db()
        assert engine1 == mock_engine
        assert mock_get_engine.call_count == 1

        # Second call should return same instance
        engine2 = get_db()
        assert engine2 == mock_engine
        assert engine2 is engine1
        assert mock_get_engine.call_count == 1  # Should not be called again

    def test_reset_db_engine(self):
        """Test reset_db_engine clears singleton."""
        # First reset to ensure clean state
        reset_db_engine()

        # Create a mock engine
        with patch('apps.server.db.engine.get_db_engine') as mock_get_engine:
            mock_engine1 = MagicMock()
            mock_engine1.driver_name = "test1"
            mock_engine2 = MagicMock()
            mock_engine2.driver_name = "test2"
            mock_get_engine.side_effect = [mock_engine1, mock_engine2]

            # Get initial instance
            engine1 = get_db()
            assert engine1 == mock_engine1

            # Reset and get new instance
            reset_db_engine()
            engine2 = get_db()
            assert engine2 == mock_engine2

            # Should have called get_db_engine twice
            assert mock_get_engine.call_count == 2
