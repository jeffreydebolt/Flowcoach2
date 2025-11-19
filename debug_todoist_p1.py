#!/usr/bin/env python3

import os
import sys

sys.path.append(".")

from apps.server.integrations.todoist_client import TodoistClient


def debug_p1_tasks():
    """Debug P1 tasks to understand why Morning Brief shows All Clear."""

    client = TodoistClient()

    print("=== Debug P1 Tasks ===")

    # Get all tasks
    tasks = client.get_tasks()
    print(f"Total tasks found: {len(tasks)}")

    # Check for P1 tasks
    p1_tasks = [task for task in tasks if task.get("priority") == 4]
    print(f"P1 tasks (priority=4): {len(p1_tasks)}")

    # Show all task priorities
    priority_counts = {}
    for task in tasks:
        priority = task.get("priority", 1)
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    print("\nPriority distribution:")
    for priority in sorted(priority_counts.keys(), reverse=True):
        count = priority_counts[priority]
        human_priority = 5 - priority  # Convert to human P1-P4
        print(f"  Priority {priority} (P{human_priority}): {count} tasks")

    print("\nP1 task details:")
    for i, task in enumerate(p1_tasks):
        print(f"  {i+1}. {task['content']} (ID: {task['id']})")
        print(f"     Priority: {task['priority']}, Labels: {task.get('labels', [])}")
        print(f"     Due: {task.get('due')}")
        print()

    print("=== Morning Brief Logic Test ===")
    from datetime import date

    today = date.today()

    qualifying_tasks = []
    for task in tasks:
        labels = [label.lower() for label in task.get("labels", [])]

        # Check inclusion criteria
        has_flow_tomorrow = any(label in ["@flow_tomorrow", "flow_tomorrow"] for label in labels)
        has_flow_weekly = any(label in ["@flow_weekly", "flow_weekly"] for label in labels)
        is_priority_1 = task.get("priority") == 4

        # Simple overdue check (assuming no due dates for now)
        is_overdue = False
        due = task.get("due")
        if due:
            print(f"Task with due date: {task['content']} - Due: {due}")

        should_include = has_flow_tomorrow or is_overdue or is_priority_1

        if should_include:
            qualifying_tasks.append(
                {
                    "content": task["content"],
                    "is_p1": is_priority_1,
                    "has_flow_tomorrow": has_flow_tomorrow,
                    "has_flow_weekly": has_flow_weekly,
                    "is_overdue": is_overdue,
                }
            )

    print(f"\nTasks qualifying for Morning Brief: {len(qualifying_tasks)}")
    for i, task in enumerate(qualifying_tasks):
        reasons = []
        if task["is_p1"]:
            reasons.append("P1")
        if task["has_flow_tomorrow"]:
            reasons.append("@flow_tomorrow")
        if task["has_flow_weekly"]:
            reasons.append("@flow_weekly")
        if task["is_overdue"]:
            reasons.append("Overdue")

        print(f"  {i+1}. {task['content']} ({', '.join(reasons)})")


if __name__ == "__main__":
    debug_p1_tasks()
