#!/usr/bin/env python3
"""Test task extraction logic"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_agent import TaskAgent
from config import get_config

# Create a minimal task agent for testing
agent = TaskAgent(get_config(), {})

# Test with Jeff's exact message
test_message = """here are a few thinsg i need to do today: 1) gather all of cathryn's tax docs and review (30 mins) 2) review all of ryan's tax docs and email Mohammed (10 mins) 3) prepare a R&D credit quesitonaire for ryan 10 mins 4) do cashflow forecaast update for last week for LL medico 10 mins"""

print("Testing task extraction...")
print(f"Input message: {test_message}")
print("-" * 50)

import re

# Test the single line pattern
single_line_pattern = r'\d+\)\s*([^0-9]+?)(?=\d+\)|$)'
matches = re.findall(single_line_pattern, test_message, re.IGNORECASE)
print(f"Regex matches: {matches}")
print(f"Number of matches: {len(matches)}")

tasks = agent._extract_tasks_from_message(test_message)
print(f"\nNumber of tasks extracted: {len(tasks)}")
print("\nExtracted tasks:")
for i, task in enumerate(tasks, 1):
    print(f"{i}. {task}")