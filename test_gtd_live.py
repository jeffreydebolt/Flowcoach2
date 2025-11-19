#!/usr/bin/env python3
"""Test GTD formatting with actual TaskAgent."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Bootstrap environment
from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from config import get_config
from services import initialize_services


def test_task_creation():
    """Test task creation with GTD formatting."""

    # Initialize services
    config = get_config()
    services = initialize_services(config)

    # Get task agent
    task_agent = services["agents"]["task"]

    # Test cases
    test_inputs = [
        "do cash flow for best self",
        "hte sink needs fixing",
        "task to follow up with hanna friday",
    ]

    print("Testing GTD formatting with TaskAgent...")
    print("=" * 50)

    for task_text in test_inputs:
        print(f"\nInput: '{task_text}'")

        # Test formatting directly
        formatted = task_agent._format_task_with_gtd(task_text)
        print(f"Formatted: '{formatted}'")

        # Test full task creation flow (without actually creating in Todoist)
        from apps.server.nlp.parser import parse_task_input

        parsed = parse_task_input(task_text)
        print(f"Parsed content: '{parsed.content}'")

        formatted_from_parsed = task_agent._format_task_with_gtd(parsed.content)
        print(f"Final format: '{formatted_from_parsed}'")


if __name__ == "__main__":
    test_task_creation()
