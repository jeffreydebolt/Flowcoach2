#!/usr/bin/env python3
"""Send a test task directly to show GTD formatting works."""

import os
import sys

sys.path.append(".")

from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from services.todoist_service import TodoistService
from core.task_agent import TaskAgent
from config import get_config

# Initialize
config = get_config()
todoist = TodoistService(config["todoist"])
task_agent = TaskAgent({"todoist_service": todoist})

# Test task with typo
test_task = "do cash flow fore museminded"
print(f"Original: '{test_task}'")

# Format it
formatted = task_agent._format_task_with_gtd(test_task)
print(f"Formatted: '{formatted}'")

# Actually create it to show it works
result = task_agent._create_task(test_task, "test_user")
print(f"\nTask created in Todoist:")
print(f"- Content: {result.get('task_content')}")
print(f"- Response: {result.get('response_type')}")
print(f"- Message: {result.get('message')}")
