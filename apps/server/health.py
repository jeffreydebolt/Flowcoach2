"""Health check endpoint for FlowCoach monitoring."""

# Bootstrap environment variables in local mode
from .core.env_bootstrap import bootstrap_env
bootstrap_env()

import os
import time
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass, asdict

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    # Fallback to simple HTTP server if FastAPI not available
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    FASTAPI_AVAILABLE = False

from .db.dal import get_dal
from .core.errors import log_event
from .core.feature_flags import get_feature_manager

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health check status information."""
    status: str  # "ok" or "degraded" or "error"
    uptime_seconds: int
    last_error_time: Optional[str]  # ISO timestamp
    error_count_24h: int
    critical_error_count_24h: int
    database_status: str
    services_status: Dict[str, str]
    feature_flags: Dict[str, bool]
    environment_status: str
    timestamp: str  # ISO timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class HealthChecker:
    """Health check logic for FlowCoach."""

    def __init__(self):
        self.start_time = time.time()
        self.dal = get_dal()

    def get_health_status(self) -> HealthStatus:
        """Get current health status."""
        try:
            # Calculate uptime
            uptime_seconds = int(time.time() - self.start_time)

            # Check database
            db_status = self._check_database_health()

            # Check for recent errors
            error_info = self._get_recent_errors()

            # Check external services
            services_status = self._check_services_status()

            # Get feature flag status
            feature_flags = self._get_feature_flags()

            # Check environment status
            env_status = self._check_environment_status()

            # Determine overall status
            overall_status = self._determine_overall_status(
                db_status,
                error_info['critical_count'],
                services_status
            )

            return HealthStatus(
                status=overall_status,
                uptime_seconds=uptime_seconds,
                last_error_time=error_info['last_error_time'],
                error_count_24h=error_info['total_count'],
                critical_error_count_24h=error_info['critical_count'],
                database_status=db_status,
                services_status=services_status,
                feature_flags=feature_flags,
                environment_status=env_status,
                timestamp=datetime.utcnow().isoformat() + 'Z'
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                status="error",
                uptime_seconds=int(time.time() - self.start_time),
                last_error_time=datetime.utcnow().isoformat() + 'Z',
                error_count_24h=1,
                critical_error_count_24h=1,
                database_status="error",
                services_status={"health_check": "error"},
                feature_flags={},
                environment_status="error",
                timestamp=datetime.utcnow().isoformat() + 'Z'
            )

    def _check_database_health(self) -> str:
        """Check if database is accessible and responsive."""
        try:
            with self.dal.db_engine.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                cursor.fetchone()
            return "ok"
        except sqlite3.Error as e:
            logger.error(f"Database health check failed: {e}")
            return "error"
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            return "error"

    def _get_recent_errors(self) -> Dict[str, Any]:
        """Get information about recent errors from the events table."""
        try:
            # Get errors from last 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            with self.dal.db_engine.get_connection() as conn:
                # Get error counts
                cursor = conn.execute("""
                    SELECT severity, COUNT(*) as count
                    FROM events
                    WHERE timestamp > ? AND severity IN ('error', 'critical')
                    GROUP BY severity
                """, (cutoff_time,))

                error_counts = dict(cursor.fetchall())
                total_count = sum(error_counts.values())
                critical_count = error_counts.get('critical', 0) + error_counts.get('error', 0)

                # Get most recent error time
                cursor = conn.execute("""
                    SELECT timestamp
                    FROM events
                    WHERE severity IN ('error', 'critical')
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)

                last_error_row = cursor.fetchone()
                last_error_time = last_error_row[0] if last_error_row else None

                return {
                    'total_count': total_count,
                    'critical_count': critical_count,
                    'last_error_time': last_error_time
                }

        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return {
                'total_count': 1,
                'critical_count': 1,
                'last_error_time': datetime.utcnow().isoformat() + 'Z'
            }

    def _check_services_status(self) -> Dict[str, str]:
        """Check status of external services (token presence)."""
        services = {
            'database': self._check_database_health(),
        }

        # Check if API tokens are configured (trim whitespace)
        slack_token = os.getenv('SLACK_BOT_TOKEN', '').strip()
        if slack_token:
            services['slack'] = 'ok'
        else:
            services['slack'] = 'not_configured'

        todoist_token = os.getenv('TODOIST_API_TOKEN', '').strip()
        if todoist_token:
            services['todoist'] = 'ok'
        else:
            services['todoist'] = 'not_configured'

        claude_token = os.getenv('CLAUDE_API_KEY', '').strip()
        if claude_token:
            services['claude'] = 'ok'
        else:
            services['claude'] = 'not_configured'

        return services

    def _get_feature_flags(self) -> Dict[str, bool]:
        """Get current feature flag status."""
        try:
            feature_manager = get_feature_manager()
            return feature_manager.get_all_flags()
        except Exception as e:
            logger.error(f"Failed to get feature flags: {e}")
            return {"error": True}

    def _check_environment_status(self) -> str:
        """Check environment variables and configuration."""
        try:
            # Check for essential environment variables
            required_vars = ['SLACK_BOT_TOKEN', 'TODOIST_API_TOKEN']
            missing_vars = [var for var in required_vars if not os.getenv(var)]

            if missing_vars:
                logger.warning(f"Missing required environment variables: {missing_vars}")
                return "incomplete"

            return "ok"

        except Exception as e:
            logger.error(f"Environment check failed: {e}")
            return "error"

    def _determine_overall_status(
        self,
        db_status: str,
        critical_error_count: int,
        services_status: Dict[str, str]
    ) -> str:
        """Determine overall system status."""
        # Database error always means error status
        if db_status == "error":
            return "error"

        # Too many critical errors means error status
        if critical_error_count > 10:  # More than 10 critical errors in 24h
            return "error"

        # Some critical errors but not too many → "degraded"
        if critical_error_count > 3:  # 3-10 critical errors in 24h
            return "degraded"

        # Check if all required services are ok
        required_services = ['slack', 'todoist', 'claude']
        all_services_ok = all(
            services_status.get(service) == 'ok'
            for service in required_services
        )

        # If DB is ok and all services are ok → overall "ok"
        if db_status == "ok" and all_services_ok:
            return "ok"

        # If DB is ok but any service is not_configured → "degraded"
        if db_status == "ok":
            return "degraded"

        return "ok"


