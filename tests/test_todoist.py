"""
Test script for FlowCoach Todoist service.

This script tests the Todoist service functionality.
"""

import os
import logging
import sys
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def test_todoist_service():
    """Test Todoist service functionality."""
    logger.info("Testing Todoist service...")
    
    try:
        from services.todoist_service import TodoistService
        
        # Get API token from environment
        api_token = os.environ.get("TODOIST_API_TOKEN")
        if not api_token:
            logger.warning("TODOIST_API_TOKEN not found in environment. Skipping Todoist service test.")
            return None
        
        # Initialize service
        todoist_service = TodoistService(api_token)
        
        # Test getting projects
        projects = todoist_service.get_projects()
        logger.info(f"Found {len(projects)} projects")
        
        # Test getting labels
        labels = todoist_service.get_labels()
        logger.info(f"Found {len(labels)} labels")
        
        # Test getting tasks
        tasks = todoist_service.get_tasks()
        logger.info(f"Found {len(tasks)} tasks")
        
        # Test GTD processing
        test_task = "Test task from FlowCoach"
        processed_task = todoist_service.add_task_with_gtd_processing(test_task)
        logger.info(f"Created task with GTD processing: {processed_task['content']}")
        
        # Test time estimate extraction
        time_estimate = todoist_service._extract_time_estimate("Quick task 2min")
        assert time_estimate == "2min", f"Expected '2min', got '{time_estimate}'"
        
        logger.info("Todoist service test passed!")
        return True
    except Exception as e:
        logger.error(f"Todoist service test failed: {e}")
        return False

if __name__ == "__main__":
    test_todoist_service()
