#!/usr/bin/env python3
"""
Temporary workaround script to show Morning Brief tasks.
Since Socket Mode is having issues, this directly displays the tasks.
"""

import os
import sys

sys.path.append(".")

from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from slack_sdk import WebClient

from apps.server.core.planning import PlanningService
from apps.server.integrations.todoist_client import TodoistClient


def send_morning_brief_message(user_id):
    """Send Morning Brief as a message instead of modal."""

    # Initialize services
    todoist_client = TodoistClient()
    planning_service = PlanningService(todoist_client)
    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

    # Get tasks
    tasks = planning_service.get_morning_brief_tasks(user_id)

    if not tasks:
        message = "*🌅 Morning Brief*\n\n🎉 All Clear! No tasks need planning right now."
    else:
        message = f"*🌅 Morning Brief*\n\nYou have {len(tasks)} tasks to plan:\n\n"

        for i, task in enumerate(tasks, 1):
            priority_emoji = "🔴" if task.is_priority_1 else "🟡"
            message += f"{i}. {priority_emoji} *{task.content}*\n"

            if task.project_name != "Inbox":
                message += f"   📁 {task.project_name}\n"

            if task.labels:
                message += f"   🏷️ {', '.join(task.labels)}\n"

            message += "\n"

    # Send message
    try:
        client.chat_postMessage(
            channel=user_id,
            text=message,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": message}}],
        )
        print(f"✓ Sent Morning Brief to user {user_id}")
    except Exception as e:
        print(f"✗ Failed to send message: {e}")


if __name__ == "__main__":
    # Get user ID from command line or use default
    user_id = sys.argv[1] if len(sys.argv) > 1 else "U08GT1JD5CZ"  # Your Slack user ID
    send_morning_brief_message(user_id)
