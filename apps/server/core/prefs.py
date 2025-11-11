"""User preferences storage using Todoist project note."""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import time

from ..integrations.todoist_client import TodoistClient

logger = logging.getLogger(__name__)


@dataclass
class EnergyWindow:
    """Time window optimized for specific work types."""

    name: str  # 'deep', 'calls', 'admin'
    start_time: str  # "09:00"
    end_time: str  # "11:00"
    max_session_minutes: int = 90


@dataclass
class WorkPreferences:
    """User work preferences from interview."""

    # Basic info
    timezone: str = "America/New_York"
    work_days: str = "mon,tue,wed,thu,fri"  # comma-separated

    # Daily rhythm
    quiet_hours_start: str = "18:00"
    quiet_hours_end: str = "09:00"
    morning_window_start: str = "07:00"
    morning_window_end: str = "10:00"
    wrap_window_start: str = "16:00"
    wrap_window_end: str = "18:00"

    # Energy windows
    energy_windows: list[EnergyWindow] = None

    # Task preferences
    max_session_minutes: int = 90
    no_new_task_threshold_minutes: int = 15

    # Check-in settings
    checkin_time_today: Optional[str] = None  # Set daily, format: "14:30"

    def __post_init__(self):
        """Set default energy windows if not provided."""
        if self.energy_windows is None:
            self.energy_windows = [
                EnergyWindow("deep", "09:00", "11:00", 90),
                EnergyWindow("calls", "14:00", "16:00", 60),
                EnergyWindow("admin", "16:00", "17:00", 30),
            ]


class PreferencesStore:
    """Manages user preferences storage in Todoist."""

    def __init__(self, todoist_client: Optional[TodoistClient] = None):
        """Initialize preferences store."""
        self.todoist = todoist_client or TodoistClient()

    def save_prefs(self, user_id: str, prefs: WorkPreferences) -> bool:
        """Save user preferences to Todoist project note."""
        try:
            # Convert to dict and add metadata
            prefs_data = {
                "user_id": user_id,
                "version": "1.0",
                "preferences": self._prefs_to_dict(prefs),
            }

            # Save as JSON in Todoist note
            json_content = json.dumps(prefs_data, indent=2)
            self.todoist.save_project_note(json_content)

            logger.info(
                f"Successfully saved preferences for user {user_id} to Todoist project note"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save preferences for user {user_id}: {e}")
            return False

    def load_prefs(self, user_id: str) -> Optional[WorkPreferences]:
        """Load user preferences from Todoist project note."""
        try:
            content = self.todoist.load_project_note()
            if not content:
                logger.debug(f"No preferences found for user {user_id} in Todoist project note")
                return None

            # Parse JSON
            try:
                prefs_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in preferences: {e}")
                return None

            # Validate structure
            if not isinstance(prefs_data, dict) or "preferences" not in prefs_data:
                logger.error("Invalid preferences structure")
                return None

            # Check if this is for the right user
            stored_user_id = prefs_data.get("user_id")
            if stored_user_id != user_id:
                logger.warning(f"Preferences user ID mismatch: {stored_user_id} != {user_id}")
                return None

            # Convert back to WorkPreferences
            prefs_dict = prefs_data["preferences"]
            prefs = self._dict_to_prefs(prefs_dict)

            logger.info(f"Loaded preferences for user {user_id}")
            return prefs

        except Exception as e:
            logger.error(f"Failed to load preferences for user {user_id}: {e}")
            return None

    def get_prefs_or_defaults(self, user_id: str) -> WorkPreferences:
        """Get user preferences, returning defaults if none exist."""
        prefs = self.load_prefs(user_id)
        if prefs is None:
            logger.debug(f"Using default preferences for user {user_id}")
            return WorkPreferences()
        return prefs

    def _prefs_to_dict(self, prefs: WorkPreferences) -> Dict[str, Any]:
        """Convert WorkPreferences to dictionary."""
        result = asdict(prefs)

        # Convert energy windows to simple dicts
        if result.get("energy_windows"):
            result["energy_windows"] = [asdict(window) for window in prefs.energy_windows]

        return result

    def _dict_to_prefs(self, prefs_dict: Dict[str, Any]) -> WorkPreferences:
        """Convert dictionary to WorkPreferences."""
        # Extract energy windows first
        energy_windows_data = prefs_dict.pop("energy_windows", [])
        energy_windows = [EnergyWindow(**window_data) for window_data in energy_windows_data]

        # Create WorkPreferences with energy windows
        prefs = WorkPreferences(**prefs_dict)
        prefs.energy_windows = energy_windows

        return prefs


# Convenience functions
def save_user_prefs(user_id: str, prefs: WorkPreferences) -> bool:
    """Save user preferences (convenience function)."""
    store = PreferencesStore()
    return store.save_prefs(user_id, prefs)


def load_user_prefs(user_id: str) -> Optional[WorkPreferences]:
    """Load user preferences (convenience function)."""
    store = PreferencesStore()
    return store.load_prefs(user_id)


def get_user_prefs_or_defaults(user_id: str) -> WorkPreferences:
    """Get user preferences with defaults fallback (convenience function)."""
    store = PreferencesStore()
    return store.get_prefs_or_defaults(user_id)
