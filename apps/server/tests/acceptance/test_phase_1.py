"""Acceptance tests for FlowCoach Phase 1 - Morning Brief Modal."""

from datetime import date
from unittest.mock import Mock, patch

from apps.server.core.planning import TaskCandidate, TaskSelector
from apps.server.platform.feature_flags import FlowCoachFlag, clear_all_overrides, set_override
from apps.server.slack.modals.morning_brief import MorningBriefModal


class TestMorningBriefEndToEnd:
    """Test complete morning brief flow from home tab to task planning."""

    def setup_method(self):
        """Reset feature flags before each test."""
        clear_all_overrides()
        set_override(FlowCoachFlag.FC_MORNING_MODAL_V1, True)
        set_override(FlowCoachFlag.FC_HOME_TAB_V1, True)

    @patch("apps.server.core.planning.PlanningService")
    @patch("apps.server.integrations.todoist_client.TodoistClient")
    def test_morning_brief_flow_with_tasks(self, mock_todoist_class, mock_planning_class):
        """Test complete morning brief flow with tasks to plan."""
        # Mock Todoist client
        mock_todoist = Mock()
        mock_todoist_class.return_value = mock_todoist

        # Mock planning service
        mock_planning = Mock()
        mock_planning_class.return_value = mock_planning

        # Set up mock task candidates
        test_tasks = [
            TaskCandidate(
                id="task_123",
                content="Review quarterly report",
                project_name="Work",
                priority=4,
                due_date="2025-11-11",
                labels=["@flow_tomorrow"],
                is_overdue=False,
                is_priority_1=True,
                is_flow_tomorrow=True,
                is_flow_weekly=False,
            ),
            TaskCandidate(
                id="task_456",
                content="Call client about project",
                project_name="Sales",
                priority=1,
                due_date=None,
                labels=[],
                is_overdue=True,
                is_priority_1=False,
                is_flow_tomorrow=False,
                is_flow_weekly=False,
            ),
        ]

        mock_planning.get_morning_brief_tasks.return_value = test_tasks
        mock_planning.mark_task_as_planned.return_value = True
        mock_planning.save_checkin_time.return_value = True

        # Create modal handler
        modal_handler = MorningBriefModal(mock_planning)

        # Mock Slack client
        mock_client = Mock()

        # Test 1: Open morning brief modal
        modal_handler.open_modal("trigger_123", "U123456", mock_client)

        # Verify modal was opened
        mock_client.views_open.assert_called_once()
        call_args = mock_client.views_open.call_args
        modal_view = call_args[1]["view"]

        # Verify modal structure
        assert modal_view["type"] == "modal"
        assert modal_view["callback_id"] == "flowcoach_morning_brief_submit"
        assert modal_view["private_metadata"] == "U123456"

        # Verify tasks are in modal blocks
        blocks = modal_view["blocks"]
        task_contents = [
            block.get("text", {}).get("text", "")
            for block in blocks
            if block.get("type") == "section"
        ]
        assert any("Review quarterly report" in content for content in task_contents)
        assert any("Call client about project" in content for content in task_contents)

        # Test 2: Simulate modal submission
        submission_body = {
            "view": {
                "private_metadata": "U123456",
                "state": {
                    "values": {
                        "task_plan_0": {
                            "priority_0": {"selected_option": {"value": "p1"}},
                            "time_0": {"selected_time": "09:00"},
                        },
                        "task_id_0": {"task_id": {"value": "task_123"}},
                        "task_plan_1": {
                            "priority_1": {"selected_option": {"value": "p2"}},
                            "time_1": {"selected_time": "10:30"},
                        },
                        "task_id_1": {"task_id": {"value": "task_456"}},
                    }
                },
            }
        }

        # Handle submission
        modal_handler.handle_submission(submission_body, mock_client)

        # Verify both tasks were planned
        assert mock_planning.mark_task_as_planned.call_count == 2

        # Verify correct planning calls
        planning_calls = mock_planning.mark_task_as_planned.call_args_list
        assert ("task_123", "p1", "09:00") in [call[0] for call in planning_calls]
        assert ("task_456", "p2", "10:30") in [call[0] for call in planning_calls]

        # Verify checkin time was saved
        mock_planning.save_checkin_time.assert_called_once()
        checkin_call = mock_planning.save_checkin_time.call_args[0]
        assert checkin_call[0] == "U123456"  # user_id
        assert len(checkin_call[1]) == 5  # time format HH:MM

        # Verify completion message was sent
        mock_client.chat_postMessage.assert_called_once()
        message_call = mock_client.chat_postMessage.call_args
        assert "complete" in message_call[1]["text"].lower()
        assert message_call[1]["channel"] == "U123456"

    @patch("apps.server.core.planning.PlanningService")
    @patch("apps.server.integrations.todoist_client.TodoistClient")
    def test_morning_brief_flow_no_tasks(self, mock_todoist_class, mock_planning_class):
        """Test morning brief flow when no tasks need planning."""
        # Mock empty task list
        mock_planning = Mock()
        mock_planning_class.return_value = mock_planning
        mock_planning.get_morning_brief_tasks.return_value = []

        # Create modal handler
        modal_handler = MorningBriefModal(mock_planning)
        mock_client = Mock()

        # Open modal with no tasks
        modal_handler.open_modal("trigger_123", "U123456", mock_client)

        # Verify empty modal was shown
        mock_client.views_open.assert_called_once()
        call_args = mock_client.views_open.call_args
        modal_view = call_args[1]["view"]

        assert modal_view["callback_id"] == "morning_brief_empty"

        # Check for "All Clear" message
        blocks = modal_view["blocks"]
        header_block = next((block for block in blocks if block.get("type") == "header"), None)
        assert header_block is not None
        assert "All Clear" in header_block["text"]["text"]

    @patch("apps.server.core.planning.PlanningService")
    def test_morning_brief_with_skip_tasks(self, mock_planning_class):
        """Test morning brief when some tasks are skipped."""
        # Mock planning service
        mock_planning = Mock()
        mock_planning_class.return_value = mock_planning
        mock_planning.mark_task_as_planned.return_value = True
        mock_planning.save_checkin_time.return_value = True

        # Create modal handler
        modal_handler = MorningBriefModal(mock_planning)
        mock_client = Mock()

        # Simulate submission with mixed planning and skipping
        submission_body = {
            "view": {
                "private_metadata": "U123456",
                "state": {
                    "values": {
                        "task_plan_0": {
                            "priority_0": {"selected_option": {"value": "p1"}},
                            "time_0": {"selected_time": "09:00"},
                        },
                        "task_id_0": {"task_id": {"value": "task_plan"}},
                        "task_plan_1": {
                            "priority_1": {"selected_option": {"value": "skip"}},
                            "time_1": {"selected_time": "10:00"},
                        },
                        "task_id_1": {"task_id": {"value": "task_skip"}},
                    }
                },
            }
        }

        # Handle submission
        modal_handler.handle_submission(submission_body, mock_client)

        # Verify only non-skipped task was planned
        mock_planning.mark_task_as_planned.assert_called_once_with("task_plan", "p1", "09:00")

        # Verify completion message mentions 1 task
        mock_client.chat_postMessage.assert_called_once()
        message_call = mock_client.chat_postMessage.call_args
        assert "1 task" in message_call[1]["text"]


