#!/usr/bin/env python3
"""Test just the GTD formatting without any APIs."""

import sys

sys.path.append(".")

from core.gtd_protection import gtd_protector

# Your exact example
test_task = "do cash flow fore museminded"
print(f"Original: '{test_task}'")

# Apply spelling correction
corrected = gtd_protector.apply_spelling_corrections(test_task)
print(f"Spelling corrected: '{corrected}'")

# Apply GTD formatting
formatted = gtd_protector.format_with_gtd_fallback(test_task)
print(f"GTD formatted: '{formatted}'")

# Test protection system (simulating AI failure)
protected = gtd_protector.protect_gtd_format(test_task, None)
print(f"Protected format: '{protected}'")

print("\n" + "=" * 50)
print("THIS IS WHAT YOUR TASK WOULD LOOK LIKE:")
print(f"'{protected}'")
print("=" * 50)

# Test the typo specifically
print("\nTypo test:")
print(f"'fore' -> '{gtd_protector.apply_spelling_corrections('fore')}'")
print("(Note: 'fore' is actually a real word meaning 'front', so it's not corrected)")
print("If you meant 'for', you need to add that to the corrections list")
