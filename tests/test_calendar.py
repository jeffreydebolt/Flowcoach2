"""
Test script for FlowCoach Calendar service.

This script tests the Calendar service functionality.
"""

import logging
import os
import sys
from datetime import datetime

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


def test_calendar_service():
    """Test Calendar service functionality."""
    logger.info("Testing Calendar service...")

    try:
        from config import get_config
        from services.calendar_service import CalendarService

        # Get config
        config = get_config()

        # Initialize service
        calendar_service = CalendarService(config["calendar"])

        # Check if service initialized (requires credentials)
        if not calendar_service._calendar_service:
            logger.warning(
                "Google Calendar service not initialized (likely missing credentials). Skipping API tests."
            )
            return None

        # Test getting events (requires valid credentials)
        logger.info("Testing get_events...")
        today = datetime.now().date()
        start_datetime = datetime.combine(today, datetime.min.time())
        end_datetime = datetime.combine(today, datetime.max.time())
        events = calendar_service.get_events("test_user", start_datetime, end_datetime)
        logger.info(f"Found {len(events)} events for today")

        # Test finding focus blocks (requires valid credentials)
        logger.info("Testing find_focus_blocks...")
        focus_blocks = calendar_service.find_focus_blocks("test_user")
        logger.info(f"Found {len(focus_blocks)} focus blocks for today")

        logger.info("Calendar service test passed!")
        return True
    except Exception as e:
        logger.error(f"Calendar service test failed: {e}")
        return False


if __name__ == "__main__":
    test_calendar_service()
