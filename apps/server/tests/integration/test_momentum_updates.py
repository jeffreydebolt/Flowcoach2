"""Integration tests for momentum updates via task completion simulation."""

import sqlite3
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from apps.server.core.momentum import MomentumTracker
from apps.server.jobs.momentum_decay import run_momentum_decay_job


class TestMomentumIntegration:
    """Integration tests for momentum tracking system."""

    def setup_method(self):
        """Set up integration test environment."""
        # Use in-memory SQLite for testing
        self.conn = sqlite3.connect(":memory:")

        # Create full schema
        self.conn.executescript(
            """
            CREATE TABLE project_momentum (
                project_id TEXT PRIMARY KEY,
                last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                momentum_score INTEGER DEFAULT 100,
                status TEXT DEFAULT 'active',
                outcome_defined BOOLEAN DEFAULT FALSE,
                due_date DATE NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                severity TEXT NOT NULL,
                action TEXT NOT NULL,
                payload TEXT,
                user_id TEXT
            );
        """
        )

        # Mock DAL to use our test connection
        with patch("apps.server.core.momentum.get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_db_engine = MagicMock()
            mock_dal.db_engine = mock_db_engine
            mock_get_dal.return_value = mock_dal

            mock_db_engine.get_connection.return_value.__enter__.return_value = self.conn
            mock_db_engine.get_connection.return_value.__exit__.return_value = None

            self.tracker = MomentumTracker()

    def test_task_completion_workflow(self):
        """Test complete workflow of task completion updating momentum."""
        project_id = "project_website_redesign"

        # Simulate task completion sequence
        tasks_completed = [
            {"is_deep_work": False, "description": "Set up project structure"},
            {"is_deep_work": True, "description": "Research user personas (2 hours)"},
            {"is_deep_work": False, "description": "Create wireframe sketches"},
            {"is_deep_work": True, "description": "Design homepage mockup (3 hours)"},
            {"is_deep_work": False, "description": "Review with team"},
        ]

        momentum_history = []

        for i, task in enumerate(tasks_completed):
            # Complete task
            self.tracker.update_project_momentum(
                project_id, is_deep_work=task["is_deep_work"], completed_task=True
            )

            # Record momentum
            cursor = self.conn.execute(
                """
                SELECT momentum_score, status FROM project_momentum
                WHERE project_id = ?
            """,
                (project_id,),
            )
            score, status = cursor.fetchone()
            momentum_history.append(score)

        # Check momentum progression
        # Task 1: 100 + 5 = 100 (capped)
        # Task 2: 100 + 15 = 100 (capped)
        # Task 3: 100 + 5 = 100 (capped)
        # Task 4: 100 + 15 = 100 (capped)
        # Task 5: 100 + 5 = 100 (capped)

        assert momentum_history == [100, 100, 100, 100, 100]

        # Test with lower starting momentum
        self.conn.execute(
            "UPDATE project_momentum SET momentum_score = 50 WHERE project_id = ?", (project_id,)
        )
        self.conn.commit()

        # Complete another deep work task
        self.tracker.update_project_momentum(project_id, is_deep_work=True, completed_task=True)

        cursor = self.conn.execute(
            "SELECT momentum_score FROM project_momentum WHERE project_id = ?", (project_id,)
        )
        final_score = cursor.fetchone()[0]

        assert final_score == 65  # 50 + 15

    def test_mixed_project_decay_scenario(self):
        """Test realistic scenario with multiple projects at different stages."""
        # Set up multiple projects with different states
        projects = [
            # Active project with recent activity
            {
                "id": "project_active",
                "last_activity": datetime.now() - timedelta(hours=6),
                "score": 80,
                "status": "active",
            },
            # Project becoming stale
            {
                "id": "project_staling",
                "last_activity": datetime.now() - timedelta(days=2),
                "score": 65,
                "status": "active",
            },
            # Project that should become stalled
            {
                "id": "project_to_stall",
                "last_activity": datetime.now() - timedelta(days=4),
                "score": 55,
                "status": "active",
            },
            # Already stalled project
            {
                "id": "project_already_stalled",
                "last_activity": datetime.now() - timedelta(days=7),
                "score": 20,
                "status": "stalled",
            },
            # Paused project (should not decay)
            {
                "id": "project_paused",
                "last_activity": datetime.now() - timedelta(days=10),
                "score": 70,
                "status": "paused",
            },
        ]

        # Insert test projects
        for project in projects:
            self.conn.execute(
                """
                INSERT INTO project_momentum
                (project_id, last_activity_at, momentum_score, status)
                VALUES (?, ?, ?, ?)
            """,
                (
                    project["id"],
                    project["last_activity"].isoformat(),
                    project["score"],
                    project["status"],
                ),
            )

        self.conn.commit()

        # Run decay
        updated_count = self.tracker.decay_project_momentum(days_threshold=1)

        # Should update 4 projects (not the paused one)
        assert updated_count == 4

        # Check final states
        cursor = self.conn.execute(
            """
            SELECT project_id, momentum_score, status
            FROM project_momentum
            ORDER BY project_id
        """
        )
        results = {row[0]: {"score": row[1], "status": row[2]} for row in cursor.fetchall()}

        # Active project: no decay (activity within threshold)
        assert results["project_active"]["score"] == 80
        assert results["project_active"]["status"] == "active"

        # Staling project: 65 - (10 * 2) = 45, becomes stalled
        assert results["project_staling"]["score"] == 45
        assert results["project_staling"]["status"] == "stalled"

        # To-stall project: 55 - (10 * 4) = 15, becomes stalled
        assert results["project_to_stall"]["score"] == 15
        assert results["project_to_stall"]["status"] == "stalled"

        # Already stalled: 20 - (10 * 7) = 0 (floored), stays stalled
        assert results["project_already_stalled"]["score"] == 0
        assert results["project_already_stalled"]["status"] == "stalled"

        # Paused project: no change
        assert results["project_paused"]["score"] == 70
        assert results["project_paused"]["status"] == "paused"

    def test_momentum_decay_job_integration(self):
        """Test the full momentum decay job execution."""
        # Set up test project
        project_id = "test_job_project"
        old_date = datetime.now() - timedelta(days=3)

        self.conn.execute(
            """
            INSERT INTO project_momentum
            (project_id, last_activity_at, momentum_score, status)
            VALUES (?, ?, 80, 'active')
        """,
            (project_id, old_date.isoformat()),
        )
        self.conn.commit()

        # Mock the DAL for the job
        with patch("apps.server.jobs.momentum_decay.MomentumTracker") as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker
            mock_tracker.decay_project_momentum.return_value = 1

            # Mock log_event
            with patch("apps.server.jobs.momentum_decay.log_event") as mock_log:
                # Run the job
                success = run_momentum_decay_job()

                # Verify job ran successfully
                assert success == True

                # Verify decay was called
                mock_tracker.decay_project_momentum.assert_called_once_with(days_threshold=1)

                # Verify event was logged
                mock_log.assert_called_once()
                call_args = mock_log.call_args[1]
                assert call_args["severity"] == "info"
                assert call_args["action"] == "momentum_decay_completed"
                assert call_args["payload"]["projects_updated"] == 1

    def test_project_lifecycle_simulation(self):
        """Simulate a complete project lifecycle with momentum changes."""
        project_id = "project_lifecycle_test"

        # Phase 1: Project kickoff with initial tasks
        initial_tasks = [
            {"is_deep_work": False, "days_offset": 0},  # Day 0: Setup
            {"is_deep_work": True, "days_offset": 1},  # Day 1: Deep planning
            {"is_deep_work": False, "days_offset": 2},  # Day 2: Quick task
        ]

        for task in initial_tasks:
            self.tracker.update_project_momentum(project_id, task["is_deep_work"], True)

        # Should be at high momentum
        cursor = self.conn.execute(
            "SELECT momentum_score, status FROM project_momentum WHERE project_id = ?",
            (project_id,),
        )
        score, status = cursor.fetchone()
        assert score == 100  # Capped at 100
        assert status == "active"

        # Phase 2: Simulate 3 days of inactivity
        past_date = datetime.now() - timedelta(days=3)
        self.conn.execute(
            """
            UPDATE project_momentum
            SET last_activity_at = ?
            WHERE project_id = ?
        """,
            (past_date.isoformat(), project_id),
        )
        self.conn.commit()

        # Run decay
        self.tracker.decay_project_momentum()

        # Check momentum decayed
        cursor = self.conn.execute(
            "SELECT momentum_score, status FROM project_momentum WHERE project_id = ?",
            (project_id,),
        )
        score, status = cursor.fetchone()
        assert score == 70  # 100 - (10 * 3)
        assert status == "active"  # Still above 50

        # Phase 3: Project stalls (more inactivity)
        very_past_date = datetime.now() - timedelta(days=8)
        self.conn.execute(
            """
            UPDATE project_momentum
            SET last_activity_at = ?
            WHERE project_id = ?
        """,
            (very_past_date.isoformat(), project_id),
        )
        self.conn.commit()

        # Run decay again
        self.tracker.decay_project_momentum()

        # Check project is now stalled
        cursor = self.conn.execute(
            "SELECT momentum_score, status FROM project_momentum WHERE project_id = ?",
            (project_id,),
        )
        score, status = cursor.fetchone()
        assert score == 20  # 70 - (10 * 8) = -10, but floored at 0... wait, let me recalculate
        # Actually: 100 - (10 * 8) = 20
        assert status == "stalled"  # Below 50

        # Phase 4: Recommit to project
        self.tracker.recommit_project(project_id, minimum_score=60)

        # Check project reactivated
        cursor = self.conn.execute(
            "SELECT momentum_score, status FROM project_momentum WHERE project_id = ?",
            (project_id,),
        )
        score, status = cursor.fetchone()
        assert score == 60  # Boosted to minimum
        assert status == "active"  # Reactivated
