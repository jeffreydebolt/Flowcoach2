#!/usr/bin/env python3
"""Check for phantom tasks in Todoist."""

import os
import sys

sys.path.append(".")

from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from apps.server.integrations.todoist_client import TodoistClient


def check_phantom_tasks():
    """Find phantom tasks that user didn't create."""

    client = TodoistClient()

    # Get all tasks
    tasks = client.get_tasks()

    # Known phantom tasks
    phantom_phrases = ["Let's see how this goes", "Small budgets, only our best sellers"]

    print("Checking for phantom tasks...")
    print("=" * 50)

    found_phantoms = []

    for task in tasks:
        content = task["content"]
        for phantom in phantom_phrases:
            if phantom in content:
                found_phantoms.append(task)
                print(f"\n🚨 FOUND PHANTOM TASK:")
                print(f"   ID: {task['id']}")
                print(f"   Content: {content}")
                print(f"   Created: {task['created_at']}")
                print(f"   Project: {task['project_id']}")
                print(f"   Labels: {task.get('labels', [])}")
                break

    if not found_phantoms:
        print("\n✅ No phantom tasks found in your Todoist!")
        print("Those tasks must have been created another way.")
    else:
        print(f"\n❌ Found {len(found_phantoms)} phantom tasks!")
        print("\nThese were NOT created by FlowCoach and should be deleted.")

        # Check if they have a pattern
        print("\nChecking for patterns...")
        for task in found_phantoms:
            # Check if task has unusual metadata
            if task.get("comment_count", 0) > 0:
                print(f"Task {task['id']} has comments - might be from another app")
            if task.get("description"):
                print(f"Task {task['id']} has description: {task['description']}")

    # Also check recently created tasks
    print("\n\nRecent tasks (last 10):")
    sorted_tasks = sorted(tasks, key=lambda x: x["created_at"], reverse=True)[:10]
    for task in sorted_tasks:
        print(f"- {task['content'][:50]}... (created: {task['created_at']})")


if __name__ == "__main__":
    check_phantom_tasks()
