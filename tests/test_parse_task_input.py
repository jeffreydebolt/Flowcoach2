"""Tests for conversational task input parsing (Phase 2.0)."""

import pytest
from apps.server.nlp.parser import parse_task_input, ParsedTask


class TestParseTaskInput:
    """Test conversational task parsing with separators, priorities, and times."""

    def test_full_conversational_format(self):
        """Test full format: task — time — priority."""
        result = parse_task_input("Build plan for 2026 insurance — 30m+ — P2")

        assert result.content == "Build plan for 2026 insurance"
        assert result.time_label == "30+min"
        assert result.user_priority == 2

    def test_different_separators(self):
        """Test various separator formats."""
        test_cases = [
            ("Call doctor — 10m — P1", "Call doctor", "10min", 1),
            ("Email team - 2m - urgent", "Email team", "2min", 1),
            ("Review contract | 30+ | high", "Review contract", "30+min", 2),
            ("Update docs; 10; P3", "Update docs", "10min", 3),
            ("Fix bug, 2min, low", "Fix bug", "2min", 4),
        ]

        for input_text, expected_content, expected_time, expected_priority in test_cases:
            result = parse_task_input(input_text)
            assert result.content == expected_content
            assert result.time_label == expected_time
            assert result.user_priority == expected_priority

    def test_prefix_stripping(self):
        """Test removal of common task creation prefixes."""
        test_cases = [
            ("Create a task to review the document — 10m", "review the document"),
            ("Add task: call john tomorrow — 2m", "call john tomorrow"),
            ("Remind me to buy groceries — P1", "buy groceries"),
            ("I need to finish the report — urgent", "finish the report"),
            ("TODO: update documentation — 30+", "update documentation"),
            ("✓ Complete assignment — normal", "Complete assignment"),
            ("1. Send emails — P2", "Send emails"),
            ("- Schedule meeting — high", "Schedule meeting"),
        ]

        for input_text, expected_content in test_cases:
            result = parse_task_input(input_text)
            assert result.content == expected_content

    def test_time_token_normalization(self):
        """Test various time format inputs normalize correctly."""
        test_cases = [
            ("Task — 2 — P1", "2min"),
            ("Task — 2m — P1", "2min"),
            ("Task — 2min — P1", "2min"),
            ("Task — 10 — P1", "10min"),
            ("Task — 10m — P1", "10min"),
            ("Task — 10min — P1", "10min"),
            ("Task — 30 — P1", "30+min"),
            ("Task — 30+ — P1", "30+min"),
            ("Task — 30m+ — P1", "30+min"),
            ("Task — 30min+ — P1", "30+min"),
        ]

        for input_text, expected_time in test_cases:
            result = parse_task_input(input_text)
            assert result.time_label == expected_time

    def test_priority_word_mapping(self):
        """Test word-based priority detection."""
        test_cases = [
            ("Task — urgent", 1),
            ("Task — critical", 1),
            ("Task — must do today", 1),
            ("Task — high", 2),
            ("Task — today", 2),
            ("Task — tomorrow", 2),
            ("Task — normal", 3),
            ("Task — medium", 3),
            ("Task — regular", 3),
            ("Task — low", 4),
            ("Task — later", 4),
            ("Task — week", 4),
        ]

        for input_text, expected_priority in test_cases:
            result = parse_task_input(input_text)
            assert result.user_priority == expected_priority

    def test_priority_p_format_takes_precedence(self):
        """Test P1-P4 format wins over word conflicts."""
        result = parse_task_input("Task with high priority — P3")

        # Should use P3 (3), not "high" (2)
        assert result.user_priority == 3

    def test_missing_components(self):
        """Test parsing when time or priority is missing."""
        # Only task content
        result = parse_task_input("Just a simple task")
        assert result.content == "Just a simple task"
        assert result.time_label is None
        assert result.user_priority is None

        # Task with time only
        result = parse_task_input("Call doctor — 10m")
        assert result.content == "Call doctor"
        assert result.time_label == "10min"
        assert result.user_priority is None

        # Task with priority only
        result = parse_task_input("Review contract — urgent")
        assert result.content == "Review contract"
        assert result.time_label is None
        assert result.user_priority == 1

    def test_order_independence(self):
        """Test that time and priority can be in any order."""
        # Time first, then priority
        result1 = parse_task_input("Send email — 2m — P1")

        # Priority first, then time
        result2 = parse_task_input("Send email — P1 — 2m")

        assert result1.content == result2.content == "Send email"
        assert result1.time_label == result2.time_label == "2min"
        assert result1.user_priority == result2.user_priority == 1

    def test_case_insensitive_detection(self):
        """Test that detection is case insensitive."""
        result = parse_task_input("Task — 2M — p1")

        assert result.time_label == "2min"
        assert result.user_priority == 1

    def test_complex_task_content(self):
        """Test complex task content with internal separators."""
        result = parse_task_input("Review Q3-Q4 budget analysis — 30m+ — P2")

        assert result.content == "Review Q3-Q4 budget analysis"
        assert result.time_label == "30+min"
        assert result.user_priority == 2

    def test_empty_or_invalid_input(self):
        """Test handling of edge cases."""
        # Empty input
        result = parse_task_input("")
        assert result.content == ""

        # Just separators
        result = parse_task_input("— — —")
        assert result.content == ""

        # Invalid time/priority tokens are ignored
        result = parse_task_input("Task — 5m — P9")
        assert result.content == "Task"
        assert result.time_label is None  # 5m not supported
        assert result.user_priority is None  # P9 not valid

    def test_whitespace_handling(self):
        """Test proper whitespace trimming."""
        result = parse_task_input("  Task with spaces  —  10m  —  P2  ")

        assert result.content == "Task with spaces"
        assert result.time_label == "10min"
        assert result.user_priority == 2
