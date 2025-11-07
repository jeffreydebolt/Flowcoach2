"""Integration tests for morning brief flow."""

import unittest
import os
from unittest.mock import Mock, patch, MagicMock
from apps.server.jobs.morning_brief import MorningBriefJob
from apps.server.core.sorting import TaskSorter
from apps.server.slack.messages import MessageBuilder


class TestMorningBriefFlow(unittest.TestCase):
    """Test the complete morning brief flow."""

    def setUp(self):
        """Set up test environment."""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'SLACK_BOT_TOKEN': 'xoxb-test-token',
            'TODOIST_API_TOKEN': 'test-todoist-token',
            'FC_ACTIVE_USERS': 'U123456',
        })
        self.env_patcher.start()

        # Create mocks
        self.mock_slack_client = Mock()
        self.mock_todoist_client = Mock()
        self.mock_dal = Mock()

    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()

    @patch('apps.server.jobs.morning_brief.WebClient')
    @patch('apps.server.jobs.morning_brief.TodoistClient')
    @patch('apps.server.jobs.morning_brief.get_dal')
    @patch('apps.server.jobs.morning_brief.MessageBuilder')
    def test_successful_morning_brief_send(self, mock_builder_class, mock_dal_func,
                                         mock_todoist_class, mock_slack_class):
        """Test successful morning brief sending."""
        # Setup mocks
        mock_slack_class.return_value = self.mock_slack_client
        mock_todoist_class.return_value = self.mock_todoist_client
        mock_dal_func.return_value = self.mock_dal

        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder

        # Mock data
        mock_tasks = [
            {"id": "1", "content": "High priority task", "labels": ["rev_driver"]},
            {"id": "2", "content": "Medium task", "labels": ["t_10min"]},
            {"id": "3", "content": "Low task", "labels": []},
        ]

        mock_outcomes = ["Ship feature", "Improve metrics", "Team growth"]

        # Configure mocks
        self.mock_dal.weekly_outcomes.get_current_outcomes.return_value = mock_outcomes
        self.mock_todoist_client.get_tasks.return_value = mock_tasks

        mock_message = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Morning!"}}]}
        mock_builder.build_morning_brief.return_value = mock_message

        # Slack API response
        self.mock_slack_client.chat_postMessage.return_value = {"ts": "1234567890.123"}
        self.mock_slack_client.users_info.return_value = {"user": {"tz": "America/Denver"}}

        # Create and run job
        job = MorningBriefJob()
        result = job.send_morning_brief("U123456")

        # Verify success
        self.assertTrue(result)

        # Verify calls
        self.mock_dal.weekly_outcomes.get_current_outcomes.assert_called_once_with("U123456")
        self.mock_todoist_client.get_tasks.assert_called_once()
        mock_builder.build_morning_brief.assert_called_once()
        self.mock_dal.morning_brief.record_surfaced_tasks.assert_called_once()
        self.mock_slack_client.chat_postMessage.assert_called_once()

    @patch('apps.server.jobs.morning_brief.WebClient')
    @patch('apps.server.jobs.morning_brief.TodoistClient')
    @patch('apps.server.jobs.morning_brief.get_dal')
    @patch('apps.server.jobs.morning_brief.MessageBuilder')
    def test_morning_brief_no_tasks(self, mock_builder_class, mock_dal_func,
                                   mock_todoist_class, mock_slack_class):
        """Test morning brief when no tasks available."""
        # Setup mocks
        mock_slack_class.return_value = self.mock_slack_client
        mock_todoist_class.return_value = self.mock_todoist_client
        mock_dal_func.return_value = self.mock_dal

        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder

        # Mock no tasks
        self.mock_dal.weekly_outcomes.get_current_outcomes.return_value = []
        self.mock_todoist_client.get_tasks.return_value = None

        # Mock fallback message
        mock_fallback = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "No tasks!"}}]}
        mock_builder.build_fallback_message.return_value = mock_fallback

        self.mock_slack_client.users_info.return_value = {"user": {"tz": "America/Denver"}}

        # Create and run job
        job = MorningBriefJob()
        result = job.send_morning_brief("U123456")

        # Should still succeed with fallback
        self.assertTrue(result)

        # Verify fallback was used
        mock_builder.build_fallback_message.assert_called_once_with("no_tasks")
        self.mock_slack_client.chat_postMessage.assert_called_once()

    @patch('apps.server.jobs.morning_brief.WebClient')
    @patch('apps.server.jobs.morning_brief.TodoistClient')
    @patch('apps.server.jobs.morning_brief.get_dal')
    def test_morning_brief_slack_error(self, mock_dal_func, mock_todoist_class, mock_slack_class):
        """Test morning brief when Slack API fails."""
        # Setup mocks
        mock_slack_class.return_value = self.mock_slack_client
        mock_todoist_class.return_value = self.mock_todoist_client
        mock_dal_func.return_value = self.mock_dal

        # Configure Slack to fail
        from slack_sdk.errors import SlackApiError
        self.mock_slack_client.chat_postMessage.side_effect = SlackApiError("API Error", {"error": "channel_not_found"})
        self.mock_slack_client.users_info.return_value = {"user": {"tz": "America/Denver"}}

        # Mock other services working
        self.mock_dal.weekly_outcomes.get_current_outcomes.return_value = []
        self.mock_todoist_client.get_tasks.return_value = [
            {"id": "1", "content": "Test task", "labels": []}
        ]

        # Create and run job
        job = MorningBriefJob()
        result = job.send_morning_brief("U123456")

        # Should fail gracefully
        self.assertFalse(result)

    def test_task_sorting_with_outcomes(self):
        """Test that task sorting works correctly with weekly outcomes."""
        tasks = [
            {"id": "1", "content": "Random task", "labels": []},
            {"id": "2", "content": "Ship feature X to production", "labels": []},
            {"id": "3", "content": "Review pull request", "labels": []},
        ]

        outcomes = ["Ship feature X", "Improve performance", "Team development"]

        sorted_tasks = TaskSorter.sort_tasks(tasks, outcomes, limit=3)

        # Task 2 should be first due to weekly outcome match
        self.assertEqual(sorted_tasks[0]["id"], "2")

    @patch('apps.server.slack.messages.Path')
    @patch('builtins.open')
    def test_message_building_integration(self, mock_open_func, mock_path):
        """Test message building with realistic data."""
        # Mock file system
        mock_path.return_value.parent.parent = Mock()

        # Mock file contents
        phrases = """{
            "morning_brief": {
                "intros": ["Good morning!"],
                "outros": ["Have a great day!"]
            }
        }"""

        template = """{
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": "{intro}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*1.* {item1}"}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": "{close}"}]}
            ]
        }"""

        # Configure mock to return different content for different files
        def mock_open_side_effect(*args, **kwargs):
            if 'phrases.json' in str(args[0]):
                return MagicMock(read=Mock(return_value=phrases))
            else:
                return MagicMock(read=Mock(return_value=template))

        mock_open_func.side_effect = mock_open_side_effect

        # Create builder and test
        builder = MessageBuilder()

        tasks = [
            {"id": "1", "content": "Important meeting", "labels": ["t_30plus"], "due": {"date": "2023-01-01"}},
        ]

        message = builder.build_morning_brief(tasks)

        # Verify structure
        self.assertIn("blocks", message)
        self.assertTrue(len(message["blocks"]) > 0)


if __name__ == '__main__':
    unittest.main()
