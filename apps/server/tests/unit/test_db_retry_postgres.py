"""Tests for PostgreSQL retry logic in db_retry module."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from apps.server.core.db_retry import db_retry, with_db_retry, PSYCOPG_AVAILABLE


class MockPsycopgError(Exception):
    """Mock PostgreSQL operational error."""
    pass


class TestPostgreSQLRetry:
    """Test database retry logic for PostgreSQL errors."""

    def test_postgresql_connection_error_retry(self):
        """Test that PostgreSQL connection errors are retried."""
        call_count = 0

        @db_retry(max_attempts=3, delay=0.01, backoff=2.0)
        def failing_postgres_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MockPsycopgError("connection to server was lost")
            return "success"

        # Mock psycopg availability and error class
        with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', True), \
             patch('apps.server.core.db_retry.PsycopgOperationalError', MockPsycopgError), \
             patch('apps.server.core.db_retry.log_event'):

            result = failing_postgres_operation()
            assert result == "success"
            assert call_count == 3

    def test_postgresql_deadlock_retry(self):
        """Test that PostgreSQL deadlock errors are retried."""
        call_count = 0

        @db_retry(max_attempts=2, delay=0.01)
        def deadlock_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise MockPsycopgError("deadlock detected")
            return "resolved"

        with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', True), \
             patch('apps.server.core.db_retry.PsycopgOperationalError', MockPsycopgError), \
             patch('apps.server.core.db_retry.log_event'):

            result = deadlock_operation()
            assert result == "resolved"
            assert call_count == 2

    def test_postgresql_serialization_error_retry(self):
        """Test that PostgreSQL serialization errors are retried."""
        call_count = 0

        @db_retry(max_attempts=2, delay=0.01)
        def serialization_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise MockPsycopgError("could not serialize access due to concurrent update")
            return "serialized"

        with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', True), \
             patch('apps.server.core.db_retry.PsycopgOperationalError', MockPsycopgError), \
             patch('apps.server.core.db_retry.log_event'):

            result = serialization_operation()
            assert result == "serialized"
            assert call_count == 2

    def test_postgresql_timeout_retry(self):
        """Test that PostgreSQL timeout errors are retried."""
        @db_retry(max_attempts=2, delay=0.01)
        def timeout_operation():
            raise MockPsycopgError("timeout expired")

        with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', True), \
             patch('apps.server.core.db_retry.PsycopgOperationalError', MockPsycopgError), \
             patch('apps.server.core.db_retry.log_event') as mock_log:

            with pytest.raises(MockPsycopgError):
                timeout_operation()

            # Verify error was logged with correct error type
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['severity'] == 'error'
            assert call_args['action'] == 'db_retry_exhausted'
            assert call_args['payload']['error_type'] == 'postgresql'

    def test_postgresql_non_retryable_error(self):
        """Test that PostgreSQL non-retryable errors are not retried."""
        call_count = 0

        @db_retry(max_attempts=3, delay=0.01)
        def non_retryable_operation():
            nonlocal call_count
            call_count += 1
            raise MockPsycopgError("relation 'table_name' does not exist")

        with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', True), \
             patch('apps.server.core.db_retry.PsycopgOperationalError', MockPsycopgError), \
             patch('apps.server.core.db_retry.log_event'):

            with pytest.raises(MockPsycopgError):
                non_retryable_operation()

            # Should only be called once (not retried)
            assert call_count == 1

    def test_postgresql_retry_backoff_timing(self):
        """Test that PostgreSQL retry backoff timing works correctly."""
        call_times = []

        @db_retry(max_attempts=3, delay=0.05, backoff=2.0)
        def timed_operation():
            call_times.append(time.time())
            raise MockPsycopgError("connection refused")

        with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', True), \
             patch('apps.server.core.db_retry.PsycopgOperationalError', MockPsycopgError), \
             patch('apps.server.core.db_retry.log_event'):

            with pytest.raises(MockPsycopgError):
                timed_operation()

            assert len(call_times) == 3

            # Check timing between attempts (allowing for some variance)
            first_gap = call_times[1] - call_times[0]
            second_gap = call_times[2] - call_times[1]

            assert 0.04 < first_gap < 0.08  # ~0.05s with tolerance
            assert 0.08 < second_gap < 0.15  # ~0.10s with tolerance

    def test_postgresql_error_without_psycopg(self):
        """Test handling PostgreSQL errors when psycopg not available."""

        @db_retry(max_attempts=2, delay=0.01)
        def postgres_without_psycopg():
            # This should use the fallback Exception class
            from apps.server.core.db_retry import PsycopgOperationalError
            raise PsycopgOperationalError("connection error")

        # Test when PSYCOPG_AVAILABLE is False
        with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', False):

            with pytest.raises(Exception):
                postgres_without_psycopg()

    def test_mixed_sqlite_postgresql_errors(self):
        """Test that both SQLite and PostgreSQL errors can be handled."""
        import sqlite3
        call_count = 0

        @db_retry(max_attempts=3, delay=0.01)
        def mixed_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise sqlite3.OperationalError("database is locked")
            elif call_count == 2:
                raise MockPsycopgError("connection to server was lost")
            return "success"

        with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', True), \
             patch('apps.server.core.db_retry.PsycopgOperationalError', MockPsycopgError), \
             patch('apps.server.core.db_retry.log_event'):

            result = mixed_errors()
            assert result == "success"
            assert call_count == 3

    def test_postgresql_network_errors(self):
        """Test that PostgreSQL network errors are retried."""
        network_errors = [
            "no route to host",
            "network is unreachable",
            "connection refused",
            "server closed the connection unexpectedly"
        ]

        for error_msg in network_errors:
            call_count = 0

            @db_retry(max_attempts=2, delay=0.01)
            def network_operation():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise MockPsycopgError(error_msg)
                return "connected"

            with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', True), \
                 patch('apps.server.core.db_retry.PsycopgOperationalError', MockPsycopgError), \
                 patch('apps.server.core.db_retry.log_event'):

                result = network_operation()
                assert result == "connected"
                assert call_count == 2


class TestDatabaseRetryCompatibility:
    """Test that existing SQLite functionality still works with PostgreSQL support."""

    def test_sqlite_errors_still_work(self):
        """Test that SQLite error handling is unchanged."""
        import sqlite3
        call_count = 0

        @db_retry(max_attempts=2, delay=0.01)
        def sqlite_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise sqlite3.OperationalError("database is locked")
            return "unlocked"

        with patch('apps.server.core.db_retry.log_event'):
            result = sqlite_operation()
            assert result == "unlocked"
            assert call_count == 2

    def test_non_database_errors_not_affected(self):
        """Test that non-database errors are not retried."""
        call_count = 0

        @db_retry(max_attempts=3, delay=0.01)
        def non_db_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("This is not a database error")

        with pytest.raises(ValueError):
            non_db_operation()

        # Should only be called once
        assert call_count == 1

    def test_with_db_retry_convenience_wrapper(self):
        """Test that the convenience wrapper works with PostgreSQL errors."""
        call_count = 0

        @with_db_retry
        def postgres_convenience():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise MockPsycopgError("temporary failure in name resolution")
            return "resolved"

        with patch('apps.server.core.db_retry.PSYCOPG_AVAILABLE', True), \
             patch('apps.server.core.db_retry.PsycopgOperationalError', MockPsycopgError), \
             patch('apps.server.core.db_retry.log_event'):

            result = postgres_convenience()
            assert result == "resolved"
            assert call_count == 2
