"""
Configuration module for FlowCoach.

This module centralizes all configuration settings for the application,
including API keys, feature flags, and application settings.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys and Tokens
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
TODOIST_API_TOKEN = os.environ.get("TODOIST_API_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

# Application Settings
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
DEBUG_MODE = os.environ.get("DEBUG_MODE", "False").lower() == "true"

# GTD Settings
DEFAULT_GTD_PROJECT = os.environ.get("DEFAULT_GTD_PROJECT", "Inbox")
TIME_ESTIMATE_LABELS = {"2min": "2min", "10min": "10min", "30+min": "30+min"}

# Calendar Settings
WORK_START_HOUR = int(os.environ.get("WORK_START_HOUR", "9"))
WORK_END_HOUR = int(os.environ.get("WORK_END_HOUR", "17"))
MIN_FOCUS_BLOCK_MINUTES = int(os.environ.get("MIN_FOCUS_BLOCK_MINUTES", "30"))

# OpenAI Settings
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4")
OPENAI_TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))

# Claude Settings
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
CLAUDE_TEMPERATURE = float(os.environ.get("CLAUDE_TEMPERATURE", "0.7"))

# Agent Settings
AGENTS = {
    "task": {"enabled": True, "description": "Manages tasks and GTD workflow"},
    "calendar": {"enabled": True, "description": "Handles calendar integration and scheduling"},
    "communication": {"enabled": True, "description": "Manages user interactions and messaging"},
}

# Feature Flags
FEATURES = {
    "task_breakdown": True,
    "calendar_prioritization": True,
    "delegation_suggestions": True,
    "email_integration": False,  # Planned for future
}


def get_config() -> Dict[str, Any]:
    """
    Get the complete configuration dictionary.

    Returns:
        Dict[str, Any]: Complete configuration dictionary
    """
    return {
        "slack": {"bot_token": SLACK_BOT_TOKEN, "app_token": SLACK_APP_TOKEN},
        "todoist": {"api_token": TODOIST_API_TOKEN},
        "openai": {
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_MODEL,
            "temperature": OPENAI_TEMPERATURE,
        },
        "claude": {
            "api_key": CLAUDE_API_KEY,
            "model": CLAUDE_MODEL,
            "temperature": CLAUDE_TEMPERATURE,
        },
        "app": {"log_level": LOG_LEVEL, "debug_mode": DEBUG_MODE},
        "gtd": {
            "default_project": DEFAULT_GTD_PROJECT,
            "time_estimate_labels": TIME_ESTIMATE_LABELS,
        },
        "calendar": {
            "work_start_hour": WORK_START_HOUR,
            "work_end_hour": WORK_END_HOUR,
            "min_focus_block_minutes": MIN_FOCUS_BLOCK_MINUTES,
        },
        "agents": AGENTS,
        "features": FEATURES,
    }


def get_agent_config(agent_name: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Optional[Dict[str, Any]]: Agent configuration or None if not found
    """
    return AGENTS.get(agent_name)


def is_feature_enabled(feature_name: str) -> bool:
    """
    Check if a feature is enabled.

    Args:
        feature_name: Name of the feature

    Returns:
        bool: True if feature is enabled, False otherwise
    """
    return FEATURES.get(feature_name, False)
