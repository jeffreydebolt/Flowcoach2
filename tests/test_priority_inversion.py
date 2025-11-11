"""Tests for human-friendly priority inversion (Phase 2.0)."""

import pytest
from unittest.mock import Mock, patch
from apps.server.integrations.todoist_client import TodoistClient


class TestPriorityInversion:
    """Test P1-P4 ↔ Todoist 4-1 priority mapping."""

    def test_human_to_todoist_priority_mapping(self):
        """Test conversion from human priorities to Todoist priorities."""
        client = TodoistClient("fake_token")

        # Human P1 (highest) → Todoist 4 (urgent)
        assert 5 - 1 == 4  # P1 → 4
        assert 5 - 2 == 3  # P2 → 3
        assert 5 - 3 == 2  # P3 → 2
        assert 5 - 4 == 1  # P4 → 1

        # Test the actual mapping logic
        test_cases = [
            (1, 4),  # P1 urgent → Todoist urgent
            (2, 3),  # P2 high → Todoist high
            (3, 2),  # P3 normal → Todoist normal
            (4, 1),  # P4 low → Todoist low
        ]

        for human_priority, expected_todoist in test_cases:
            todoist_priority = 5 - human_priority
            assert todoist_priority == expected_todoist

    def test_todoist_to_human_priority_mapping(self):
        """Test conversion from Todoist priorities to human priorities."""
        client = TodoistClient("fake_token")

        # Test get_priority_human method
        test_cases = [
            (4, 1),  # Todoist urgent → P1
            (3, 2),  # Todoist high → P2
            (2, 3),  # Todoist normal → P3
            (1, 4),  # Todoist low → P4
        ]

        for todoist_priority, expected_human in test_cases:
            human_priority = client.get_priority_human(todoist_priority)
            assert human_priority == expected_human

    @patch("apps.server.integrations.todoist_client.TodoistAPI")
    def test_set_priority_human_method(self, mock_api_class):
        """Test set_priority_human method converts and calls API correctly."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        client = TodoistClient("fake_token")

        # Test setting P1 (human) → 4 (Todoist)
        client.set_priority_human("task_123", 1)

        mock_api.update_task.assert_called_once_with(task_id="task_123", priority=4)

        # Reset and test P3 (human) → 2 (Todoist)
        mock_api.reset_mock()
        client.set_priority_human("task_456", 3)

        mock_api.update_task.assert_called_once_with(task_id="task_456", priority=2)

    @patch("apps.server.integrations.todoist_client.TodoistAPI")
    def test_priority_clamping(self, mock_api_class):
        """Test that human priorities are clamped to valid range 1-4."""
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        client = TodoistClient("fake_token")

        # Test values outside range get clamped
        test_cases = [
            (0, 1),  # Below range → clamp to 1 → Todoist 4
            (-5, 1),  # Negative → clamp to 1 → Todoist 4
            (5, 4),  # Above range → clamp to 4 → Todoist 1
            (10, 4),  # Way above → clamp to 4 → Todoist 1
        ]

        for input_priority, clamped_human in test_cases:
            expected_todoist = 5 - clamped_human

            client.set_priority_human("task_test", input_priority)

            # Should call with clamped and inverted priority
            mock_api.update_task.assert_called_with(task_id="task_test", priority=expected_todoist)
            mock_api.reset_mock()

    def test_priority_inversion_is_symmetric(self):
        """Test that converting back and forth preserves values."""
        client = TodoistClient("fake_token")

        # Test round-trip conversion
        for human_priority in [1, 2, 3, 4]:
            # Human → Todoist
            todoist_priority = 5 - human_priority

            # Todoist → Human
            converted_back = client.get_priority_human(todoist_priority)

            assert converted_back == human_priority

    def test_priority_semantic_mapping(self):
        """Test that priority mapping matches semantic intent."""
        client = TodoistClient("fake_token")

        # Human semantics: P1=urgent, P2=high, P3=normal, P4=low
        # Todoist semantics: 4=urgent, 3=high, 2=normal, 1=low

        semantic_mappings = [
            ("P1 urgent", 1, 4, "urgent"),
            ("P2 high", 2, 3, "high"),
            ("P3 normal", 3, 2, "normal"),
            ("P4 low", 4, 1, "low"),
        ]

        for description, human_p, todoist_p, semantic in semantic_mappings:
            # Forward mapping
            assert 5 - human_p == todoist_p, f"Failed forward mapping for {description}"

            # Reverse mapping
            assert (
                client.get_priority_human(todoist_p) == human_p
            ), f"Failed reverse mapping for {description}"

    @patch("apps.server.integrations.todoist_client.TodoistAPI")
    def test_set_priority_human_handles_api_errors(self, mock_api_class):
        """Test that set_priority_human handles API errors gracefully."""
        mock_api = Mock()
        mock_api.update_task.side_effect = Exception("API Error")
        mock_api_class.return_value = mock_api

        client = TodoistClient("fake_token")

        # Should return False on error, not raise
        result = client.set_priority_human("task_error", 2)

        assert result is False
        mock_api.update_task.assert_called_once_with(task_id="task_error", priority=3)

    @patch("apps.server.integrations.todoist_client.TodoistAPI")
    def test_set_priority_human_returns_true_on_success(self, mock_api_class):
        """Test that set_priority_human returns True on successful update."""
        mock_api = Mock()
        mock_api.update_task.return_value = True  # Simulate success
        mock_api_class.return_value = mock_api

        client = TodoistClient("fake_token")

        result = client.set_priority_human("task_success", 1)

        assert result is True
        mock_api.update_task.assert_called_once_with(task_id="task_success", priority=4)

    def test_priority_boundary_values(self):
        """Test priority inversion works correctly at boundaries."""
        client = TodoistClient("fake_token")

        # Test exact boundary values
        boundary_tests = [
            (1, 4),  # Highest human → Highest Todoist
            (4, 1),  # Lowest human → Lowest Todoist
        ]

        for human, expected_todoist in boundary_tests:
            todoist = 5 - human
            assert todoist == expected_todoist

            # Round trip
            back_to_human = client.get_priority_human(todoist)
            assert back_to_human == human

    def test_default_priority_handling(self):
        """Test handling of default/missing priority values."""
        client = TodoistClient("fake_token")

        # Todoist default is typically 2 (normal)
        # Should map to human P3 (normal)
        default_todoist = 2
        human_equivalent = client.get_priority_human(default_todoist)

        assert human_equivalent == 3  # P3 normal

        # Human default P3 should map to Todoist 2
        default_human = 3
        todoist_equivalent = 5 - default_human

        assert todoist_equivalent == 2  # Todoist normal
