"""Data Access Layer for FlowCoach."""

from .models import (
    WeeklyOutcomesModel,
    TaskScoreModel,
    EventLogger,
    MorningBriefModel
)
from .engine import get_db
from typing import Optional
import os


class DAL:
    """Centralized data access layer using database engine abstraction."""

    _instance: Optional['DAL'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            # Use the database engine abstraction instead of direct Database class
            self.db_engine = get_db()
            self.weekly_outcomes = WeeklyOutcomesModel(self.db_engine)
            self.task_scores = TaskScoreModel(self.db_engine)
            self.events = EventLogger(self.db_engine)
            self.morning_brief = MorningBriefModel(self.db_engine)
            self.initialized = True


def get_dal() -> DAL:
    """Get DAL singleton instance."""
    return DAL()
