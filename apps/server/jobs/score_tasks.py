"""CLI tool to trigger deep work task scoring."""

import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.server.core.errors import log_event
from apps.server.core.scheduler import DeepWorkScheduler

logger = logging.getLogger(__name__)


def main():
    """Process and score deep work tasks."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info("Starting deep work task scoring...")

    try:
        scheduler = DeepWorkScheduler()

        # Process new tasks (will prompt users if configured)
        user_id = os.getenv("FC_DEFAULT_USER")  # Optional default user for prompts
        scheduler.process_new_tasks(user_id)

        # Batch process any unscored tasks
        results = scheduler.batch_process_unscored_tasks()

        logger.info(f"Scoring complete: {results}")
        log_event("info", "deep_work_scoring_complete", results)

    except Exception as e:
        logger.error(f"Failed to score tasks: {e}")
        log_event("error", "deep_work_scoring_failed", {"error": str(e)})
        sys.exit(1)


if __name__ == "__main__":
    main()
