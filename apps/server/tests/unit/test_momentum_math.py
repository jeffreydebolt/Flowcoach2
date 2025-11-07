"""Tests for momentum tracking math and logic."""

import pytest
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from apps.server.core.momentum import MomentumTracker, ProjectMomentum


class TestMomentumMath:
    """Test momentum bump and decay calculations."""

    def setup_method(self):
        """Set up test environment."""
        # Use in-memory SQLite for testing
        with patch('apps.server.core.momentum.get_dal') as mock_get_dal:
            mock_dal = MagicMock()
            mock_db_engine = MagicMock()
            mock_dal.db_engine = mock_db_engine
            mock_get_dal.return_value = mock_dal

            # Mock connection with actual SQLite
            import sqlite3
            self.conn = sqlite3.connect(':memory:')
            mock_db_engine.get_connection.return_value.__enter__.return_value = self.conn
            mock_db_engine.get_connection.return_value.__exit__.return_value = None

            # Create test table
            self.conn.execute("""
                CREATE TABLE project_momentum (
                    project_id TEXT PRIMARY KEY,
                    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    momentum_score INTEGER DEFAULT 100,
                    status TEXT DEFAULT 'active',
                    outcome_defined BOOLEAN DEFAULT FALSE,
                    due_date DATE NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()

            self.tracker = MomentumTracker()

    def test_deep_work_completion_boost(self):
        """Test that deep work completion gives +15 boost."""
        project_id = "test_project_deep"

        # Insert base project
        self.conn.execute("""
            INSERT INTO project_momentum (project_id, momentum_score)
            VALUES (?, 50)
        """, (project_id,))
        self.conn.commit()

        # Update with deep work completion
        self.tracker.update_project_momentum(project_id, is_deep_work=True, completed_task=True)

        # Check result
        cursor = self.conn.execute("SELECT momentum_score FROM project_momentum WHERE project_id = ?", (project_id,))
        result = cursor.fetchone()

        assert result[0] == 65  # 50 + 15

    def test_normal_task_completion_boost(self):
        """Test that normal task completion gives +5 boost."""
        project_id = "test_project_normal"

        # Insert base project
        self.conn.execute("""
            INSERT INTO project_momentum (project_id, momentum_score)
            VALUES (?, 40)
        """, (project_id,))
        self.conn.commit()

        # Update with normal completion
        self.tracker.update_project_momentum(project_id, is_deep_work=False, completed_task=True)

        # Check result
        cursor = self.conn.execute("SELECT momentum_score FROM project_momentum WHERE project_id = ?", (project_id,))
        result = cursor.fetchone()

        assert result[0] == 45  # 40 + 5

    def test_task_addition_boost(self):
        """Test that adding tasks gives +2 boost."""
        project_id = "test_project_add"

        # Insert base project
        self.conn.execute("""
            INSERT INTO project_momentum (project_id, momentum_score)
            VALUES (?, 30)
        """, (project_id,))
        self.conn.commit()

        # Update with task addition
        self.tracker.update_project_momentum(project_id, is_deep_work=False, completed_task=False)

        # Check result
        cursor = self.conn.execute("SELECT momentum_score FROM project_momentum WHERE project_id = ?", (project_id,))
        result = cursor.fetchone()

        assert result[0] == 32  # 30 + 2

    def test_momentum_score_caps_at_100(self):
        """Test that momentum score never exceeds 100."""
        project_id = "test_project_cap"

        # Insert project near cap
        self.conn.execute("""
            INSERT INTO project_momentum (project_id, momentum_score)
            VALUES (?, 95)
        """, (project_id,))
        self.conn.commit()

        # Update with deep work completion (+15)
        self.tracker.update_project_momentum(project_id, is_deep_work=True, completed_task=True)

        # Check result is capped
        cursor = self.conn.execute("SELECT momentum_score FROM project_momentum WHERE project_id = ?", (project_id,))
        result = cursor.fetchone()

        assert result[0] == 100  # Capped at 100, not 110

    def test_new_project_starts_at_100_plus_boost(self):
        """Test that new projects start at 100 + initial boost."""
        project_id = "test_project_new"

        # Update non-existent project with normal completion
        self.tracker.update_project_momentum(project_id, is_deep_work=False, completed_task=True)

        # Check it was created with correct score
        cursor = self.conn.execute("SELECT momentum_score FROM project_momentum WHERE project_id = ?", (project_id,))
        result = cursor.fetchone()

        assert result[0] == 100  # Started at 100 + 5, capped at 100

    def test_decay_calculation(self):
        """Test momentum decay calculation."""
        # Create test projects with different idle periods
        projects = [
            ("project_1day", 1, 80),   # 1 day idle, start 80
            ("project_3days", 3, 90),  # 3 days idle, start 90
            ("project_5days", 5, 60),  # 5 days idle, start 60
        ]

        for project_id, days_idle, initial_score in projects:
            # Add extra hour buffer to ensure dates are clearly in the past
            idle_date = datetime.now() - timedelta(days=days_idle, hours=1)
            self.conn.execute("""
                INSERT INTO project_momentum
                (project_id, last_activity_at, momentum_score, status)
                VALUES (?, ?, ?, 'active')
            """, (project_id, idle_date.isoformat(), initial_score))

        self.conn.commit()

        # Run decay with 1 day threshold
        updated_count = self.tracker.decay_project_momentum(days_threshold=1)

        assert updated_count == 3

        # Check results
        cursor = self.conn.execute("""
            SELECT project_id, momentum_score, status
            FROM project_momentum
            ORDER BY project_id
        """)
        results = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

        # project_1day: 80 - (10 * 1) = 70, still active
        assert results["project_1day"] == (70, "active")

        # project_3days: 90 - (10 * 3) = 60, still active
        assert results["project_3days"] == (60, "active")

        # project_5days: 60 - (10 * 5) = 10, should be stalled
        assert results["project_5days"] == (10, "stalled")

    def test_decay_never_goes_below_zero(self):
        """Test that decay never makes momentum negative."""
        project_id = "test_project_floor"

        # Create project with very old activity
        old_date = datetime.now() - timedelta(days=20)
        self.conn.execute("""
            INSERT INTO project_momentum
            (project_id, last_activity_at, momentum_score, status)
            VALUES (?, ?, 30, 'active')
        """, (project_id, old_date.isoformat()))
        self.conn.commit()

        # Run decay
        self.tracker.decay_project_momentum(days_threshold=1)

        # Check result is floored at 0
        cursor = self.conn.execute("SELECT momentum_score FROM project_momentum WHERE project_id = ?", (project_id,))
        result = cursor.fetchone()

        assert result[0] == 0  # Floored at 0, not negative

    def test_stalled_threshold_at_50(self):
        """Test that projects become stalled below 50 momentum."""
        project_id = "test_project_stall"

        # Create project that will fall below 50 (use 2 days to ensure clear threshold)
        old_date = datetime.now() - timedelta(days=2)
        self.conn.execute("""
            INSERT INTO project_momentum
            (project_id, last_activity_at, momentum_score, status)
            VALUES (?, ?, 55, 'active')
        """, (project_id, old_date.isoformat()))
        self.conn.commit()

        # Run decay with 1 day threshold: 55 - (10 * 2) = 35
        self.tracker.decay_project_momentum(days_threshold=1)

        # Check status changed to stalled
        cursor = self.conn.execute("SELECT momentum_score, status FROM project_momentum WHERE project_id = ?", (project_id,))
        score, status = cursor.fetchone()

        assert score == 35  # 55 - (10 * 2)
        assert status == "stalled"

    def test_paused_projects_skip_decay(self):
        """Test that paused projects don't decay."""
        project_id = "test_project_paused"

        # Create paused project
        old_date = datetime.now() - timedelta(days=5)
        self.conn.execute("""
            INSERT INTO project_momentum
            (project_id, last_activity_at, momentum_score, status)
            VALUES (?, ?, 80, 'paused')
        """, (project_id, old_date.isoformat()))
        self.conn.commit()

        # Run decay
        self.tracker.decay_project_momentum(days_threshold=1)

        # Check paused project unchanged
        cursor = self.conn.execute("SELECT momentum_score, status FROM project_momentum WHERE project_id = ?", (project_id,))
        score, status = cursor.fetchone()

        assert score == 80  # Unchanged
        assert status == "paused"

    def test_recommit_boosts_minimum_score(self):
        """Test that recommit sets minimum score."""
        project_id = "test_project_recommit"

        # Create stalled project
        self.conn.execute("""
            INSERT INTO project_momentum
            (project_id, momentum_score, status)
            VALUES (?, 30, 'stalled')
        """, (project_id,))
        self.conn.commit()

        # Recommit with minimum 60
        success = self.tracker.recommit_project(project_id, minimum_score=60)

        assert success == True

        # Check result
        cursor = self.conn.execute("SELECT momentum_score, status FROM project_momentum WHERE project_id = ?", (project_id,))
        score, status = cursor.fetchone()

        assert score == 60  # Boosted to minimum
        assert status == "active"  # Reactivated