# FastAPI implementation
if FASTAPI_AVAILABLE:
    app = FastAPI(title="FlowCoach Health Check", version="1.0.0")
    health_checker = HealthChecker()

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        health_status = health_checker.get_health_status()

        status_code = 200
        if health_status.status == "error":
            status_code = 503
        elif health_status.status == "degraded":
            status_code = 200  # Still available but with warnings

        return JSONResponse(
            content=health_status.to_dict(),
            status_code=status_code
        )

    @app.get("/")
    async def root():
        """Root endpoint redirect to health."""
        return {"message": "FlowCoach Health Check API", "health_endpoint": "/health"}

# Fallback HTTP server implementation
else:
    class HealthRequestHandler(BaseHTTPRequestHandler):
        """Simple HTTP request handler for health checks."""

        def __init__(self, *args, **kwargs):
            self.health_checker = HealthChecker()
            super().__init__(*args, **kwargs)

        def do_GET(self):
            """Handle GET requests."""
            if self.path == '/health':
                self._handle_health_check()
            elif self.path == '/':
                self._handle_root()
            else:
                self._send_404()

        def _handle_health_check(self):
            """Handle health check request."""
            try:
                health_status = self.health_checker.get_health_status()

                status_code = 200
                if health_status.status == "error":
                    status_code = 503

                self.send_response(status_code)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                response_data = json.dumps(health_status.to_dict(), indent=2)
                self.wfile.write(response_data.encode('utf-8'))

            except Exception as e:
                logger.error(f"Health check handler error: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                error_response = json.dumps({
                    "status": "error",
                    "message": "Health check failed"
                })
                self.wfile.write(error_response.encode('utf-8'))

        def _handle_root(self):
            """Handle root request."""
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            response = json.dumps({
                "message": "FlowCoach Health Check API",
                "health_endpoint": "/health"
            })
            self.wfile.write(response.encode('utf-8'))

        def _send_404(self):
            """Send 404 response."""
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            response = json.dumps({"error": "Not found"})
            self.wfile.write(response.encode('utf-8'))

        def log_message(self, format, *args):
            """Override to use our logger."""
            logger.info(f"{self.address_string()} - {format % args}")


def run_health_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the health check server."""
    if FASTAPI_AVAILABLE:
        logger.info(f"Starting FastAPI health server on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
    else:
        logger.info(f"Starting simple HTTP health server on {host}:{port}")
        server = HTTPServer((host, port), HealthRequestHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down health server")
            server.shutdown()


if __name__ == "__main__":
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get port from command line or environment
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.error("Invalid port number")
            sys.exit(1)

    port = int(os.getenv('HEALTH_CHECK_PORT', port))

    # Log availability of FastAPI
    if FASTAPI_AVAILABLE:
        logger.info("Using FastAPI for health server")
    else:
        logger.info("FastAPI not available, using simple HTTP server")
        logger.info("Install FastAPI with: pip install fastapi uvicorn")

    run_health_server(port=port)
