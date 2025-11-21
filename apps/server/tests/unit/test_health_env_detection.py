"""Tests for health endpoint environment variable detection."""

import os
from unittest.mock import MagicMock, patch

from apps.server.health import HealthChecker


class TestHealthEnvDetection:
    """Test health endpoint service detection."""

    def test_services_marked_ok_when_env_vars_set(self):
        """Test that services are marked 'ok' when environment variables are set."""
        with (
            patch.dict(
                os.environ,
                {
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "TODOIST_API_TOKEN": "test-todoist-token",
                    "CLAUDE_API_KEY": "test-claude-key",
                },
                clear=False,
            ),
            patch("apps.server.health.get_dal") as mock_get_dal,
        ):

            # Mock DAL and database engine
            mock_dal = MagicMock()
            mock_db_engine = MagicMock()
            mock_dal.db_engine = mock_db_engine
            mock_get_dal.return_value = mock_dal

            # Mock successful database connection
            mock_conn = MagicMock()
            mock_db_engine.get_connection.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value.fetchone.return_value = (1,)
            mock_conn.execute.return_value.fetchall.return_value = []

            checker = HealthChecker()
            services = checker._check_services_status()

            assert services["slack"] == "ok"
            assert services["todoist"] == "ok"
            assert services["claude"] == "ok"
            assert services["database"] == "ok"

    def test_services_marked_not_configured_when_missing(self):
        """Test that services are marked 'not_configured' when env vars are missing."""
        # Clear all service-related environment variables
        env_vars_to_clear = ["SLACK_BOT_TOKEN", "TODOIST_API_TOKEN", "CLAUDE_API_KEY"]

        # Create a clean environment without these variables
        clean_env = {k: v for k, v in os.environ.items() if k not in env_vars_to_clear}

        with (
            patch.dict(os.environ, clean_env, clear=True),
            patch("apps.server.health.get_dal") as mock_get_dal,
        ):

            # Mock DAL and database engine
            mock_dal = MagicMock()
            mock_db_engine = MagicMock()
            mock_dal.db_engine = mock_db_engine
            mock_get_dal.return_value = mock_dal

            # Mock successful database connection
            mock_conn = MagicMock()
            mock_db_engine.get_connection.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value.fetchone.return_value = (1,)

            checker = HealthChecker()
            services = checker._check_services_status()

            assert services["slack"] == "not_configured"
            assert services["todoist"] == "not_configured"
            assert services["claude"] == "not_configured"

    def test_env_vars_trimmed_for_whitespace(self):
        """Test that environment variables with trailing spaces are properly trimmed."""
        with (
            patch.dict(
                os.environ,
                {
                    "SLACK_BOT_TOKEN": "  xoxb-test-token  ",
                    "TODOIST_API_TOKEN": "\ttest-todoist-token\t",
                    "CLAUDE_API_KEY": "\ntest-claude-key\n",
                },
                clear=False,
            ),
            patch("apps.server.health.get_dal") as mock_get_dal,
        ):

            # Mock DAL and database engine
            mock_dal = MagicMock()
            mock_db_engine = MagicMock()
            mock_dal.db_engine = mock_db_engine
            mock_get_dal.return_value = mock_dal

            # Mock successful database connection
            mock_conn = MagicMock()
            mock_db_engine.get_connection.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value.fetchone.return_value = (1,)
            mock_conn.execute.return_value.fetchall.return_value = []

            checker = HealthChecker()
            services = checker._check_services_status()

            # Should be marked as ok despite whitespace
            assert services["slack"] == "ok"
            assert services["todoist"] == "ok"
            assert services["claude"] == "ok"

    def test_empty_env_vars_marked_not_configured(self):
        """Test that empty environment variables are marked as not configured."""
        with (
            patch.dict(
                os.environ,
                {
                    "SLACK_BOT_TOKEN": "",
                    "TODOIST_API_TOKEN": "   ",  # Just whitespace
                    "CLAUDE_API_KEY": "\t\n",  # Just whitespace characters
                },
                clear=False,
            ),
            patch("apps.server.health.get_dal") as mock_get_dal,
        ):

            # Mock DAL and database engine
            mock_dal = MagicMock()
            mock_db_engine = MagicMock()
            mock_dal.db_engine = mock_db_engine
            mock_get_dal.return_value = mock_dal

            # Mock successful database connection
            mock_conn = MagicMock()
            mock_db_engine.get_connection.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value.fetchone.return_value = (1,)

            checker = HealthChecker()
            services = checker._check_services_status()

            # Should be marked as not_configured since they're empty after trimming
            assert services["slack"] == "not_configured"
            assert services["todoist"] == "not_configured"
            assert services["claude"] == "not_configured"

    def test_overall_status_ok_when_all_services_ok(self):
        """Test that overall status is 'ok' when database and all services are ok."""
        services_status = {"database": "ok", "slack": "ok", "todoist": "ok", "claude": "ok"}

        with patch("apps.server.health.get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_get_dal.return_value = mock_dal

            checker = HealthChecker()
            overall_status = checker._determine_overall_status("ok", 0, services_status)

            assert overall_status == "ok"

    def test_overall_status_degraded_when_service_not_configured(self):
        """Test that overall status is 'degraded' when any service is not configured."""
        services_status = {
            "database": "ok",
            "slack": "ok",
            "todoist": "not_configured",  # One service not configured
            "claude": "ok",
        }

        with patch("apps.server.health.get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_get_dal.return_value = mock_dal

            checker = HealthChecker()
            overall_status = checker._determine_overall_status("ok", 0, services_status)

            assert overall_status == "degraded"

    def test_overall_status_error_when_database_error(self):
        """Test that overall status is 'error' when database has an error."""
        services_status = {"database": "error", "slack": "ok", "todoist": "ok", "claude": "ok"}

        with patch("apps.server.health.get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_get_dal.return_value = mock_dal

            checker = HealthChecker()
            overall_status = checker._determine_overall_status("error", 0, services_status)

            assert overall_status == "error"

    def test_overall_status_error_when_too_many_critical_errors(self):
        """Test that overall status is 'error' when there are too many critical errors."""
        services_status = {"database": "ok", "slack": "ok", "todoist": "ok", "claude": "ok"}

        with patch("apps.server.health.get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_get_dal.return_value = mock_dal

            checker = HealthChecker()
            overall_status = checker._determine_overall_status(
                "ok", 15, services_status
            )  # > 10 critical errors

            assert overall_status == "error"

    def test_overall_status_degraded_when_moderate_critical_errors(self):
        """Test that overall status is 'degraded' when there are moderate critical errors."""
        services_status = {"database": "ok", "slack": "ok", "todoist": "ok", "claude": "ok"}

        with patch("apps.server.health.get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_get_dal.return_value = mock_dal

            checker = HealthChecker()
            overall_status = checker._determine_overall_status(
                "ok", 5, services_status
            )  # 3-10 critical errors

            assert overall_status == "degraded"
