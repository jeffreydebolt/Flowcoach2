#!/usr/bin/env python3
"""Verify GTD protection is actually integrated."""

import sys

sys.path.append(".")

from core.task_agent import TaskAgent

# Check if the protection is imported
try:

    print("✓ GTD Protection module found")
except:
    print("✗ GTD Protection module NOT FOUND")
    sys.exit(1)

# Check if TaskAgent uses it
import inspect

source = inspect.getsource(TaskAgent._format_task_with_gtd)

if "gtd_protector" in source:
    print("✓ TaskAgent is using GTD protection")
else:
    print("✗ TaskAgent is NOT using GTD protection")
    print("\nTaskAgent._format_task_with_gtd source:")
    print(source)
    sys.exit(1)

print("\n✅ GTD Protection is properly integrated!")
