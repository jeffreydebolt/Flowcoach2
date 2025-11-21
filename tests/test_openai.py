"""
Test script for FlowCoach OpenAI service.

This script tests the OpenAI service functionality.
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


def test_openai_service():
    """Test OpenAI service functionality."""
    logger.info("Testing OpenAI service...")

    try:
        from services.openai_service import OpenAIService

        # Get API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment. Skipping OpenAI service test.")
            return None

        # Initialize service
        openai_service = OpenAIService({"api_key": api_key, "model": "gpt-4", "temperature": 0.7})

        # Test generating text
        logger.info("Testing generate_text...")
        prompt = "What are the key principles of GTD (Getting Things Done)?"
        response = openai_service.generate_text(prompt, max_tokens=200)
        logger.info(f"Generated response of length: {len(response)}")

        # Test formatting task with GTD
        logger.info("Testing format_task_with_gtd...")
        task_text = "need to finish the project report"
        formatted_task = openai_service.format_task_with_gtd(task_text)
        logger.info(f"Formatted task: {formatted_task}")

        # Test generating subtasks
        logger.info("Testing generate_subtasks...")
        complex_task = "Redesign the company website"
        subtasks = openai_service.generate_subtasks(complex_task, num_subtasks=3)
        logger.info(f"Generated {len(subtasks)} subtasks")

        logger.info("OpenAI service test passed!")
        return True
    except Exception as e:
        logger.error(f"OpenAI service test failed: {e}")
        return False


if __name__ == "__main__":
    test_openai_service()
