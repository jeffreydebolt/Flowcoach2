"""Nightly job to decay momentum for idle projects."""

import logging
from datetime import datetime

from ..core.errors import log_event
from ..core.momentum import MomentumTracker

logger = logging.getLogger(__name__)


class MomentumDecayJob:
    """Nightly job to decay project momentum."""

    def __init__(self):
        self.tracker = MomentumTracker()

    def run(self) -> bool:
        """
        Run momentum decay job.

        Returns:
            True if job completed successfully
        """
        try:
            logger.info("Starting momentum decay job")

            # Decay momentum for projects idle > 1 day
            updated_count = self.tracker.decay_project_momentum(days_threshold=1)

            # Log results
            log_event(
                severity="info",
                action="momentum_decay_completed",
                payload={
                    "projects_updated": updated_count,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(f"Momentum decay completed: {updated_count} projects updated")
            return True

        except Exception as e:
            logger.error(f"Momentum decay job failed: {e}")

            log_event(
                severity="error",
                action="momentum_decay_failed",
                payload={"error": str(e), "timestamp": datetime.now().isoformat()},
            )

            return False


def run_momentum_decay_job() -> bool:
    """Entry point for momentum decay job."""
    job = MomentumDecayJob()
    return job.run()


def main():
    """Entry point for momentum decay job."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run the job
    success = run_momentum_decay_job()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
