"""Database models for FlowCoach."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import sqlite3
import json
import logging

from ..core.db_retry import with_db_retry, DatabaseRetryMixin
from .engine import DatabaseEngine

logger = logging.getLogger(__name__)


class Database(DatabaseRetryMixin):
    """Simple SQLite database wrapper."""

    def __init__(self, db_path: str = "./flowcoach.db"):
        self.db_path = db_path
        self._init_db()

    @with_db_retry
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weekly_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    week_start DATE NOT NULL,
                    outcomes TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, week_start)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    impact INTEGER NOT NULL,
                    urgency INTEGER NOT NULL,
                    energy TEXT NOT NULL,
                    total_score INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    severity TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload TEXT,
                    user_id TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS morning_brief_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    task_content TEXT NOT NULL,
                    surfaced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'surfaced'
                )
            """)

            conn.commit()

    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)


class WeeklyOutcomesModel:
    """Handle weekly outcomes storage."""

    def __init__(self, db_engine: DatabaseEngine):
        self.db_engine = db_engine

    @with_db_retry
    def set_outcomes(self, user_id: str, outcomes: List[str], week_start: datetime) -> None:
        """Store or update weekly outcomes."""
        with self.db_engine.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO weekly_outcomes
                (user_id, week_start, outcomes, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                week_start.date(),
                json.dumps(outcomes),
                datetime.now()
            ))
            conn.commit()

    @with_db_retry
    def get_current_outcomes(self, user_id: str) -> Optional[List[str]]:
        """Get current week's outcomes."""
        # Calculate start of current week (Monday)
        today = datetime.now()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)

        with self.db_engine.get_connection() as conn:
            cursor = conn.execute("""
                SELECT outcomes FROM weekly_outcomes
                WHERE user_id = ? AND week_start = ?
            """, (user_id, week_start.date()))

            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None


class TaskScoreModel:
    """Handle task score storage."""

    def __init__(self, db_engine: DatabaseEngine):
        self.db_engine = db_engine

    @with_db_retry
    def save_score(
        self,
        task_id: str,
        impact: int,
        urgency: int,
        energy: str,
        total_score: int
    ) -> None:
        """Save task scores."""
        with self.db_engine.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO task_scores
                (task_id, impact, urgency, energy, total_score)
                VALUES (?, ?, ?, ?, ?)
            """, (task_id, impact, urgency, energy, total_score))
            conn.commit()

    @with_db_retry
    def get_score(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task scores."""
        with self.db_engine.get_connection() as conn:
            cursor = conn.execute("""
                SELECT impact, urgency, energy, total_score
                FROM task_scores WHERE task_id = ?
            """, (task_id,))

            row = cursor.fetchone()
            if row:
                return {
                    'impact': row[0],
                    'urgency': row[1],
                    'energy': row[2],
                    'total_score': row[3]
                }
            return None


class EventLogger:
    """Handle event logging to database."""

    def __init__(self, db_engine: DatabaseEngine):
        self.db_engine = db_engine

    @with_db_retry
    def log_event(
        self,
        severity: str,
        action: str,
        payload: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> None:
        """Log an event to database."""
        with self.db_engine.get_connection() as conn:
            conn.execute("""
                INSERT INTO events (severity, action, payload, user_id)
                VALUES (?, ?, ?, ?)
            """, (severity, action, json.dumps(payload), user_id))
            conn.commit()


class MorningBriefModel:
    """Track tasks surfaced in morning briefs."""

    def __init__(self, db_engine: DatabaseEngine):
        self.db_engine = db_engine

    @with_db_retry
    def record_surfaced_tasks(self, user_id: str, tasks: List[Dict[str, Any]]) -> None:
        """Record which tasks were shown in morning brief."""
        with self.db_engine.get_connection() as conn:
            for task in tasks:
                conn.execute("""
                    INSERT INTO morning_brief_tasks
                    (user_id, task_id, task_content)
                    VALUES (?, ?, ?)
                """, (user_id, task['id'], task['content']))
            conn.commit()

    @with_db_retry
    def get_today_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get tasks surfaced today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        with self.db_engine.get_connection() as conn:
            cursor = conn.execute("""
                SELECT task_id, task_content, status
                FROM morning_brief_tasks
                WHERE user_id = ? AND surfaced_at >= ?
            """, (user_id, today_start))

            return [
                {'task_id': row[0], 'task_content': row[1], 'status': row[2]}
                for row in cursor.fetchall()
            ]

    @with_db_retry
    def update_task_status(self, task_id: str, status: str) -> None:
        """Update status of a surfaced task."""
        with self.db_engine.get_connection() as conn:
            conn.execute("""
                UPDATE morning_brief_tasks
                SET status = ?
                WHERE task_id = ?
            """, (status, task_id))
            conn.commit()
