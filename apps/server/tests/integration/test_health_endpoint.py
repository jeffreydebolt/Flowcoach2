"""Integration tests for health check endpoint."""

import unittest
import json
import threading
import time
import requests
from unittest.mock import patch, Mock
import tempfile
import os

from apps.server.health import run_health_server, HealthChecker


class TestHealthEndpoint(unittest.TestCase):
    """Test health check HTTP endpoint."""

    def setUp(self):
        """Set up test environment."""
        self.test_port = 18080  # Use a different port for testing
        self.base_url = f"http://localhost:{self.test_port}"
        self.server_thread = None

        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()

    def tearDown(self):
        """Clean up test environment."""
        # Stop server if running
        if self.server_thread and self.server_thread.is_alive():
            # Server will be stopped by the test
            pass

        # Clean up temp database
        try:
            os.unlink(self.temp_db.name)
        except FileNotFoundError:
            pass

    def start_health_server(self):
        """Start health server in a separate thread."""
        def run_server():
            try:
                run_health_server(host="localhost", port=self.test_port)
            except Exception as e:
                print(f"Server error: {e}")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait for server to start
        max_attempts = 30
        for _ in range(max_attempts):
            try:
                response = requests.get(f"{self.base_url}/", timeout=1)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.1)
        else:
            self.fail("Health server failed to start within timeout")

    @patch.dict('os.environ', {
        'TODOIST_API_TOKEN': 'test-token',
        'CLAUDE_API_KEY': 'test-key',
        'FC_DB_PATH': tempfile.NamedTemporaryFile().name
    })
    def test_health_endpoint_ok_status(self):
        """Test health endpoint returns OK status when everything is healthy."""
        try:
            self.start_health_server()

            response = requests.get(f"{self.base_url}/health", timeout=5)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['content-type'], 'application/json')

            data = response.json()

            # Check required fields
            required_fields = [
                'status', 'uptime_seconds', 'error_count_24h',
                'critical_error_count_24h', 'database_status',
                'services_status', 'timestamp'
            ]

            for field in required_fields:
                self.assertIn(field, data, f"Missing field: {field}")

            # Check that status is reasonable
            self.assertIn(data['status'], ['ok', 'degraded', 'error'])
            self.assertIsInstance(data['uptime_seconds'], int)
            self.assertGreaterEqual(data['uptime_seconds'], 0)

        except requests.exceptions.RequestException as e:
            self.fail(f"Failed to connect to health server: {e}")

    @patch('apps.server.health.get_dal')
    def test_health_endpoint_error_status(self, mock_get_dal):
        """Test health endpoint returns 503 when there are critical errors."""
        # Mock DAL to simulate database errors
        mock_dal = Mock()
        mock_dal.db.get_connection.side_effect = Exception("Database unavailable")
        mock_get_dal.return_value = mock_dal

        try:
            self.start_health_server()

            response = requests.get(f"{self.base_url}/health", timeout=5)

            # Should return 503 for error status
            self.assertEqual(response.status_code, 503)

            data = response.json()
            self.assertEqual(data['status'], 'error')
            self.assertEqual(data['database_status'], 'error')

        except requests.exceptions.RequestException as e:
            self.fail(f"Failed to connect to health server: {e}")

    def test_root_endpoint(self):
        """Test root endpoint returns basic information."""
        try:
            self.start_health_server()

            response = requests.get(f"{self.base_url}/", timeout=5)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['content-type'], 'application/json')

            data = response.json()
            self.assertIn('message', data)
            self.assertIn('health_endpoint', data)
            self.assertEqual(data['health_endpoint'], '/health')

        except requests.exceptions.RequestException as e:
            self.fail(f"Failed to connect to health server: {e}")

    def test_404_for_unknown_endpoints(self):
        """Test that unknown endpoints return 404."""
        try:
            self.start_health_server()

            response = requests.get(f"{self.base_url}/unknown", timeout=5)

            self.assertEqual(response.status_code, 404)

        except requests.exceptions.RequestException as e:
            self.fail(f"Failed to connect to health server: {e}")

    @patch.dict('os.environ', {}, clear=True)
    def test_health_endpoint_missing_config(self):
        """Test health endpoint when configuration is missing."""
        try:
            self.start_health_server()

            response = requests.get(f"{self.base_url}/health", timeout=5)

            # Should still return 200 but with degraded status
            self.assertEqual(response.status_code, 200)

            data = response.json()
            # Should be degraded due to missing Todoist token
            self.assertIn(data['status'], ['degraded', 'error'])
            self.assertEqual(data['services_status']['todoist'], 'not_configured')

        except requests.exceptions.RequestException as e:
            self.fail(f"Failed to connect to health server: {e}")

    def test_health_endpoint_json_format(self):
        """Test that health endpoint returns properly formatted JSON."""
        try:
            self.start_health_server()

            response = requests.get(f"{self.base_url}/health", timeout=5)

            # Should be valid JSON
            data = response.json()

            # Test that we can serialize it back
            json_str = json.dumps(data)
            reparsed = json.loads(json_str)

            self.assertEqual(data, reparsed)

        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            self.fail(f"JSON parsing failed: {e}")


class TestHealthCheckerIntegration(unittest.TestCase):
    """Integration tests for HealthChecker with real database."""

    def setUp(self):
        """Set up test environment with real database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()

        # Patch the database path
        self.db_path_patcher = patch.dict('os.environ', {
            'FC_DB_PATH': self.temp_db.name
        })
        self.db_path_patcher.start()

    def tearDown(self):
        """Clean up test environment."""
        self.db_path_patcher.stop()
        try:
            os.unlink(self.temp_db.name)
        except FileNotFoundError:
            pass

    def test_health_checker_with_real_database(self):
        """Test HealthChecker with actual database operations."""
        # Create health checker - this will initialize the database
        checker = HealthChecker()

        # Get health status
        status = checker.get_health_status()

        # Should have valid status
        self.assertIn(status.status, ['ok', 'degraded', 'error'])
        self.assertEqual(status.database_status, 'ok')
        self.assertIsInstance(status.uptime_seconds, int)
        self.assertGreaterEqual(status.uptime_seconds, 0)

        # Should have services status
        self.assertIn('database', status.services_status)
        self.assertEqual(status.services_status['database'], 'ok')

    def test_health_checker_error_tracking(self):
        """Test that health checker properly tracks errors in database."""
        checker = HealthChecker()

        # Add some error events to the database
        dal = checker.dal
        dal.events.log_event('error', 'test_error', {'message': 'Test error 1'})
        dal.events.log_event('critical', 'test_critical', {'message': 'Critical error'})

        # Get health status
        status = checker.get_health_status()

        # Should have recorded the errors
        self.assertGreaterEqual(status.error_count_24h, 2)
        self.assertGreaterEqual(status.critical_error_count_24h, 2)
        self.assertIsNotNone(status.last_error_time)


if __name__ == '__main__':
    # Skip integration tests if requests is not available
    try:
        import requests
        unittest.main()
    except ImportError:
        print("Skipping integration tests - requests library not available")
        print("Install with: pip install requests")
