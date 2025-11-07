"""Project momentum tracking and scoring logic."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..db.dal import get_dal
from ..core.db_retry import with_db_retry
from ..core.feature_flags import FeatureFlag, is_feature_enabled

logger = logging.getLogger(__name__)


def require_db_writes(func):
    """Decorator to check if database writes are enabled."""
    def wrapper(self, *args, **kwargs):
        if not is_feature_enabled(FeatureFlag.DATABASE_WRITES):
            logger.warning(f"Database writes disabled - skipping {func.__name__}")
            return False
        return func(self, *args, **kwargs)
    return wrapper


@dataclass
class ProjectMomentum:
    """Project momentum data class."""
    project_id: str
    last_activity_at: datetime
    momentum_score: int
    status: str
    outcome_defined: bool
    due_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MomentumTracker:
    """Tracks project momentum based on task activity."""

    def __init__(self):
        self.dal = get_dal()

    @with_db_retry
    @require_db_writes
    def update_project_momentum(
        self,
        project_id: str,
        is_deep_work: bool = False,
        completed_task: bool = True
    ) -> None:
        """
        Update momentum for a project based on task activity.

        Args:
            project_id: Todoist project ID
            is_deep_work: True if task has @t_30plus label
            completed_task: True for completion, False for just adding task
        """
        # Calculate momentum boost
        if completed_task and is_deep_work:
            boost = 15
        elif completed_task:
            boost = 5
        else:
            boost = 2  # Small boost for adding tasks

        now = datetime.now()

        with self.dal.db_engine.get_connection() as conn:
            # Get existing momentum or create new
            cursor = conn.execute("""
                SELECT momentum_score, status
                FROM project_momentum
                WHERE project_id = ?
            """, (project_id,))

            row = cursor.fetchone()

            if row:
                current_score = row[0]
                current_status = row[1]

                # Calculate new score (cap at 100)
                new_score = min(100, current_score + boost)

                # Update status if needed
                new_status = 'active' if new_score >= 50 else current_status

                # Update existing record
                conn.execute("""
                    UPDATE project_momentum
                    SET last_activity_at = ?,
                        momentum_score = ?,
                        status = ?,
                        updated_at = ?
                    WHERE project_id = ?
                """, (now, new_score, new_status, now, project_id))
            else:
                # Create new record
                initial_score = min(100, 100 + boost)  # Start at 100 + boost
                conn.execute("""
                    INSERT INTO project_momentum
                    (project_id, last_activity_at, momentum_score, status, outcome_defined, created_at, updated_at)
                    VALUES (?, ?, ?, 'active', FALSE, ?, ?)
                """, (project_id, now, initial_score, now, now))

            conn.commit()

        logger.info(f"Updated momentum for project {project_id}: +{boost} points")

    @with_db_retry
    def decay_project_momentum(self, days_threshold: int = 1) -> int:
        """
        Decay momentum for idle projects and mark stalled ones.

        Args:
            days_threshold: Days of inactivity before decay starts

        Returns:
            Number of projects updated
        """
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        updated_count = 0

        with self.dal.db_engine.get_connection() as conn:
            # Get projects that need decay
            cursor = conn.execute("""
                SELECT project_id, last_activity_at, momentum_score, status
                FROM project_momentum
                WHERE datetime(last_activity_at) < datetime(?) AND status != 'paused'
            """, (cutoff_date.isoformat(),))

            projects_to_update = cursor.fetchall()

            for project_id, last_activity, current_score, current_status in projects_to_update:
                # Calculate days idle
                if isinstance(last_activity, str):
                    # Handle both ISO format with and without timezone
                    if 'T' in last_activity:
                        last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    else:
                        last_activity = datetime.fromisoformat(last_activity)

                days_idle = (datetime.now() - last_activity).days
                # Ensure at least 1 day for projects that meet threshold
                if days_idle == 0 and last_activity < cutoff_date:
                    days_idle = 1

                # Decay: -10 points per day idle (never below 0)
                decay_amount = 10 * days_idle
                new_score = max(0, current_score - decay_amount)

                # Determine new status
                if new_score < 50 and current_status == 'active':
                    new_status = 'stalled'
                else:
                    new_status = current_status

                # Update project
                conn.execute("""
                    UPDATE project_momentum
                    SET momentum_score = ?,
                        status = ?,
                        updated_at = ?
                    WHERE project_id = ?
                """, (new_score, new_status, datetime.now(), project_id))

                updated_count += 1

                logger.info(
                    f"Decayed project {project_id}: -{decay_amount} points "
                    f"(score: {current_score} → {new_score}, status: {current_status} → {new_status})"
                )

            conn.commit()

        return updated_count

    @with_db_retry
    def get_project_momentum(self, project_id: str) -> Optional[ProjectMomentum]:
        """Get momentum data for a specific project."""
        with self.dal.db_engine.get_connection() as conn:
            cursor = conn.execute("""
                SELECT project_id, last_activity_at, momentum_score, status,
                       outcome_defined, due_date, created_at, updated_at
                FROM project_momentum
                WHERE project_id = ?
            """, (project_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return ProjectMomentum(
                project_id=row[0],
                last_activity_at=datetime.fromisoformat(row[1]) if row[1] else datetime.now(),
                momentum_score=row[2],
                status=row[3],
                outcome_defined=bool(row[4]),
                due_date=datetime.fromisoformat(row[5]) if row[5] else None,
                created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                updated_at=datetime.fromisoformat(row[7]) if row[7] else None
            )

    @with_db_retry
    @require_db_writes
    def recommit_project(self, project_id: str, minimum_score: int = 60) -> bool:
        """
        Recommit to a project by boosting momentum score.

        Args:
            project_id: Project to recommit to
            minimum_score: Minimum score to set (default 60)

        Returns:
            True if project was updated
        """
        now = datetime.now()

        with self.dal.db_engine.get_connection() as conn:
            cursor = conn.execute("""
                SELECT momentum_score, status FROM project_momentum
                WHERE project_id = ?
            """, (project_id,))

            row = cursor.fetchone()
            if not row:
                return False

            current_score = row[0]
            new_score = max(current_score, minimum_score)
            new_status = 'active' if new_score >= 50 else row[1]

            conn.execute("""
                UPDATE project_momentum
                SET momentum_score = ?,
                    status = ?,
                    last_activity_at = ?,
                    updated_at = ?
                WHERE project_id = ?
            """, (new_score, new_status, now, now, project_id))

            conn.commit()

            logger.info(f"Recommitted to project {project_id}: score boosted to {new_score}")
            return True

    @with_db_retry
    @require_db_writes
    def pause_project(self, project_id: str) -> bool:
        """Pause a project (stops momentum decay)."""
        with self.dal.db_engine.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE project_momentum
                SET status = 'paused', updated_at = ?
                WHERE project_id = ?
            """, (datetime.now(), project_id))

            conn.commit()
            return cursor.rowcount > 0

    @with_db_retry
    @require_db_writes
    def rewrite_project(
        self,
        project_id: str,
        outcome: str,
        due_date: Optional[datetime] = None
    ) -> bool:
        """
        Rewrite a project with new outcome and due date.

        Args:
            project_id: Project to rewrite
            outcome: New outcome description
            due_date: Optional due date

        Returns:
            True if project was updated
        """
        now = datetime.now()

        with self.dal.db_engine.get_connection() as conn:
            # Upsert project momentum record
            conn.execute("""
                INSERT OR REPLACE INTO project_momentum
                (project_id, last_activity_at, momentum_score, status,
                 outcome_defined, due_date, created_at, updated_at)
                VALUES (?, ?,
                    COALESCE((SELECT momentum_score FROM project_momentum WHERE project_id = ?), 100),
                    'active', TRUE, ?,
                    COALESCE((SELECT created_at FROM project_momentum WHERE project_id = ?), ?),
                    ?)
            """, (project_id, now, project_id, due_date, project_id, now, now))

            conn.commit()

            logger.info(f"Rewrote project {project_id}: outcome defined, due_date={due_date}")
            return True

    @with_db_retry
    @require_db_writes
    def update_project_outcome(
        self,
        project_id: str,
        outcome_defined: bool = True,
        due_date: Optional[datetime] = None
    ) -> bool:
        """
        Update project outcome and due date without changing momentum score.

        Args:
            project_id: Project to update
            outcome_defined: Whether outcome is now defined
            due_date: Optional due date

        Returns:
            True if project was updated
        """
        now = datetime.now()

        with self.dal.db_engine.get_connection() as conn:
            # Upsert project momentum record, preserving momentum score
            conn.execute("""
                INSERT OR REPLACE INTO project_momentum
                (project_id, last_activity_at, momentum_score, status,
                 outcome_defined, due_date, created_at, updated_at)
                VALUES (?, ?,
                    COALESCE((SELECT momentum_score FROM project_momentum WHERE project_id = ?), 100),
                    COALESCE((SELECT status FROM project_momentum WHERE project_id = ?), 'active'),
                    ?, ?,
                    COALESCE((SELECT created_at FROM project_momentum WHERE project_id = ?), ?),
                    ?)
            """, (project_id, now, project_id, project_id, outcome_defined, due_date, project_id, now, now))

            conn.commit()

            logger.info(f"Updated project {project_id} outcome: outcome_defined={outcome_defined}, due_date={due_date}")
            return True
