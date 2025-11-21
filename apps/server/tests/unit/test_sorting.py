"""Unit tests for task sorting logic."""

import unittest
from datetime import datetime, timedelta

from apps.server.core.sorting import TaskSorter


class TestTaskSorter(unittest.TestCase):
    """Test task sorting functionality."""

    def setUp(self):
        """Set up test data."""
        self.current_time = datetime.now()
        self.today = self.current_time.strftime("%Y-%m-%d")
        self.tomorrow = (self.current_time + timedelta(days=1)).strftime("%Y-%m-%d")
        self.yesterday = (self.current_time - timedelta(days=1)).strftime("%Y-%m-%d")

    def test_weekly_outcomes_priority(self):
        """Test that weekly outcomes get highest priority."""
        tasks = [
            {"id": "1", "content": "Regular task", "labels": []},
            {"id": "2", "content": "Build new feature dashboard", "labels": []},
            {"id": "3", "content": "Urgent task", "due": {"date": self.today}},
        ]

        outcomes = ["Build new feature dashboard", "Ship v2", "Improve performance"]

        sorted_tasks = TaskSorter.sort_tasks(tasks, outcomes, limit=3)

        # Weekly outcome task should be first
        self.assertEqual(sorted_tasks[0]["id"], "2")

    def test_rev_driver_priority(self):
        """Test that @rev_driver tasks get high priority."""
        tasks = [
            {"id": "1", "content": "Regular task", "labels": []},
            {"id": "2", "content": "Revenue task", "labels": ["rev_driver"]},
            {"id": "3", "content": "Another task", "labels": ["someday"]},
        ]

        sorted_tasks = TaskSorter.sort_tasks(tasks, [], limit=3)

        # Revenue driver should be first
        self.assertEqual(sorted_tasks[0]["id"], "2")

    def test_deep_work_scoring(self):
        """Test deep work task scoring."""
        tasks = [
            {
                "id": "1",
                "content": "Low priority deep work",
                "labels": ["t_30plus", "impact2", "urgency2", "energy_pm"],
            },
            {
                "id": "2",
                "content": "High priority deep work",
                "labels": ["t_30plus", "impact5", "urgency4", "energy_am"],
            },
            {"id": "3", "content": "Regular task", "labels": []},
        ]

        # Test morning sorting (AM task gets bonus)
        morning_time = datetime.now().replace(hour=9)
        scores = []
        for task in tasks:
            score = TaskSorter.calculate_priority_score(task, [], morning_time)
            scores.append((task["id"], score))

        scores.sort(key=lambda x: x[1], reverse=True)

        # High priority AM task should score highest in morning
        self.assertEqual(scores[0][0], "2")

    def test_due_date_priority(self):
        """Test due date prioritization."""
        tasks = [
            {"id": "1", "content": "Future task", "due": {"date": self.tomorrow}, "labels": []},
            {"id": "2", "content": "Overdue task", "due": {"date": self.yesterday}, "labels": []},
            {"id": "3", "content": "Today task", "due": {"date": self.today}, "labels": []},
            {"id": "4", "content": "No due date", "labels": []},
        ]

        sorted_tasks = TaskSorter.sort_tasks(tasks, [], limit=4)

        # Overdue should be first, then today
        task_ids = [t["id"] for t in sorted_tasks]
        self.assertEqual(task_ids[0], "2")  # Overdue
        self.assertEqual(task_ids[1], "3")  # Due today

    def test_limit_enforcement(self):
        """Test that limit is enforced."""
        tasks = [{"id": str(i), "content": f"Task {i}", "labels": []} for i in range(10)]

        sorted_tasks = TaskSorter.sort_tasks(tasks, [], limit=3)
        self.assertEqual(len(sorted_tasks), 3)

    def test_empty_task_list(self):
        """Test handling of empty task list."""
        sorted_tasks = TaskSorter.sort_tasks([], [], limit=3)
        self.assertEqual(sorted_tasks, [])


if __name__ == "__main__":
    unittest.main()
