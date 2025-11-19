#!/usr/bin/env python3

import os
import sys

sys.path.append(".")

# Bootstrap environment
from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from apps.server.integrations.todoist_client import TodoistClient
from apps.server.core.planning import PlanningService
from datetime import date


def test_morning_brief_logic():
    """Test Morning Brief logic directly without Slack."""

    print("=== Testing Morning Brief Logic ===\n")

    # Initialize services
    todoist_client = TodoistClient()
    planning_service = PlanningService(todoist_client)

    # Test the actual morning brief logic
    user_id = "test_user"

    print("1. Getting morning brief tasks...")
    tasks = planning_service.get_morning_brief_tasks(user_id)

    print(f"\n2. Found {len(tasks)} tasks for Morning Brief")

    if tasks:
        print("\n3. Task details:")
        for i, task in enumerate(tasks):
            print(f"\n   Task {i+1}:")
            print(f"   - Content: {task.content}")
            print(f"   - ID: {task.id}")
            print(f"   - Project: {task.project_name}")
            print(f"   - Priority: {task.priority} (is_p1: {task.is_priority_1})")
            print(f"   - Labels: {task.labels}")
            print(
                f"   - Flags: overdue={task.is_overdue}, tomorrow={task.is_flow_tomorrow}, weekly={task.is_flow_weekly}"
            )
    else:
        print("\n3. NO TASKS FOUND - This explains the 'All Clear' message!")

        # Let's debug why
        print("\n4. Debugging task retrieval...")

        # Get all tasks directly
        all_tasks = todoist_client.get_tasks()
        print(f"   - Total tasks in Todoist: {len(all_tasks)}")

        # Check P1 tasks
        p1_tasks = [t for t in all_tasks if t.get("priority") == 4]
        print(f"   - P1 tasks (priority=4): {len(p1_tasks)}")

        if p1_tasks:
            print("\n5. P1 tasks exist but aren't being returned by get_morning_brief_tasks!")
            print("   This indicates a bug in the TaskSelector._evaluate_task method")

            # Check the first P1 task
            sample_task = p1_tasks[0]
            print(f"\n   Sample P1 task:")
            print(f"   - Content: {sample_task['content']}")
            print(f"   - Priority: {sample_task.get('priority')}")
            print(f"   - Labels: {sample_task.get('labels', [])}")


if __name__ == "__main__":
    test_morning_brief_logic()
