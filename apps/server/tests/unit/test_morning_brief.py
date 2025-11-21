"""Unit tests for morning brief modal and planning logic."""

from unittest.mock import Mock, patch

from apps.server.core.planning import PlanningService, TaskCandidate, TaskSelector
from apps.server.slack.modals.morning_brief import MorningBriefModal


class TestTaskSelector:
    """Test task selection logic for morning brief."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_todoist = Mock()
        self.selector = TaskSelector(self.mock_todoist)

    def test_get_morning_brief_tasks_monday(self):
        """Test that Monday includes weekly tasks."""
        # Mock Todoist tasks
        self.mock_todoist.get_tasks.return_value = [
            {
                "id": "123",
                "content": "Weekly review",
                "labels": ["@flow_weekly"],
                "priority": 1,
                "project_id": "proj1",
                "due": None,
            },
            {
                "id": "456",
                "content": "Daily task",
                "labels": ["@flow_tomorrow"],
                "priority": 1,
                "project_id": "proj1",
                "due": None,
            },
        ]

        self.mock_todoist.get_projects.return_value = [{"id": "proj1", "name": "Work"}]

        # Test Monday (includes weekly tasks)
        tasks = self.selector.get_morning_brief_tasks("U123", is_monday=True)

        assert len(tasks) == 2
        assert any(task.content == "Weekly review" for task in tasks)
        assert any(task.content == "Daily task" for task in tasks)

    def test_get_morning_brief_tasks_not_monday(self):
        """Test that non-Monday excludes weekly tasks."""
        self.mock_todoist.get_tasks.return_value = [
            {
                "id": "123",
                "content": "Weekly review",
                "labels": ["@flow_weekly"],
                "priority": 1,
                "project_id": "proj1",
                "due": None,
            },
            {
                "id": "456",
                "content": "Daily task",
                "labels": ["@flow_tomorrow"],
                "priority": 1,
                "project_id": "proj1",
                "due": None,
            },
        ]

        self.mock_todoist.get_projects.return_value = [{"id": "proj1", "name": "Work"}]

        # Test Tuesday (excludes weekly tasks)
        tasks = self.selector.get_morning_brief_tasks("U123", is_monday=False)

        assert len(tasks) == 1
        assert tasks[0].content == "Daily task"
        assert not any(task.content == "Weekly review" for task in tasks)

    def test_overdue_task_included(self):
        """Test that overdue tasks are included."""
        # Mock task with past due date
        past_date = "2025-11-09"  # Yesterday (test runs on 2025-11-10)

        self.mock_todoist.get_tasks.return_value = [
            {
                "id": "789",
                "content": "Overdue task",
                "labels": [],
                "priority": 1,
                "project_id": "proj1",
                "due": {"date": past_date},
            }
        ]

        self.mock_todoist.get_projects.return_value = [{"id": "proj1", "name": "Work"}]

        tasks = self.selector.get_morning_brief_tasks("U123", is_monday=False)

        assert len(tasks) == 1
        assert tasks[0].content == "Overdue task"
        assert tasks[0].is_overdue is True

    def test_priority_1_task_included(self):
        """Test that Priority 1 tasks are included."""
        self.mock_todoist.get_tasks.return_value = [
            {
                "id": "999",
                "content": "Important task",
                "labels": [],
                "priority": 4,  # Todoist priority 4 = Priority 1
                "project_id": "proj1",
                "due": None,
            }
        ]

        self.mock_todoist.get_projects.return_value = [{"id": "proj1", "name": "Work"}]

        tasks = self.selector.get_morning_brief_tasks("U123", is_monday=False)

        assert len(tasks) == 1
        assert tasks[0].content == "Important task"
        assert tasks[0].is_priority_1 is True

    def test_irrelevant_task_excluded(self):
        """Test that irrelevant tasks are excluded."""
        self.mock_todoist.get_tasks.return_value = [
            {
                "id": "111",
                "content": "Random task",
                "labels": ["@someday"],
                "priority": 1,
                "project_id": "proj1",
                "due": None,
            }
        ]

        tasks = self.selector.get_morning_brief_tasks("U123", is_monday=False)

        assert len(tasks) == 0

    def test_task_sorting_priority(self):
        """Test that tasks are sorted by priority correctly."""
        self.mock_todoist.get_tasks.return_value = [
            {
                "id": "1",
                "content": "Flow tomorrow",
                "labels": ["@flow_tomorrow"],
                "priority": 1,
                "project_id": "proj1",
                "due": None,
            },
            {
                "id": "2",
                "content": "Priority 1",
                "labels": [],
                "priority": 4,
                "project_id": "proj1",
                "due": None,
            },
            {
                "id": "3",
                "content": "Overdue",
                "labels": [],
                "priority": 1,
                "project_id": "proj1",
                "due": {"date": "2025-11-09"},  # Yesterday
            },
        ]

        self.mock_todoist.get_projects.return_value = [{"id": "proj1", "name": "Work"}]

        tasks = self.selector.get_morning_brief_tasks("U123", is_monday=False)

        # Should be sorted: overdue > priority 1 > flow_tomorrow
        assert len(tasks) == 3
        assert tasks[0].content == "Overdue"
        assert tasks[1].content == "Priority 1"
        assert tasks[2].content == "Flow tomorrow"


class TestPlanningService:
    """Test planning service functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_todoist = Mock()
        self.service = PlanningService(self.mock_todoist)

    def test_mark_task_as_planned_success(self):
        """Test successful task planning."""
        self.mock_todoist.add_task_label.return_value = True
        self.mock_todoist.add_task_comment.return_value = True

        result = self.service.mark_task_as_planned("task123", "p1", "09:00")

        assert result is True
        self.mock_todoist.add_task_label.assert_called_once_with("task123", "@flow_top_today")
        self.mock_todoist.add_task_comment.assert_called_once_with(
            "task123", "flow:planned_due priority=p1 time=09:00"
        )

    def test_mark_task_as_planned_label_failure(self):
        """Test task planning when label addition fails."""
        self.mock_todoist.add_task_label.return_value = False

        result = self.service.mark_task_as_planned("task123", "p1", "09:00")

        assert result is False
        self.mock_todoist.add_task_label.assert_called_once()
        # Comment should not be called if label fails
        self.mock_todoist.add_task_comment.assert_not_called()

    def test_mark_task_as_planned_comment_failure(self):
        """Test task planning when comment addition fails."""
        self.mock_todoist.add_task_label.return_value = True
        self.mock_todoist.add_task_comment.return_value = False

        result = self.service.mark_task_as_planned("task123", "p1", "09:00")

        assert result is False
        self.mock_todoist.add_task_label.assert_called_once()
        self.mock_todoist.add_task_comment.assert_called_once()

    @patch("apps.server.core.prefs.PreferencesStore")
    def test_save_checkin_time_success(self, mock_store_class):
        """Test successful checkin time save."""
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        # Mock existing preferences
        mock_prefs = Mock()
        mock_store.load_prefs.return_value = mock_prefs
        mock_store.save_prefs.return_value = True

        result = self.service.save_checkin_time("U123", "09:30")

        assert result is True
        assert mock_prefs.checkin_time_today == "09:30"
        mock_store.save_prefs.assert_called_once_with("U123", mock_prefs)

    @patch("apps.server.core.prefs.PreferencesStore")
    def test_save_checkin_time_no_prefs(self, mock_store_class):
        """Test checkin time save when no preferences exist."""
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.load_prefs.return_value = None

        result = self.service.save_checkin_time("U123", "09:30")

        assert result is False
        mock_store.save_prefs.assert_not_called()


