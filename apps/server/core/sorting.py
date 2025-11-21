"""Task sorting and prioritization logic."""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class TaskSorter:
    """Handles task sorting for Morning Brief."""

    @staticmethod
    def calculate_priority_score(
        task: dict[str, Any], weekly_outcomes: list[str], current_time: datetime
    ) -> float:
        """
        Calculate priority score for a task.

        Priority order:
        1. Weekly outcomes alignment (1000 points)
        2. @rev_driver label (500 points)
        3. Deep work task scores (up to 11 points)
        4. Due/overdue tasks (100-200 points)
        5. Energy fit bonus (+1 point)
        """
        score = 0.0

        # Check weekly outcomes alignment
        task_content = task.get("content", "").lower()
        for outcome in weekly_outcomes:
            if outcome.lower() in task_content:
                score += 1000
                logger.debug(f"Task '{task_content[:30]}...' matches weekly outcome")
                break

        # Check for @rev_driver label
        labels = task.get("labels", [])
        if "rev_driver" in labels:
            score += 500

        # Deep work scores (from labels)
        impact = 0
        urgency = 0
        energy = None

        for label in labels:
            if label.startswith("impact"):
                try:
                    impact = int(label[6:])
                except ValueError:
                    pass
            elif label.startswith("urgency"):
                try:
                    urgency = int(label[7:])
                except ValueError:
                    pass
            elif label.startswith("energy_"):
                energy = label[7:]  # 'am' or 'pm'

        # Add deep work score
        if impact > 0 and urgency > 0:
            base_score = impact + urgency

            # Energy fit bonus
            current_hour = current_time.hour
            is_morning = 6 <= current_hour < 12

            if (is_morning and energy == "am") or (not is_morning and energy == "pm"):
                base_score += 1

            score += base_score

        # Due date scoring
        due = task.get("due")
        if due:
            due_date = datetime.fromisoformat(due["date"].replace("Z", "+00:00"))
            today = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

            if due_date < today:
                # Overdue
                score += 200
            elif due_date == today:
                # Due today
                score += 100

        return score

    @classmethod
    def sort_tasks(
        cls,
        tasks: list[dict[str, Any]],
        weekly_outcomes: list[str] | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Sort tasks by priority and return top N.

        Args:
            tasks: List of task dictionaries
            weekly_outcomes: Current week's outcomes
            limit: Maximum tasks to return

        Returns:
            Top N prioritized tasks
        """
        if not tasks:
            return []

        weekly_outcomes = weekly_outcomes or []
        current_time = datetime.now()

        # Calculate scores
        scored_tasks = []
        for task in tasks:
            score = cls.calculate_priority_score(task, weekly_outcomes, current_time)
            scored_tasks.append((score, task))

        # Sort by score (descending)
        scored_tasks.sort(key=lambda x: x[0], reverse=True)

        # Return top N tasks
        return [task for _, task in scored_tasks[:limit]]
