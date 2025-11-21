"""Unit tests for Slack message building."""

import json
import unittest
from unittest.mock import mock_open, patch

from apps.server.slack.messages import MessageBuilder


class TestMessageBuilder(unittest.TestCase):
    """Test Slack message construction."""

    def setUp(self):
        """Set up test message builder."""
        # Mock the file reading
        phrases_content = {
            "morning_brief": {"intros": ["Good morning!"], "outros": ["Have a great day!"]},
            "evening_wrap": {"intros": ["Evening recap"], "outros": ["Good night!"]},
            "weekly_outcomes": {"prompts": ["What are your 3 goals?"]},
        }

        morning_template = {
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": "{intro}"}},
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*1.* {item1}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*2.* {item2}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*3.* {item3}"}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": "{close}"}]},
            ]
        }

        with (
            patch("builtins.open", mock_open(read_data=json.dumps(phrases_content))),
            patch.object(MessageBuilder, "_load_template", return_value=morning_template),
        ):
            self.builder = MessageBuilder()

    def test_morning_brief_payload_structure(self):
        """Test morning brief message has correct structure."""
        tasks = [
            {"id": "1", "content": "Test task 1", "labels": ["t_10min"]},
            {"id": "2", "content": "Test task 2", "labels": []},
        ]

        message = self.builder.build_morning_brief(tasks)

        # Check basic structure
        self.assertIn("blocks", message)
        self.assertIsInstance(message["blocks"], list)
        self.assertTrue(len(message["blocks"]) >= 3)  # At least intro, tasks, outro

        # Check that task content appears
        message_str = json.dumps(message)
        self.assertIn("Test task 1", message_str)
        self.assertIn("Test task 2", message_str)

    def test_morning_brief_time_labels(self):
        """Test that time estimates are displayed correctly."""
        tasks = [
            {"id": "1", "content": "Quick task", "labels": ["t_2min"]},
            {"id": "2", "content": "Medium task", "labels": ["t_10min"]},
            {"id": "3", "content": "Long task", "labels": ["t_30plus"]},
        ]

        message = self.builder.build_morning_brief(tasks)
        message_str = json.dumps(message)

        # Time estimates should be formatted nicely
        self.assertIn("2min", message_str)
        self.assertIn("10min", message_str)
        self.assertIn("30+", message_str)

    def test_morning_brief_due_dates(self):
        """Test that due dates are indicated."""
        tasks = [
            {"id": "1", "content": "Overdue task", "due": {"date": "2023-01-01"}},
            {"id": "2", "content": "Normal task", "labels": []},
        ]

        message = self.builder.build_morning_brief(tasks)
        message_str = json.dumps(message)

        # Due date indicator should appear
        self.assertTrue("\\ud83d\\udd34" in message_str or "🔴" in message_str)

    def test_morning_brief_fewer_than_three_tasks(self):
        """Test handling when fewer than 3 tasks provided."""
        tasks = [
            {"id": "1", "content": "Only task", "labels": []},
        ]

        message = self.builder.build_morning_brief(tasks)
        message_str = json.dumps(message)

        # Should pad with placeholder
        self.assertIn("No more tasks for now", message_str)

    def test_evening_wrap_structure(self):
        """Test evening wrap message structure."""
        surfaced_tasks = [
            {"task_id": "1", "task_content": "Task 1", "status": "surfaced"},
            {"task_id": "2", "task_content": "Task 2", "status": "surfaced"},
        ]
        completed_ids = ["1"]

        message = self.builder.build_evening_wrap(surfaced_tasks, completed_ids)

        self.assertIn("blocks", message)
        message_str = json.dumps(message)

        # Should show completed and open tasks
        self.assertTrue("\\u2705" in message_str or "✅" in message_str)  # Completed marker
        self.assertTrue("\\ud83d\\udd01" in message_str or "🔁" in message_str)  # Open marker

        # Task content should appear
        self.assertIn("Task 1", message_str)
        self.assertIn("Task 2", message_str)

    def test_weekly_outcomes_prompt(self):
        """Test weekly outcomes prompt message."""
        message = self.builder.build_weekly_outcomes_prompt()

        self.assertIn("blocks", message)
        message_str = json.dumps(message)

        # Should contain prompt
        self.assertIn("What are your 3 goals?", message_str)
        self.assertIn("bullet points", message_str.lower())

    def test_fallback_messages(self):
        """Test fallback message generation."""
        # Test different error types
        error_types = ["todoist", "no_tasks", "general"]

        for error_type in error_types:
            with self.subTest(error_type=error_type):
                message = self.builder.build_fallback_message(error_type)

                self.assertIn("blocks", message)
                message_str = json.dumps(message)

                # Should contain appropriate error message
                if error_type == "todoist":
                    self.assertIn("Todoist", message_str)
                elif error_type == "no_tasks":
                    self.assertIn("No tasks", message_str)
                else:
                    self.assertIn("Something went wrong", message_str)


if __name__ == "__main__":
    unittest.main()
