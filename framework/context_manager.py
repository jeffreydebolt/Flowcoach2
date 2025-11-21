"""
Context Manager for maintaining conversation state across agents.

Inspired by BMAD's context preservation patterns, this handles:
- User conversation state
- Agent handoff context
- Workflow context
- Persistent user preferences
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages conversation context across agents and sessions.

    Features:
    - Per-user conversation state
    - Agent handoff context preservation
    - Workflow state tracking
    - Context expiration and cleanup
    - Persistent storage (optional)
    """

    def __init__(self, storage_backend=None):
        """
        Initialize context manager.

        Args:
            storage_backend: Optional persistent storage backend
        """
        self.storage = storage_backend
        self.contexts: dict[str, dict[str, Any]] = {}
        self.context_timestamps: dict[str, datetime] = {}
        self.default_expiry = timedelta(hours=24)  # Context expires after 24h

        logger.info("ContextManager initialized")

    def get_context(self, user_id: str, create_if_missing: bool = True) -> dict[str, Any]:
        """
        Get conversation context for a user.

        Args:
            user_id: User identifier
            create_if_missing: Create new context if none exists

        Returns:
            User's conversation context
        """
        # Clean up expired contexts first
        self._cleanup_expired_contexts()

        if user_id not in self.contexts:
            if create_if_missing:
                self.contexts[user_id] = self._create_default_context()
                self.context_timestamps[user_id] = datetime.now()
                logger.debug(f"Created new context for user {user_id}")
            else:
                return {}

        # Update timestamp
        self.context_timestamps[user_id] = datetime.now()
        return self.contexts.get(user_id, {})

    def update_context(self, user_id: str, updates: dict[str, Any]):
        """
        Update user's conversation context.

        Args:
            user_id: User identifier
            updates: Context updates to apply
        """
        context = self.get_context(user_id)
        context.update(updates)
        self.context_timestamps[user_id] = datetime.now()

        # Persist to storage if available
        if self.storage:
            self._persist_context(user_id, context)

        logger.debug(f"Updated context for user {user_id}: {list(updates.keys())}")

    def set_context_value(self, user_id: str, key: str, value: Any):
        """
        Set a specific context value.

        Args:
            user_id: User identifier
            key: Context key
            value: Value to set
        """
        context = self.get_context(user_id)
        context[key] = value
        self.context_timestamps[user_id] = datetime.now()

        if self.storage:
            self._persist_context(user_id, context)

    def get_context_value(self, user_id: str, key: str, default=None):
        """
        Get a specific context value.

        Args:
            user_id: User identifier
            key: Context key
            default: Default value if key not found

        Returns:
            Context value or default
        """
        context = self.get_context(user_id, create_if_missing=False)
        return context.get(key, default)

    def clear_context(self, user_id: str):
        """
        Clear all context for a user.

        Args:
            user_id: User identifier
        """
        if user_id in self.contexts:
            del self.contexts[user_id]
        if user_id in self.context_timestamps:
            del self.context_timestamps[user_id]

        if self.storage:
            self._delete_persisted_context(user_id)

        logger.info(f"Cleared context for user {user_id}")

    def prepare_handoff_context(
        self,
        user_id: str,
        source_agent: str,
        target_agent: str,
        handoff_data: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """
        Prepare context for agent handoff.

        Args:
            user_id: User identifier
            source_agent: Agent handing off
            target_agent: Agent receiving handoff
            handoff_data: Additional data for handoff

        Returns:
            Prepared handoff context
        """
        context = self.get_context(user_id)

        # Store handoff information
        handoff_context = {
            "source_agent": source_agent,
            "target_agent": target_agent,
            "handoff_time": datetime.now().isoformat(),
            "handoff_data": handoff_data or {},
        }

        context["last_handoff"] = handoff_context
        context["current_agent"] = target_agent
        context["agent_history"] = context.get("agent_history", []) + [source_agent]

        self.update_context(user_id, context)

        logger.info(f"Prepared handoff context: {source_agent} → {target_agent} for user {user_id}")
        return context

    def get_workflow_context(self, user_id: str, workflow_id: str) -> dict[str, Any]:
        """
        Get workflow-specific context.

        Args:
            user_id: User identifier
            workflow_id: Workflow identifier

        Returns:
            Workflow context
        """
        context = self.get_context(user_id)
        workflows = context.get("workflows", {})
        return workflows.get(workflow_id, {})

    def update_workflow_context(
        self, user_id: str, workflow_id: str, workflow_data: dict[str, Any]
    ):
        """
        Update workflow-specific context.

        Args:
            user_id: User identifier
            workflow_id: Workflow identifier
            workflow_data: Workflow context updates
        """
        context = self.get_context(user_id)
        workflows = context.get("workflows", {})

        if workflow_id not in workflows:
            workflows[workflow_id] = {"created_at": datetime.now().isoformat(), "status": "active"}

        workflows[workflow_id].update(workflow_data)
        workflows[workflow_id]["updated_at"] = datetime.now().isoformat()

        context["workflows"] = workflows
        self.update_context(user_id, context)

        logger.debug(f"Updated workflow {workflow_id} context for user {user_id}")

    def complete_workflow(self, user_id: str, workflow_id: str, result: dict[str, Any] = None):
        """
        Mark a workflow as complete.

        Args:
            user_id: User identifier
            workflow_id: Workflow identifier
            result: Optional workflow result data
        """
        workflow_data = {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result": result or {},
        }

        self.update_workflow_context(user_id, workflow_id, workflow_data)
        logger.info(f"Completed workflow {workflow_id} for user {user_id}")

    def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """
        Get user preferences.

        Args:
            user_id: User identifier

        Returns:
            User preferences
        """
        context = self.get_context(user_id)
        return context.get("preferences", {})

    def update_user_preferences(self, user_id: str, preferences: dict[str, Any]):
        """
        Update user preferences.

        Args:
            user_id: User identifier
            preferences: Preference updates
        """
        context = self.get_context(user_id)
        user_prefs = context.get("preferences", {})
        user_prefs.update(preferences)
        context["preferences"] = user_prefs

        self.update_context(user_id, context)
        logger.debug(f"Updated preferences for user {user_id}")

    def _create_default_context(self) -> dict[str, Any]:
        """Create default context structure."""
        return {
            "created_at": datetime.now().isoformat(),
            "current_agent": None,
            "agent_history": [],
            "workflows": {},
            "preferences": {},
            "conversation_data": {},
            "last_handoff": None,
        }

    def _cleanup_expired_contexts(self):
        """Remove expired contexts."""
        now = datetime.now()
        expired_users = []

        for user_id, timestamp in self.context_timestamps.items():
            if now - timestamp > self.default_expiry:
                expired_users.append(user_id)

        for user_id in expired_users:
            self.clear_context(user_id)
            logger.debug(f"Cleaned up expired context for user {user_id}")

    def _persist_context(self, user_id: str, context: dict[str, Any]):
        """Persist context to storage backend."""
        if not self.storage:
            return

        try:
            self.storage.save_context(user_id, context)
        except Exception as e:
            logger.error(f"Failed to persist context for user {user_id}: {e}")

    def _delete_persisted_context(self, user_id: str):
        """Delete persisted context."""
        if not self.storage:
            return

        try:
            self.storage.delete_context(user_id)
        except Exception as e:
            logger.error(f"Failed to delete persisted context for user {user_id}: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """
        Get context manager statistics.

        Returns:
            Statistics about active contexts
        """
        active_contexts = len(self.contexts)
        total_workflows = sum(len(ctx.get("workflows", {})) for ctx in self.contexts.values())

        return {
            "active_contexts": active_contexts,
            "total_workflows": total_workflows,
            "storage_backend": self.storage.__class__.__name__ if self.storage else None,
        }
