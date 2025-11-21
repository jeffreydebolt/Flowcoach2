#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_config
from core.task_agent import TaskAgent

agent = TaskAgent(get_config(), {})

test_text = "create financial forecast - 30 mins"
time_estimate, cleaned_text = agent._extract_time_estimate(test_text)

print(f"Input: {test_text}")
print(f"Time estimate: {time_estimate}")
print(f"Cleaned text: {cleaned_text}")
