"""Services package for FlowCoach.

This package contains modules for interacting with external services like Todoist, Google Calendar, and OpenAI,
and initializes the core agents.
"""

import logging

from .todoist_service import TodoistService
from .calendar_service import CalendarService
from .openai_service import OpenAIService
from .claude_service import ClaudeService
from core.task_agent import TaskAgent
from core.calendar_agent import CalendarAgent
from core.communication_agent import CommunicationAgent

logger = logging.getLogger(__name__)


def initialize_services(config):
    """Initialize all services and agents based on configuration."""
    services = {}

    # Initialize Services
    if config["todoist"]["api_token"]:
        try:
            services["todoist"] = TodoistService(config["todoist"]["api_token"])
        except Exception as e:
            logger.error(f"Error initializing Todoist service: {e}")
    else:
        logger.warning("Todoist API token not found. Todoist service not initialized.")

    try:
        services["calendar"] = CalendarService(config["calendar"])
    except Exception as e:
        logger.error(f"Error initializing Calendar service: {e}")

    if config["openai"]["api_key"]:
        try:
            services["openai"] = OpenAIService(config["openai"])
        except Exception as e:
            logger.error(f"Error initializing OpenAI service: {e}")
    else:
        logger.warning("OpenAI API key not found. OpenAI service not initialized.")

    if config["claude"]["api_key"]:
        try:
            services["claude"] = ClaudeService(config["claude"])
        except Exception as e:
            logger.error(f"Error initializing Claude service: {e}")
    else:
        logger.warning("Claude API key not found. Claude service not initialized.")

    # Initialize Agents
    agents = {}
    try:
        agents["task"] = TaskAgent(config, services)
    except Exception as e:
        logger.error(f"Error initializing Task Agent: {e}")

    try:
        agents["calendar"] = CalendarAgent(config, services)
    except Exception as e:
        logger.error(f"Error initializing Calendar Agent: {e}")

    try:
        agents["communication"] = CommunicationAgent(config, services)
    except Exception as e:
        logger.error(f"Error initializing Communication Agent: {e}")

    # Add agents to the services dictionary
    services["agents"] = agents

    return services


__all__ = [
    "initialize_services",
    "TodoistService",
    "CalendarService",
    "OpenAIService",
    "ClaudeService",
]
