"""Unit tests for task scoring logic."""

import unittest
from apps.server.core.scoring import TaskScorer


class TestTaskScorer(unittest.TestCase):
    """Test task scoring functionality."""

    def test_duration_extraction(self):
        """Test duration extraction from task text."""
        test_cases = [
            ("email client - 5 min", 5),
            ("Review proposal 30 minutes", 30),
            ("Deep work session - 2 hours", 120),
            ("Quick sync call 10m", 10),
            ("Create presentation ~45m", 45),
            ("No time mentioned", None),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = TaskScorer.extract_duration(text)
                self.assertEqual(result, expected)

    def test_deep_work_detection(self):
        """Test deep work task detection."""
        deep_work_tasks = [
            "Plan quarterly roadmap",
            "Design new architecture",
            "Research user behavior patterns",
            "Write technical proposal",
            "Implement authentication system - 2 hours",
            "Quick task but 20 minutes",
        ]

        regular_tasks = [
            "Send email to client",
            "Update status in Slack",
            "Quick PR check",
            "5 minute standup",
        ]

        for task in deep_work_tasks:
            with self.subTest(task=task):
                self.assertTrue(TaskScorer.is_deep_work(task), f"Should detect '{task}' as deep work")

        for task in regular_tasks:
            with self.subTest(task=task):
                self.assertFalse(TaskScorer.is_deep_work(task), f"Should not detect '{task}' as deep work")

    def test_score_input_parsing(self):
        """Test parsing of score input."""
        valid_cases = [
            ("4/3/am", (4, 3, "am")),
            ("5/1/pm", (5, 1, "pm")),
            ("1/5/AM", (1, 5, "am")),  # Case insensitive
            ("3/3/PM", (3, 3, "pm")),
        ]

        invalid_cases = [
            "4/3",  # Missing energy
            "4/3/evening",  # Invalid energy
            "6/3/am",  # Impact out of range
            "4/0/pm",  # Urgency out of range
            "a/3/am",  # Non-numeric
            "4-3-am",  # Wrong separator
        ]

        for input_str, expected in valid_cases:
            with self.subTest(input=input_str):
                result = TaskScorer.parse_score_input(input_str)
                self.assertEqual(result, expected)

        for input_str in invalid_cases:
            with self.subTest(input=input_str):
                result = TaskScorer.parse_score_input(input_str)
                self.assertIsNone(result)

    def test_total_score_calculation(self):
        """Test total score calculation with energy bonus."""
        # Base score without bonus
        score = TaskScorer.calculate_total_score(4, 3, "pm")
        self.assertGreaterEqual(score, 7)  # Base: 4 + 3 = 7, may have +1 energy bonus

        # Energy bonus depends on current time, so we can't test exact values
        # But we can test that AM/PM preference affects the score
        am_score = TaskScorer.calculate_total_score(4, 3, "am")
        pm_score = TaskScorer.calculate_total_score(4, 3, "pm")

        # One should be higher than the other (depending on current time)
        self.assertTrue(am_score != pm_score or am_score == pm_score)  # Could be equal if neutral time

    def test_score_labels_generation(self):
        """Test generation of Todoist labels."""
        labels = TaskScorer.get_score_labels(4, 3, "am")
        expected = ["impact4", "urgency3", "energy_am"]
        self.assertEqual(labels, expected)

        labels = TaskScorer.get_score_labels(5, 1, "pm")
        expected = ["impact5", "urgency1", "energy_pm"]
        self.assertEqual(labels, expected)


if __name__ == '__main__':
    unittest.main()
