"""Tests for Phase 2.0 conversational task creation with chips."""

from apps.server.slack.blocks import render_task_creation_message


class TestTaskCreationChips:
    """Test task creation with time and priority chips."""

    def test_task_creation_with_missing_time_shows_chips(self):
        """Test that missing time shows time chips with default selected."""
        message = render_task_creation_message(
            task_content="Call Banner Med",
            task_id="task_123",
            current_time=None,  # Missing time
            current_priority=2,  # Has priority
            show_chips=True,
        )

        blocks = message["blocks"]

        # Should have task confirmation + time chips + priority chips
        assert len(blocks) == 3
        assert ":white_check_mark: Added *Call Banner Med*" in blocks[0]["text"]["text"]

        # Check time chips are present with default 10min selected
        time_block = blocks[1]
        assert time_block["type"] == "actions"
        assert time_block["block_id"] == "time_row_task_123"

        time_elements = time_block["elements"]
        assert len(time_elements) == 3

        # Find the 10m button (default) - should be highlighted
        ten_min_button = next(el for el in time_elements if el["text"]["text"] == "10m")
        assert ten_min_button["style"] == "primary"

        # Other buttons should not be highlighted
        two_min_button = next(el for el in time_elements if el["text"]["text"] == "2m")
        assert "style" not in two_min_button

    def test_task_creation_with_missing_priority_shows_chips(self):
        """Test that missing priority shows priority chips with default selected."""
        message = render_task_creation_message(
            task_content="Review contract",
            task_id="task_456",
            current_time="2min",  # Has time
            current_priority=None,  # Missing priority
            show_chips=True,
        )

        blocks = message["blocks"]

        # Should have task confirmation + time chips + priority chips
        assert len(blocks) == 3

        # Check priority chips are present with default P3 selected
        priority_block = blocks[2]
        assert priority_block["type"] == "actions"
        assert priority_block["block_id"] == "prio_row_task_456"

        priority_elements = priority_block["elements"]
        assert len(priority_elements) == 4

        # Find the P3 button (default) - should be highlighted
        p3_button = next(el for el in priority_elements if "P3" in el["text"]["text"])
        assert p3_button["style"] == "primary"

        # P1 button should have danger style when not selected
        p1_button = next(el for el in priority_elements if "P1" in el["text"]["text"])
        assert p1_button["style"] == "danger"

    def test_task_creation_with_both_parsed_omits_chips(self):
        """Test that when both time and priority are parsed, no chips are shown."""
        message = render_task_creation_message(
            task_content="Send proposal",
            task_id="task_789",
            current_time="30+min",  # Has time
            current_priority=1,  # Has priority
            show_chips=False,  # Both present, no chips needed
        )

        blocks = message["blocks"]

        # Should have only task confirmation, no chips
        assert len(blocks) == 1
        assert ":white_check_mark: Added *Send proposal*" in blocks[0]["text"]["text"]

    def test_chip_action_ids_format_correctly(self):
        """Test that chip action IDs include task ID and values."""
        message = render_task_creation_message(
            task_content="Test task",
            task_id="task_abc123",
            current_time="10min",
            current_priority=2,
            show_chips=True,
        )

        blocks = message["blocks"]

        # Check time chip action IDs
        time_elements = blocks[1]["elements"]
        expected_time_actions = [
            "set_time_task_abc123_2min",
            "set_time_task_abc123_10min",
            "set_time_task_abc123_30+min",
        ]

        actual_time_actions = [el["action_id"] for el in time_elements]
        assert actual_time_actions == expected_time_actions

        # Check priority chip action IDs
        priority_elements = blocks[2]["elements"]
        expected_priority_actions = [
            "set_priority_task_abc123_P1",
            "set_priority_task_abc123_P2",
            "set_priority_task_abc123_P3",
            "set_priority_task_abc123_P4",
        ]

        actual_priority_actions = [el["action_id"] for el in priority_elements]
        assert actual_priority_actions == expected_priority_actions

    def test_chip_selection_highlights_correctly(self):
        """Test that current selections are properly highlighted."""
        # Test with P1 selected (should show primary style)
        message = render_task_creation_message(
            task_content="Urgent task",
            task_id="task_urgent",
            current_time="2min",
            current_priority=1,  # P1 selected
            show_chips=True,
        )

        priority_block = message["blocks"][2]
        priority_elements = priority_block["elements"]

        # P1 should be highlighted with primary
        p1_button = next(el for el in priority_elements if "P1" in el["text"]["text"])
        assert p1_button["style"] == "primary"

        # Other priorities should not be primary
        for element in priority_elements:
            if "P1" not in element["text"]["text"]:
                assert element.get("style") != "primary"

    def test_defaults_applied_when_none_specified(self):
        """Test that proper defaults are used when components are None."""
        message = render_task_creation_message(
            task_content="Default test",
            task_id="task_defaults",
            current_time=None,  # Should default to "10min"
            current_priority=None,  # Should default to 3 (P3)
            show_chips=True,
        )

        blocks = message["blocks"]

        # Check default time (10min) is highlighted
        time_elements = blocks[1]["elements"]
        ten_min_button = next(el for el in time_elements if el["text"]["text"] == "10m")
        assert ten_min_button["style"] == "primary"

        # Check default priority (P3) is highlighted
        priority_elements = blocks[2]["elements"]
        p3_button = next(el for el in priority_elements if "P3" in el["text"]["text"])
        assert p3_button["style"] == "primary"

    def test_time_chip_labels_display_correctly(self):
        """Test that time chips show the right display labels."""
        message = render_task_creation_message(
            task_content="Time test",
            task_id="task_time",
            current_time="30+min",
            current_priority=3,
            show_chips=True,
        )

        time_elements = message["blocks"][1]["elements"]

        # Check display labels match expected format
        expected_labels = ["2m", "10m", "30m+"]
        actual_labels = [el["text"]["text"] for el in time_elements]
        assert actual_labels == expected_labels

    def test_priority_chip_labels_include_emojis(self):
        """Test that priority chips show emojis and labels correctly."""
        message = render_task_creation_message(
            task_content="Priority test",
            task_id="task_priority",
            current_time="10min",
            current_priority=2,
            show_chips=True,
        )

        priority_elements = message["blocks"][2]["elements"]

        # Check labels include emojis
        expected_labels = ["P1 🔴", "P2 🟠", "P3 🟡", "P4 ⚪"]
        actual_labels = [el["text"]["text"] for el in priority_elements]
        assert actual_labels == expected_labels

    def test_multiple_tasks_have_unique_block_ids(self):
        """Test that different tasks get unique block IDs for chips."""
        message1 = render_task_creation_message(
            task_content="Task 1", task_id="task_001", show_chips=True
        )

        message2 = render_task_creation_message(
            task_content="Task 2", task_id="task_002", show_chips=True
        )

        # Block IDs should be unique
        assert message1["blocks"][1]["block_id"] == "time_row_task_001"
        assert message1["blocks"][2]["block_id"] == "prio_row_task_001"

        assert message2["blocks"][1]["block_id"] == "time_row_task_002"
        assert message2["blocks"][2]["block_id"] == "prio_row_task_002"
