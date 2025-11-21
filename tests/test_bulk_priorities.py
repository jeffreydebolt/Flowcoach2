"""Tests for bulk priority review functionality (Phase 2.0)."""

from unittest.mock import Mock, patch

from apps.server.slack.blocks import render_bulk_priority_list
from handlers.message_handlers import _handle_bulk_priority_review, _is_bulk_priority_intent


class TestBulkPriorities:
    """Test bulk priority review, pagination, and per-row updates."""

    def test_bulk_priority_intent_detection(self):
        """Test detection of bulk priority review requests."""
        positive_cases = [
            "show my open tasks to adjust priorities",
            "adjust priorities",
            "priority review",
            "bulk priorities",
            "review my priorities",
            "change task priorities",
            "Show My Open Tasks To Adjust Priorities",  # Case insensitive
            "I want to adjust priorities for my tasks",  # Contains pattern
        ]

        for text in positive_cases:
            assert _is_bulk_priority_intent(text), f"Should detect: {text}"

    def test_bulk_priority_intent_non_detection(self):
        """Test that non-bulk-priority requests aren't detected."""
        negative_cases = [
            "create a task",
            "show my calendar",
            "what's my schedule",
            "priority task for today",  # Contains "priority" but different context
            "adjust the meeting time",  # Contains "adjust" but different context
            "",
            "hello",
        ]

        for text in negative_cases:
            assert not _is_bulk_priority_intent(text), f"Should not detect: {text}"

    def test_render_bulk_priority_list_basic(self):
        """Test basic rendering of bulk priority list."""
        tasks = [
            {"id": "task_1", "content": "Call doctor", "priority_human": 1},
            {"id": "task_2", "content": "Review contract", "priority_human": 3},
            {"id": "task_3", "content": "Send proposal", "priority_human": 2},
        ]

        message = render_bulk_priority_list(tasks, page=0, total_pages=1)
        blocks = message["blocks"]

        # Should have header, page info, divider + (3 tasks × 3 blocks each) = 6 task blocks
        # Header (1) + Page info (1) + Divider (1) + Tasks (9) = 12 blocks
        assert len(blocks) >= 3  # At least header + page + divider

        # Check header
        assert blocks[0]["type"] == "header"
        assert "Adjust Task Priorities" in blocks[0]["text"]["text"]

        # Check page info
        assert blocks[1]["type"] == "section"
        assert "Page 1 of 1" in blocks[1]["text"]["text"]

    def test_render_bulk_priority_pagination(self):
        """Test pagination controls in bulk priority list."""
        tasks = [{"id": f"task_{i}", "content": f"Task {i}", "priority_human": 3} for i in range(5)]

        # Test middle page (should have both prev and next)
        message = render_bulk_priority_list(tasks, page=1, total_pages=3)
        blocks = message["blocks"]

        # Look for pagination block at the end
        pagination_blocks = [b for b in blocks if b.get("block_id") == "pagination_controls"]
        assert len(pagination_blocks) == 1

        pagination_block = pagination_blocks[0]
        elements = pagination_block["elements"]

        # Should have Previous + Page indicator + Next
        assert len(elements) == 3

        # Check action IDs
        prev_button = next(el for el in elements if "Previous" in el["text"]["text"])
        assert prev_button["action_id"] == "page_priorities_0"

        next_button = next(el for el in elements if "Next" in el["text"]["text"])
        assert next_button["action_id"] == "page_priorities_2"

    def test_priority_badge_display(self):
        """Test that priority badges display correctly in bulk list."""
        tasks = [
            {"id": "task_p1", "content": "Urgent task", "priority_human": 1},
            {"id": "task_p2", "content": "High task", "priority_human": 2},
            {"id": "task_p3", "content": "Normal task", "priority_human": 3},
            {"id": "task_p4", "content": "Low task", "priority_human": 4},
        ]

        message = render_bulk_priority_list(tasks, page=0, total_pages=1)
        blocks = message["blocks"]

        # Find task section blocks
        task_blocks = [
            b for b in blocks if b["type"] == "section" and "task" in b["text"]["text"].lower()
        ]

        # Check priority badges
        expected_badges = ["🟥 P1", "🟧 P2", "🟨 P3", "⬜ P4"]

        for i, expected_badge in enumerate(expected_badges):
            task_text = task_blocks[i]["text"]["text"]
            assert expected_badge in task_text

    def test_bulk_priority_button_action_ids(self):
        """Test that bulk priority buttons have correct action IDs."""
        tasks = [{"id": "task_abc123", "content": "Test task", "priority_human": 3}]

        message = render_bulk_priority_list(tasks, page=0, total_pages=1)
        blocks = message["blocks"]

        # Find the priority button actions block
        action_blocks = [
            b
            for b in blocks
            if b["type"] == "actions" and b.get("block_id", "").startswith("bulk_prio")
        ]
        assert len(action_blocks) == 1

        action_block = action_blocks[0]
        elements = action_block["elements"]

        # Should have 4 priority buttons
        assert len(elements) == 4

        # Check action IDs
        expected_actions = [
            "bulk_set_priority_task_abc123_P1",
            "bulk_set_priority_task_abc123_P2",
            "bulk_set_priority_task_abc123_P3",
            "bulk_set_priority_task_abc123_P4",
        ]

        actual_actions = [el["action_id"] for el in elements]
        assert actual_actions == expected_actions

    def test_bulk_priority_current_selection_highlight(self):
        """Test that current priority is highlighted in bulk list."""
        tasks = [{"id": "task_123", "content": "Test task", "priority_human": 2}]  # P2 selected

        message = render_bulk_priority_list(tasks, page=0, total_pages=1)
        blocks = message["blocks"]

        # Find priority button actions
        action_blocks = [
            b
            for b in blocks
            if b["type"] == "actions" and b.get("block_id", "").startswith("bulk_prio")
        ]
        action_block = action_blocks[0]
        elements = action_block["elements"]

        # P2 button should be highlighted
        p2_button = next(el for el in elements if "P2" in el["text"]["text"])
        assert p2_button["style"] == "primary"

        # P1 button should have danger style when not selected
        p1_button = next(el for el in elements if "P1" in el["text"]["text"])
        assert p1_button["style"] == "danger"

        # P3 and P4 should not have styles
        for element in elements:
            if "P3" in element["text"]["text"] or "P4" in element["text"]["text"]:
                assert element.get("style") != "primary"

    def test_content_truncation_for_long_tasks(self):
        """Test that long task content is truncated properly."""
        long_content = "This is a very long task description that should be truncated because it exceeds the 70 character limit for display"

        tasks = [{"id": "task_long", "content": long_content, "priority_human": 3}]

        message = render_bulk_priority_list(tasks, page=0, total_pages=1)
        blocks = message["blocks"]

        # Find task section
        task_blocks = [
            b for b in blocks if b["type"] == "section" and long_content[:20] in b["text"]["text"]
        ]
        assert len(task_blocks) == 1

        task_text = task_blocks[0]["text"]["text"]

        # Should be truncated with "..."
        assert len(task_text) < len(long_content) + 20  # Account for badge prefix
        assert "..." in task_text

    @patch("apps.server.integrations.todoist_client.TodoistClient")
    def test_handle_bulk_priority_review_success(self, mock_client_class):
        """Test successful handling of bulk priority review request."""
        # Mock todoist client and tasks
        mock_client = Mock()
        mock_client.get_tasks.return_value = [
            {
                "id": "task_1",
                "content": "Task 1",
                "priority": 2,
                "due": None,
                "created_at": "2023-01-01",
            },
            {
                "id": "task_2",
                "content": "Task 2",
                "priority": 4,
                "due": {"date": "2023-12-01"},
                "created_at": "2023-01-02",
            },
        ]
        mock_client.get_priority_human.side_effect = lambda p: 5 - p  # Mock inversion

        services = {"todoist": mock_client}

        response = _handle_bulk_priority_review("user_123", services)

        assert response is not None
        assert response["response_type"] == "bulk_priorities"
        assert len(response["tasks"]) == 2
        assert response["page"] == 0
        assert response["total_pages"] == 1

        # Check task formatting
        task_1 = response["tasks"][0]
        assert task_1["id"] == "task_1"
        assert task_1["content"] == "Task 1"
        assert task_1["priority_human"] == 3  # 5 - 2

    def test_handle_bulk_priority_review_no_tasks(self):
        """Test handling when no open tasks exist."""
        mock_client = Mock()
        mock_client.get_tasks.return_value = []

        services = {"todoist": mock_client}

        response = _handle_bulk_priority_review("user_123", services)

        assert response is not None
        assert response["response_type"] == "simple"
        assert "No open tasks found" in response["message"]

    def test_handle_bulk_priority_review_no_service(self):
        """Test handling when todoist service is not available."""
        services = {}  # No todoist service

        response = _handle_bulk_priority_review("user_123", services)

        assert response is not None
        assert response["response_type"] == "error"
        assert "Todoist service not available" in response["message"]

    def test_task_sorting_due_date_priority(self):
        """Test that tasks are sorted by due date first, then created date."""
        mock_client = Mock()
        mock_client.get_tasks.return_value = [
            {
                "id": "task_1",
                "content": "No due",
                "priority": 2,
                "due": None,
                "created_at": "2023-01-03",
            },
            {
                "id": "task_2",
                "content": "Due tomorrow",
                "priority": 2,
                "due": {"date": "2023-12-02"},
                "created_at": "2023-01-02",
            },
            {
                "id": "task_3",
                "content": "Due today",
                "priority": 2,
                "due": {"date": "2023-12-01"},
                "created_at": "2023-01-01",
            },
        ]
        mock_client.get_priority_human.return_value = 3

        services = {"todoist": mock_client}

        response = _handle_bulk_priority_review("user_123", services)

        # Tasks should be sorted: due tasks first (by due date), then non-due tasks (by created date)
        task_ids = [task["id"] for task in response["tasks"]]

        # Expected order: task_3 (due 12-01), task_2 (due 12-02), task_1 (no due, created last)
        assert task_ids == ["task_3", "task_2", "task_1"]

    def test_pagination_calculation(self):
        """Test pagination calculation with different task counts."""
        # Test with 23 tasks, page size 10
        tasks = [
            {"id": f"task_{i}", "content": f"Task {i}", "priority_human": 3} for i in range(23)
        ]

        message = render_bulk_priority_list(tasks[:10], page=0, total_pages=3)  # First page
        blocks = message["blocks"]

        # Check page info shows correct pagination
        page_info_block = blocks[1]
        assert "Page 1 of 3" in page_info_block["text"]["text"]

        # Test last page
        message = render_bulk_priority_list(tasks[20:23], page=2, total_pages=3)  # Last page
        page_info_text = message["blocks"][1]["text"]["text"]
        assert "Page 3 of 3" in page_info_text
