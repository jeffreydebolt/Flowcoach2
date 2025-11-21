"""
Workflow persistence service for multi-step workflows.

Provides simple persistence for workflow states, allowing users to resume
interrupted workflows and maintain context across sessions.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowPersistenceService:
    """
    Service for persisting workflow state across sessions.

    Features:
    - Save/load workflow state per user
    - Automatic expiration of old workflows
    - Simple JSON serialization
    - SQLite backend for reliability
    """

    def __init__(self, db_path: str = "flowcoach.db", expiry_hours: int = 24):
        """
        Initialize workflow persistence service.

        Args:
            db_path: Path to SQLite database
            expiry_hours: Hours before workflow state expires
        """
        self.db_path = db_path
        self.expiry_hours = expiry_hours

        # Initialize database
        self._init_db()

        logger.info(f"WorkflowPersistenceService initialized with db: {db_path}")

    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_states (
                    user_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    PRIMARY KEY (user_id, workflow_id)
                )
            """
            )

            # Create index for efficient lookups
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workflow_states_user 
                ON workflow_states(user_id)
            """
            )

            conn.commit()

    def save_workflow_state(
        self, user_id: str, workflow_id: str, agent_id: str, state_data: dict[str, Any]
    ) -> bool:
        """
        Save workflow state for a user.

        Args:
            user_id: User identifier
            workflow_id: Workflow identifier (e.g., "project_breakdown_123")
            agent_id: Agent handling the workflow
            state_data: State data to persist

        Returns:
            True if saved successfully
        """
        try:
            expires_at = datetime.now() + timedelta(hours=self.expiry_hours)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO workflow_states 
                    (user_id, workflow_id, agent_id, state_data, updated_at, expires_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """,
                    (user_id, workflow_id, agent_id, json.dumps(state_data), expires_at),
                )

                conn.commit()

            logger.info(f"Saved workflow state for user {user_id}, workflow {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving workflow state: {e}")
            return False

    def load_workflow_state(self, user_id: str, workflow_id: str) -> dict[str, Any] | None:
        """
        Load workflow state for a user.

        Args:
            user_id: User identifier
            workflow_id: Workflow identifier

        Returns:
            State data if found and not expired, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT agent_id, state_data, expires_at
                    FROM workflow_states
                    WHERE user_id = ? AND workflow_id = ?
                    AND expires_at > CURRENT_TIMESTAMP
                """,
                    (user_id, workflow_id),
                )

                row = cursor.fetchone()

                if row:
                    return {
                        "agent_id": row["agent_id"],
                        "state_data": json.loads(row["state_data"]),
                        "expires_at": row["expires_at"],
                    }

            return None

        except Exception as e:
            logger.error(f"Error loading workflow state: {e}")
            return None

    def get_active_workflows(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get all active workflows for a user.

        Args:
            user_id: User identifier

        Returns:
            List of active workflows
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT workflow_id, agent_id, updated_at, expires_at
                    FROM workflow_states
                    WHERE user_id = ?
                    AND expires_at > CURRENT_TIMESTAMP
                    ORDER BY updated_at DESC
                """,
                    (user_id,),
                )

                workflows = []
                for row in cursor:
                    workflows.append(
                        {
                            "workflow_id": row["workflow_id"],
                            "agent_id": row["agent_id"],
                            "updated_at": row["updated_at"],
                            "expires_at": row["expires_at"],
                        }
                    )

                return workflows

        except Exception as e:
            logger.error(f"Error getting active workflows: {e}")
            return []

    def delete_workflow_state(self, user_id: str, workflow_id: str) -> bool:
        """
        Delete a workflow state.

        Args:
            user_id: User identifier
            workflow_id: Workflow identifier

        Returns:
            True if deleted successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM workflow_states
                    WHERE user_id = ? AND workflow_id = ?
                """,
                    (user_id, workflow_id),
                )

                conn.commit()

            logger.info(f"Deleted workflow state for user {user_id}, workflow {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting workflow state: {e}")
            return False

    def cleanup_expired_workflows(self) -> int:
        """
        Clean up expired workflow states.

        Returns:
            Number of workflows cleaned up
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM workflow_states
                    WHERE expires_at <= CURRENT_TIMESTAMP
                """
                )

                deleted_count = cursor.rowcount
                conn.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired workflows")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up expired workflows: {e}")
            return 0

    def extend_workflow_expiry(
        self, user_id: str, workflow_id: str, additional_hours: int = None
    ) -> bool:
        """
        Extend the expiry time of a workflow.

        Args:
            user_id: User identifier
            workflow_id: Workflow identifier
            additional_hours: Hours to add (defaults to self.expiry_hours)

        Returns:
            True if extended successfully
        """
        try:
            hours = additional_hours or self.expiry_hours
            new_expiry = datetime.now() + timedelta(hours=hours)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    UPDATE workflow_states
                    SET expires_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND workflow_id = ?
                    AND expires_at > CURRENT_TIMESTAMP
                """,
                    (new_expiry, user_id, workflow_id),
                )

                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(
                        f"Extended workflow expiry for user {user_id}, workflow {workflow_id}"
                    )
                    return True

            return False

        except Exception as e:
            logger.error(f"Error extending workflow expiry: {e}")
            return False
