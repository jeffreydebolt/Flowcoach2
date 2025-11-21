"""
Test script for FlowCoach.

This script tests the basic functionality of the FlowCoach application.
"""

import logging
import os
import sys

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


def test_config():
    """Test configuration loading."""
    logger.info("Testing configuration...")

    try:
        from config import get_config

        config = get_config()

        # Check essential config values
        assert "slack" in config, "Slack configuration missing"
        assert "todoist" in config, "Todoist configuration missing"
        assert "openai" in config, "OpenAI configuration missing"
        assert "calendar" in config, "Calendar configuration missing"
        assert "agents" in config, "Agents configuration missing"

        logger.info("Configuration test passed!")
        return True
    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return False


def test_services():
    """Test service initialization."""
    logger.info("Testing services...")

    try:
        from config import get_config
        from services import initialize_services

        config = get_config()
        services = initialize_services(config)

        # Check if services were initialized
        # Note: This will only check if the services dictionary was created,
        # not if the services themselves are working properly
        assert isinstance(services, dict), "Services should be a dictionary"

        logger.info("Services test passed!")
        return True
    except Exception as e:
        logger.error(f"Services test failed: {e}")
        return False


def test_agents():
    """Test agent initialization."""
    logger.info("Testing agents...")

    try:
        from config import get_config
        from core.calendar_agent import CalendarAgent
        from core.communication_agent import CommunicationAgent
        from core.task_agent import TaskAgent
        from services import initialize_services

        config = get_config()
        services = initialize_services(config)

        # Initialize agents
        task_agent = TaskAgent(config, services)
        calendar_agent = CalendarAgent(config, services)
        communication_agent = CommunicationAgent(config, services)

        # Test agent capabilities
        assert task_agent.get_capabilities(), "Task agent should have capabilities"
        assert calendar_agent.get_capabilities(), "Calendar agent should have capabilities"
        assert (
            communication_agent.get_capabilities()
        ), "Communication agent should have capabilities"

        logger.info("Agents test passed!")
        return True
    except Exception as e:
        logger.error(f"Agents test failed: {e}")
        return False


def test_handlers():
    """Test handler registration."""
    logger.info("Testing handlers...")

    try:
        from slack_bolt import App

        from config import get_config
        from handlers import register_handlers
        from services import initialize_services

        # Create mock app
        app = App(token="xoxb-mock-token")

        # Initialize services
        config = get_config()
        services = initialize_services(config)

        # Register handlers
        register_handlers(app, services)

        logger.info("Handlers test passed!")
        return True
    except Exception as e:
        logger.error(f"Handlers test failed: {e}")
        return False


def run_tests():
    """Run all tests."""
    logger.info("Starting FlowCoach tests...")

    tests = [test_config, test_services, test_agents, test_handlers]

    results = []
    for test in tests:
        results.append(test())

    # Print summary
    logger.info("Test Summary:")
    for i, result in enumerate(results):
        logger.info(f"  Test {i+1}: {'PASSED' if result else 'FAILED'}")

    if all(results):
        logger.info("All tests passed!")
        return True
    else:
        logger.error("Some tests failed!")
        return False


if __name__ == "__main__":
    run_tests()
