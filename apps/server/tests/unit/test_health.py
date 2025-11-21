"""Unit tests for health check functionality."""

import json
import unittest
from unittest.mock import Mock, patch

from apps.server.health import HealthChecker, HealthStatus


class TestHealthChecker(unittest.TestCase):
    """Test health check functionality."""

    def setUp(self):
        """Set up test environment."""
        self.mock_dal = Mock()

        with patch("apps.server.health.get_dal", return_value=self.mock_dal):
            self.health_checker = HealthChecker()

    def test_health_status_creation(self):
        """Test HealthStatus creation and serialization."""
        status = HealthStatus(
            status="ok",
            uptime_seconds=3600,
            last_error_time=None,
            error_count_24h=0,
            critical_error_count_24h=0,
            database_status="ok",
            services_status={"database": "ok"},
            timestamp="2023-01-01T12:00:00Z",
        )

        data = status.to_dict()

        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["uptime_seconds"], 3600)
        self.assertIsNone(data["last_error_time"])
        self.assertEqual(data["error_count_24h"], 0)

    @patch("apps.server.health.time.time")
    def test_uptime_calculation(self, mock_time):
        """Test uptime calculation."""
        # Mock time progression
        start_time = 1000000
        current_time = start_time + 3600  # 1 hour later

        mock_time.side_effect = [start_time, current_time]

        with patch("apps.server.health.get_dal", return_value=self.mock_dal):
            checker = HealthChecker()

            # Mock database check
            mock_conn = Mock()
            self.mock_dal.db.get_connection.return_value.__enter__.return_value = mock_conn

            # Mock error query results
            mock_conn.execute.side_effect = [
                Mock(fetchall=lambda: []),  # Error counts query
                Mock(fetchone=lambda: None),  # Last error query
            ]

            status = checker.get_health_status()

            self.assertEqual(status.uptime_seconds, 3600)

    def test_database_health_check_success(self):
        """Test successful database health check."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.execute.return_value = mock_cursor

        self.mock_dal.db.get_connection.return_value.__enter__.return_value = mock_conn

        result = self.health_checker._check_database_health()

        self.assertEqual(result, "ok")
        mock_conn.execute.assert_called_with("SELECT 1")

    def test_database_health_check_failure(self):
        """Test database health check failure."""
        import sqlite3

        self.mock_dal.db.get_connection.side_effect = sqlite3.Error("Database locked")

        result = self.health_checker._check_database_health()

        self.assertEqual(result, "error")

    def test_recent_errors_parsing(self):
        """Test recent errors parsing from database."""
        mock_conn = Mock()

        # Mock error counts query
        mock_cursor1 = Mock()
        mock_cursor1.fetchall.return_value = [("error", 5), ("critical", 2)]

        # Mock last error time query
        mock_cursor2 = Mock()
        mock_cursor2.fetchone.return_value = ("2023-01-01T10:00:00Z",)

        mock_conn.execute.side_effect = [mock_cursor1, mock_cursor2]
        self.mock_dal.db.get_connection.return_value.__enter__.return_value = mock_conn

        result = self.health_checker._get_recent_errors()

        self.assertEqual(result["total_count"], 7)  # 5 + 2
        self.assertEqual(result["critical_count"], 7)  # Both error and critical count as critical
        self.assertEqual(result["last_error_time"], "2023-01-01T10:00:00Z")

    def test_recent_errors_no_errors(self):
        """Test recent errors when no errors found."""
        mock_conn = Mock()

        # Mock empty results
        mock_cursor1 = Mock()
        mock_cursor1.fetchall.return_value = []

        mock_cursor2 = Mock()
        mock_cursor2.fetchone.return_value = None

        mock_conn.execute.side_effect = [mock_cursor1, mock_cursor2]
        self.mock_dal.db.get_connection.return_value.__enter__.return_value = mock_conn

        result = self.health_checker._get_recent_errors()

        self.assertEqual(result["total_count"], 0)
        self.assertEqual(result["critical_count"], 0)
        self.assertIsNone(result["last_error_time"])

    @patch.dict(
        "os.environ",
        {
            "TODOIST_API_TOKEN": "test-token",
            "CLAUDE_API_KEY": "test-key",
            "SLACK_BOT_TOKEN": "test-slack-token",
        },
    )
    def test_services_status_configured(self):
        """Test services status when all services are configured."""
        with patch.object(self.health_checker, "_check_database_health", return_value="ok"):
            result = self.health_checker._check_services_status()

        self.assertEqual(result["database"], "ok")
        self.assertEqual(result["todoist"], "configured")
        self.assertEqual(result["claude"], "configured")
        self.assertEqual(result["slack"], "configured")

    @patch.dict("os.environ", {}, clear=True)
    def test_services_status_not_configured(self):
        """Test services status when services are not configured."""
        with patch.object(self.health_checker, "_check_database_health", return_value="ok"):
            result = self.health_checker._check_services_status()

        self.assertEqual(result["database"], "ok")
        self.assertEqual(result["todoist"], "not_configured")
        self.assertEqual(result["claude"], "not_configured")
        self.assertEqual(result["slack"], "not_configured")

    def test_overall_status_determination(self):
        """Test overall status determination logic."""
        # Test OK status
        status = self.health_checker._determine_overall_status(
            db_status="ok", critical_error_count=1, services_status={"todoist": "configured"}
        )
        self.assertEqual(status, "ok")

        # Test degraded status - too many errors
        status = self.health_checker._determine_overall_status(
            db_status="ok", critical_error_count=5, services_status={"todoist": "configured"}
        )
        self.assertEqual(status, "degraded")

        # Test error status - database error
        status = self.health_checker._determine_overall_status(
            db_status="error", critical_error_count=0, services_status={"todoist": "configured"}
        )
        self.assertEqual(status, "error")

        # Test error status - too many critical errors
        status = self.health_checker._determine_overall_status(
            db_status="ok", critical_error_count=15, services_status={"todoist": "configured"}
        )
        self.assertEqual(status, "error")

        # Test degraded status - todoist not configured
        status = self.health_checker._determine_overall_status(
            db_status="ok", critical_error_count=0, services_status={"todoist": "not_configured"}
        )
        self.assertEqual(status, "degraded")

    def test_get_health_status_integration(self):
        """Test complete health status generation."""
        # Mock all dependencies
        mock_conn = Mock()

        # Mock error queries
        mock_cursor1 = Mock()
        mock_cursor1.fetchall.return_value = [("error", 2)]

        mock_cursor2 = Mock()
        mock_cursor2.fetchone.return_value = ("2023-01-01T10:00:00Z",)

        # Mock database health check
        mock_cursor3 = Mock()
        mock_cursor3.fetchone.return_value = (1,)

        mock_conn.execute.side_effect = [
            mock_cursor1,  # Error counts
            mock_cursor2,  # Last error time
            mock_cursor3,  # Database health check
        ]

        self.mock_dal.db.get_connection.return_value.__enter__.return_value = mock_conn

        with patch.dict("os.environ", {"TODOIST_API_TOKEN": "test-token"}):
            status = self.health_checker.get_health_status()

        self.assertEqual(status.status, "ok")
        self.assertEqual(status.error_count_24h, 2)
        self.assertEqual(status.critical_error_count_24h, 2)
        self.assertEqual(status.database_status, "ok")
        self.assertIn("todoist", status.services_status)

    def test_health_status_exception_handling(self):
        """Test health status generation when exceptions occur."""
        # Make everything fail
        self.mock_dal.db.get_connection.side_effect = Exception("Total failure")

        status = self.health_checker.get_health_status()

        self.assertEqual(status.status, "error")
        self.assertEqual(status.database_status, "error")
        self.assertEqual(status.critical_error_count_24h, 1)


class TestHealthStatusSerialization(unittest.TestCase):
    """Test HealthStatus serialization."""

    def test_to_dict_conversion(self):
        """Test conversion to dictionary for JSON serialization."""
        status = HealthStatus(
            status="ok",
            uptime_seconds=3600,
            last_error_time="2023-01-01T10:00:00Z",
            error_count_24h=5,
            critical_error_count_24h=2,
            database_status="ok",
            services_status={"database": "ok", "todoist": "configured"},
            timestamp="2023-01-01T12:00:00Z",
        )

        data = status.to_dict()

        # Verify all fields are present
        expected_fields = [
            "status",
            "uptime_seconds",
            "last_error_time",
            "error_count_24h",
            "critical_error_count_24h",
            "database_status",
            "services_status",
            "timestamp",
        ]

        for field in expected_fields:
            self.assertIn(field, data)

        # Verify values
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["uptime_seconds"], 3600)
        self.assertEqual(data["services_status"]["todoist"], "configured")

    def test_json_serialization(self):
        """Test that HealthStatus can be JSON serialized."""
        status = HealthStatus(
            status="degraded",
            uptime_seconds=7200,
            last_error_time=None,
            error_count_24h=3,
            critical_error_count_24h=1,
            database_status="ok",
            services_status={"database": "ok"},
            timestamp="2023-01-01T12:00:00Z",
        )

        # Should not raise an exception
        json_str = json.dumps(status.to_dict())

        # Should be able to parse back
        parsed = json.loads(json_str)
        self.assertEqual(parsed["status"], "degraded")
        self.assertEqual(parsed["uptime_seconds"], 7200)
        self.assertIsNone(parsed["last_error_time"])


if __name__ == "__main__":
    unittest.main()
