#!/usr/bin/env python3
"""
Test script for enhanced FlowCoach features.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_agent import TaskAgent
from services.openai_service import OpenAIService
from services.todoist_service import TodoistService
from config import get_config

def test_time_extraction():
    """Test natural language time extraction."""
    agent = TaskAgent(get_config(), {})
    
    test_cases = [
        ("review email this morning - 30 mins +", ("30+min", "review email this morning")),
        ("email Aaron about cash flow questions 2 mins", ("2min", "email Aaron about cash flow questions")),
        ("build cash flow forecast for client a 30 mins plus", ("30+min", "build cash flow forecast for client a")),
        ("quick task to update website (5 min)", ("2min", "quick task to update website")),
        ("review and approve budget - 45 minutes", ("30+min", "review and approve budget")),
        ("send invoice 2m", ("2min", "send invoice")),
        ("long planning session for Q1 strategy", ("30+min", "long planning session for Q1 strategy")),
    ]
    
    print("Testing time extraction...")
    for text, expected in test_cases:
        time_est, cleaned = agent._extract_time_estimate(text)
        print(f"\nInput: '{text}'")
        print(f"Expected: {expected}")
        print(f"Got: ({time_est}, '{cleaned}')")
        print(f"✅ PASS" if (time_est, cleaned) == expected else "❌ FAIL")

def test_project_detection():
    """Test project detection logic."""
    config = get_config()
    openai_service = OpenAIService(config)
    todoist_service = TodoistService(config)
    
    services = {
        "openai": openai_service,
        "todoist": todoist_service
    }
    
    agent = TaskAgent(config, services)
    
    test_cases = [
        ("build cash flow forecast for client", True),
        ("email client about meeting", False),
        ("create new website for company", True),
        ("review spreadsheet", False),
        ("develop marketing strategy for Q1", True),
        ("send weekly report", False),
    ]
    
    print("\n\nTesting project detection...")
    for task, should_be_project in test_cases:
        print(f"\nTask: '{task}'")
        print(f"Should be project: {should_be_project}")
        
        # Simulate task creation with 30+ min estimate
        context = {}
        response = agent._create_task(f"{task} - 30 mins plus", "test_user")
        
        if response.get("response_type") == "project_detected":
            print("✅ Detected as project")
        else:
            print("❌ Not detected as project")

def test_task_breakdown():
    """Test task breakdown generation."""
    config = get_config()
    openai_service = OpenAIService(config)
    
    agent = TaskAgent(config, {"openai": openai_service})
    
    test_tasks = [
        "build cash flow forecast for client",
        "create marketing campaign for new product",
        "redesign company website",
    ]
    
    print("\n\nTesting task breakdown...")
    for task in test_tasks:
        print(f"\nTask: '{task}'")
        subtasks = agent._generate_subtasks(task)
        print("Subtasks:")
        for i, subtask in enumerate(subtasks, 1):
            print(f"  {i}. {subtask}")

def test_full_flow():
    """Test a complete interaction flow."""
    config = get_config()
    openai_service = OpenAIService(config)
    todoist_service = TodoistService(config)
    
    services = {
        "openai": openai_service,
        "todoist": todoist_service
    }
    
    agent = TaskAgent(config, services)
    
    print("\n\nTesting full interaction flow...")
    
    # Test 1: Simple task with time
    print("\n1. Simple task with time estimate:")
    message = {"text": "email Aaron about cash flow questions 2 mins", "user": "test_user"}
    response = agent.process_message(message, {})
    print(f"Response type: {response.get('response_type')}")
    print(f"Task created: {response.get('task_content')}")
    
    # Test 2: Complex task that might be a project
    print("\n2. Complex task (potential project):")
    message = {"text": "build comprehensive financial model for startup - 30 mins +", "user": "test_user"}
    response = agent.process_message(message, {})
    print(f"Response type: {response.get('response_type')}")
    print(f"Message: {response.get('message', '')[:200]}...")

if __name__ == "__main__":
    print("FlowCoach Enhanced Features Test Suite")
    print("=" * 50)
    
    test_time_extraction()
    # Uncomment these to test with real API calls
    # test_project_detection()
    # test_task_breakdown()
    # test_full_flow()
    
    print("\n\nTest suite completed!")