class TestTaskSelectionLogic:
    """Test task selection criteria for morning brief."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_todoist = Mock()
        self.selector = TaskSelector(self.mock_todoist)

    def test_monday_includes_weekly_tasks(self):
        """Test that Monday morning brief includes @flow_weekly tasks."""
        # Mock tasks with weekly label
        self.mock_todoist.get_tasks.return_value = [
            {
                "id": "weekly_123",
                "content": "Weekly team standup preparation",
                "labels": ["@flow_weekly"],
                "priority": 1,
                "project_id": "proj1",
                "due": None,
            },
            {
                "id": "daily_456",
                "content": "Regular daily task",
                "labels": ["@flow_tomorrow"],
                "priority": 1,
                "project_id": "proj1",
                "due": None,
            },
        ]

        self.mock_todoist.get_projects.return_value = [{"id": "proj1", "name": "Work"}]

        # Test Monday selection
        monday_tasks = self.selector.get_morning_brief_tasks("U123", is_monday=True)
        tuesday_tasks = self.selector.get_morning_brief_tasks("U123", is_monday=False)

        # Monday should include both tasks
        assert len(monday_tasks) == 2
        task_contents = [task.content for task in monday_tasks]
        assert "Weekly team standup preparation" in task_contents
        assert "Regular daily task" in task_contents

        # Tuesday should exclude weekly task
        assert len(tuesday_tasks) == 1
        assert tuesday_tasks[0].content == "Regular daily task"

    def test_overdue_priority_sorting(self):
        """Test that overdue tasks have highest priority in selection."""
        today_str = date.today().strftime("%Y-%m-%d")
        yesterday_str = "2025-11-09"  # Known past date

        self.mock_todoist.get_tasks.return_value = [
            {
                "id": "normal_123",
                "content": "Normal priority task",
                "labels": ["@flow_tomorrow"],
                "priority": 1,
                "project_id": "proj1",
                "due": None,
            },
            {
                "id": "high_456",
                "content": "High priority task",
                "labels": [],
                "priority": 4,  # Priority 1 in Todoist
                "project_id": "proj1",
                "due": None,
            },
            {
                "id": "overdue_789",
                "content": "Overdue task",
                "labels": [],
                "priority": 1,
                "project_id": "proj1",
                "due": {"date": yesterday_str},
            },
        ]

        self.mock_todoist.get_projects.return_value = [{"id": "proj1", "name": "Work"}]

        tasks = self.selector.get_morning_brief_tasks("U123", is_monday=False)

        # Verify all qualifying tasks are included and properly sorted
        assert len(tasks) == 3

        # Overdue should be first
        assert tasks[0].content == "Overdue task"
        assert tasks[0].is_overdue is True

        # High priority should be second
        assert tasks[1].content == "High priority task"
        assert tasks[1].is_priority_1 is True

        # Flow tomorrow should be third
        assert tasks[2].content == "Normal priority task"
        assert tasks[2].is_flow_tomorrow is True

    def test_task_limit_applied(self):
        """Test that task selection is limited to reasonable number."""
        # Create 15 tasks (more than the 10 limit)
        mock_tasks = []
        for i in range(15):
            mock_tasks.append(
                {
                    "id": f"task_{i}",
                    "content": f"Task {i}",
                    "labels": ["@flow_tomorrow"],
                    "priority": 4 if i < 5 else 1,  # First 5 are high priority
                    "project_id": "proj1",
                    "due": None,
                }
            )

        self.mock_todoist.get_tasks.return_value = mock_tasks
        self.mock_todoist.get_projects.return_value = [{"id": "proj1", "name": "Work"}]

        tasks = self.selector.get_morning_brief_tasks("U123", is_monday=False)

        # Should be limited to 10 tasks
        assert len(tasks) == 10

        # Should prioritize the high priority tasks
        high_priority_count = sum(1 for task in tasks if task.is_priority_1)
        assert high_priority_count == 5  # All 5 high priority tasks should be included


class TestFeatureFlagIntegration:
    """Test that morning brief respects feature flags."""

    def setup_method(self):
        """Reset feature flags before each test."""
        clear_all_overrides()

    def test_morning_brief_disabled_by_flag(self):
        """Test that morning brief is disabled when feature flag is off."""
        # Ensure flag is disabled
        set_override(FlowCoachFlag.FC_MORNING_MODAL_V1, False)

        # Mock services
        mock_planning = Mock()
        modal_handler = MorningBriefModal(mock_planning)
        mock_client = Mock()

        # Try to open modal
        modal_handler.open_modal("trigger_123", "U123456", mock_client)

        # Should not open modal when disabled
        mock_client.views_open.assert_not_called()
        mock_planning.get_morning_brief_tasks.assert_not_called()

    def test_morning_brief_enabled_by_flag(self):
        """Test that morning brief works when feature flag is on."""
        # Enable flag
        set_override(FlowCoachFlag.FC_MORNING_MODAL_V1, True)

        # Mock services
        mock_planning = Mock()
        mock_planning.get_morning_brief_tasks.return_value = []  # Empty for simple test
        modal_handler = MorningBriefModal(mock_planning)
        mock_client = Mock()

        # Try to open modal
        modal_handler.open_modal("trigger_123", "U123456", mock_client)

        # Should open modal when enabled
        mock_client.views_open.assert_called_once()
        mock_planning.get_morning_brief_tasks.assert_called_once_with("U123456")


class TestErrorHandling:
    """Test error handling in morning brief flow."""

    @patch("apps.server.core.planning.PlanningService")
    def test_partial_planning_failure(self, mock_planning_class):
        """Test handling when some tasks fail to be planned."""
        # Mock planning service with mixed success/failure
        mock_planning = Mock()
        mock_planning_class.return_value = mock_planning

        def mock_mark_planned(task_id, priority, time):
            # Simulate failure for task_456
            return task_id != "task_456"

        mock_planning.mark_task_as_planned.side_effect = mock_mark_planned
        mock_planning.save_checkin_time.return_value = True

        # Create modal handler
        modal_handler = MorningBriefModal(mock_planning)
        mock_client = Mock()

        # Simulate submission with multiple tasks
        submission_body = {
            "view": {
                "private_metadata": "U123456",
                "state": {
                    "values": {
                        "task_plan_0": {
                            "priority_0": {"selected_option": {"value": "p1"}},
                            "time_0": {"selected_time": "09:00"},
                        },
                        "task_id_0": {"task_id": {"value": "task_123"}},
                        "task_plan_1": {
                            "priority_1": {"selected_option": {"value": "p2"}},
                            "time_1": {"selected_time": "10:00"},
                        },
                        "task_id_1": {"task_id": {"value": "task_456"}},
                    }
                },
            }
        }

        # Handle submission
        modal_handler.handle_submission(submission_body, mock_client)

        # Verify completion message indicates partial success
        mock_client.chat_postMessage.assert_called_once()
        message_call = mock_client.chat_postMessage.call_args
        message_text = message_call[1]["text"].lower()
        assert "partially complete" in message_text or "1 of 2" in message_text
