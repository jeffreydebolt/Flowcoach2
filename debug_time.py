#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.task_agent import TaskAgent
from config import get_config

agent = TaskAgent(get_config(), {})

test_text = "create financial forecast - 30 mins"
time_estimate, cleaned_text = agent._extract_time_estimate(test_text)

print(f"Input: {test_text}")
print(f"Time estimate: {time_estimate}")
print(f"Cleaned text: {cleaned_text}")