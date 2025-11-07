"""Unit tests for database retry logic."""

import unittest
import sqlite3
import tempfile
import os
from unittest.mock import patch, Mock, MagicMock
from apps.server.core.db_retry import db_retry, with_db_retry, DatabaseRetryMixin


class TestDBRetry(unittest.TestCase):
    """Test database retry functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up test environment."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass

    def test_successful_operation_no_retry(self):
        """Test that successful operations don't trigger retry."""
        call_count = 0

        @with_db_retry
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = mock_db_operation()

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)

    def test_retryable_error_recovers(self):
        """Test that retryable errors recover on subsequent attempts."""
        call_count = 0

        @with_db_retry
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise sqlite3.OperationalError("database is locked")
            return "success after retry"

        result = mock_db_operation()

        self.assertEqual(result, "success after retry")
        self.assertEqual(call_count, 3)

    def test_non_retryable_error_fails_immediately(self):
        """Test that non-retryable errors fail immediately."""
        call_count = 0

        @with_db_retry
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a database error")

        with self.assertRaises(ValueError):
            mock_db_operation()

        self.assertEqual(call_count, 1)

    @patch('apps.server.core.db_retry.log_event')
    def test_exhausted_retries_logs_event(self, mock_log_event):
        """Test that exhausted retries log appropriate event."""
        @with_db_retry
        def mock_db_operation():
            raise sqlite3.OperationalError("database is locked")

        with self.assertRaises(sqlite3.OperationalError):
            mock_db_operation()

        # Verify event was logged
        mock_log_event.assert_called_once()
        call_args = mock_log_event.call_args[1]
        self.assertEqual(call_args['severity'], 'error')
        self.assertEqual(call_args['action'], 'db_retry_exhausted')
        self.assertIn('kind', call_args['payload'])
        self.assertEqual(call_args['payload']['kind'], 'db_error')

    def test_custom_retry_parameters(self):
        """Test custom retry parameters work correctly."""
        call_count = 0

        @db_retry(max_attempts=5, delay=0.01, backoff=1.5)
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        result = mock_db_operation()

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 5)

    def test_different_retryable_errors(self):
        """Test different types of retryable database errors."""
        retryable_errors = [
            "database is locked",
            "database table is locked",
            "disk i/o error",
            "unable to open database file"
        ]

        for error_msg in retryable_errors:
            with self.subTest(error=error_msg):
                call_count = 0

                @with_db_retry
                def mock_db_operation():
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise sqlite3.OperationalError(error_msg)
                    return "success"

                result = mock_db_operation()
                self.assertEqual(result, "success")
                self.assertEqual(call_count, 2)

    def test_non_retryable_db_error(self):
        """Test that non-retryable database errors don't retry."""
        call_count = 0

        @with_db_retry
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            raise sqlite3.OperationalError("syntax error")

        with self.assertRaises(sqlite3.OperationalError):
            mock_db_operation()

        # Should only be called once for non-retryable errors
        self.assertEqual(call_count, 1)

    def test_database_retry_mixin(self):
        """Test the DatabaseRetryMixin functionality."""
        class TestClass(DatabaseRetryMixin):
            pass

        test_instance = TestClass()

        # Mock connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor

        # Test execute_with_retry
        result = test_instance.execute_with_retry(mock_conn, "SELECT * FROM test", ())
        self.assertEqual(result, mock_cursor)
        mock_conn.execute.assert_called_with("SELECT * FROM test", ())

        # Test commit_with_retry
        test_instance.commit_with_retry(mock_conn)
        mock_conn.commit.assert_called_once()

        # Test fetchone_with_retry
        mock_cursor.fetchone.return_value = ("test", "data")
        result = test_instance.fetchone_with_retry(mock_conn, "SELECT * FROM test", ())
        self.assertEqual(result, ("test", "data"))

        # Test fetchall_with_retry
        mock_cursor.fetchall.return_value = [("test1", "data1"), ("test2", "data2")]
        result = test_instance.fetchall_with_retry(mock_conn, "SELECT * FROM test", ())
        self.assertEqual(result, [("test1", "data1"), ("test2", "data2")])

    @patch('time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        """Test that exponential backoff works correctly."""
        call_count = 0

        @db_retry(max_attempts=4, delay=0.1, backoff=2.0)
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        result = mock_db_operation()

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 4)

        # Check that sleep was called with exponentially increasing delays
        expected_delays = [0.1, 0.2, 0.4]
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertEqual(actual_delays, expected_delays)


if __name__ == '__main__':
    unittest.main()