class TestMorningBriefModal:
    """Test morning brief modal functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_planning_service = Mock()
        self.modal = MorningBriefModal(self.mock_planning_service)
        self.mock_client = Mock()

    @patch("apps.server.slack.modals.morning_brief.is_enabled")
    def test_open_modal_feature_disabled(self, mock_is_enabled):
        """Test modal opening when feature is disabled."""
        mock_is_enabled.return_value = False

        self.modal.open_modal("trigger123", "U123", self.mock_client)

        # Should not open modal when disabled
        self.mock_client.views_open.assert_not_called()

    @patch("apps.server.slack.modals.morning_brief.is_enabled")
    def test_open_modal_no_tasks(self, mock_is_enabled):
        """Test modal opening when no tasks need planning."""
        mock_is_enabled.return_value = True
        self.mock_planning_service.get_morning_brief_tasks.return_value = []

        self.modal.open_modal("trigger123", "U123", self.mock_client)

        # Should open empty modal
        self.mock_client.views_open.assert_called_once()
        call_args = self.mock_client.views_open.call_args
        view = call_args[1]["view"]
        assert view["callback_id"] == "morning_brief_empty"

    @patch("apps.server.slack.modals.morning_brief.is_enabled")
    def test_open_modal_with_tasks(self, mock_is_enabled):
        """Test modal opening with tasks to plan."""
        mock_is_enabled.return_value = True

        # Mock tasks
        mock_tasks = [
            TaskCandidate(
                id="123",
                content="Test task",
                project_name="Work",
                priority=4,
                due_date=None,
                labels=["@flow_tomorrow"],
                is_overdue=False,
                is_priority_1=True,
                is_flow_tomorrow=True,
                is_flow_weekly=False,
            )
        ]
        self.mock_planning_service.get_morning_brief_tasks.return_value = mock_tasks

        self.modal.open_modal("trigger123", "U123", self.mock_client)

        # Should open planning modal
        self.mock_client.views_open.assert_called_once()
        call_args = self.mock_client.views_open.call_args
        view = call_args[1]["view"]
        assert view["callback_id"] == "flowcoach_morning_brief_submit"
        assert view["private_metadata"] == "U123"

    def test_format_task_context(self):
        """Test task context formatting."""
        task = TaskCandidate(
            id="123",
            content="Test task",
            project_name="Work Project",
            priority=4,
            due_date="2025-11-11",
            labels=["@flow_tomorrow"],
            is_overdue=False,
            is_priority_1=True,
            is_flow_tomorrow=True,
            is_flow_weekly=False,
        )

        context = self.modal._format_task_context(task)

        assert "📁 Work Project" in context
        assert "📅 Due 2025-11-11" in context
        assert "⭐ Priority 1" in context
        assert "@flow_tomorrow" in context

    def test_format_task_context_overdue(self):
        """Test task context formatting for overdue tasks."""
        task = TaskCandidate(
            id="123",
            content="Test task",
            project_name="Inbox",
            priority=1,
            due_date="2025-11-09",
            labels=[],
            is_overdue=True,
            is_priority_1=False,
            is_flow_tomorrow=False,
            is_flow_weekly=False,
        )

        context = self.modal._format_task_context(task)

        assert "🔴 Overdue" in context
        assert "📁 Inbox" not in context  # Inbox is default, not shown
