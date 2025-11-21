"""Evening Wrap job - sends daily recap at 6:00 PM."""

import logging
import os
from datetime import datetime, time

import pytz
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..core.errors import log_event, retry
from ..db.dal import get_dal
from ..slack.messages import MessageBuilder
from ..todoist.client import TodoistClient

logger = logging.getLogger(__name__)


class EveningWrapJob:
    """Sends evening wrap-up with task status."""

    def __init__(self):
        self.slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not self.slack_token:
            raise ValueError("SLACK_BOT_TOKEN not found in environment")

        self.slack = WebClient(token=self.slack_token)
        self.todoist = TodoistClient()
        self.message_builder = MessageBuilder()
        self.dal = get_dal()

        # Default timezone
        self.default_tz = pytz.timezone(os.getenv("FC_DEFAULT_TIMEZONE", "America/Denver"))

    def get_user_timezone(self, user_id: str) -> pytz.timezone:
        """Get user's timezone from Slack profile or use default."""
        try:
            response = self.slack.users_info(user=user_id)
            tz_string = response["user"].get("tz", "America/Denver")
            return pytz.timezone(tz_string)
        except Exception as e:
            logger.warning(f"Failed to get user timezone: {e}")
            return self.default_tz

    @retry(max_attempts=3)
    def send_evening_wrap(self, user_id: str) -> bool:
        """
        Send evening wrap to user.

        Args:
            user_id: Slack user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get tasks that were surfaced in morning brief
            surfaced_tasks = self.dal.morning_brief.get_today_tasks(user_id)

            if not surfaced_tasks:
                logger.info(f"No tasks were surfaced today for user {user_id}")
                return True

            # Get completed task IDs from Todoist
            completed_ids = self._get_completed_task_ids([t["task_id"] for t in surfaced_tasks])

            # Update local status
            for task_id in completed_ids:
                self.dal.morning_brief.update_task_status(task_id, "completed")

            # Build and send message
            message = self.message_builder.build_evening_wrap(surfaced_tasks, completed_ids)

            response = self.slack.chat_postMessage(channel=user_id, **message)

            log_event(
                "info",
                "evening_wrap_sent",
                {
                    "user_id": user_id,
                    "surfaced_count": len(surfaced_tasks),
                    "completed_count": len(completed_ids),
                },
            )

            # Log to events table
            self.dal.events.log_event(
                severity="info",
                action="evening_wrap",
                payload={
                    "surfaced_tasks": [t["task_id"] for t in surfaced_tasks],
                    "completed_tasks": completed_ids,
                },
                user_id=user_id,
            )

            return True

        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            log_event("error", "evening_wrap_slack_error", {"user_id": user_id, "error": str(e)})
            return False
        except Exception as e:
            logger.error(f"Failed to send evening wrap: {e}")
            log_event("error", "evening_wrap_error", {"user_id": user_id, "error": str(e)})
            return False

    def _get_completed_task_ids(self, task_ids: list[str]) -> list[str]:
        """Check which tasks have been completed in Todoist."""
        completed = []

        for task_id in task_ids:
            try:
                # Try to fetch the task - completed tasks will throw an error
                task = self.todoist.api.get_task(task_id)
                # If we can fetch it, it's not completed
            except:
                # Task not found or completed
                completed.append(task_id)

        return completed

    def should_run_for_user(self, user_id: str, check_time: time | None = None) -> bool:
        """
        Check if job should run for user at current time.

        Args:
            user_id: Slack user ID
            check_time: Time to check (default: 6:00 PM)

        Returns:
            True if job should run
        """
        if check_time is None:
            check_time = time(18, 0)  # 6:00 PM

        user_tz = self.get_user_timezone(user_id)
        now = datetime.now(user_tz)

        # Check if it's the right time (within 5 minute window)
        current_time = now.time()
        time_diff = abs(
            current_time.hour * 60 + current_time.minute - check_time.hour * 60 - check_time.minute
        )

        return time_diff <= 5

    def run_for_all_users(self) -> None:
        """Run evening wrap for all active users."""
        try:
            # Get list of users from environment
            user_ids = os.getenv("FC_ACTIVE_USERS", "").split(",")
            user_ids = [uid.strip() for uid in user_ids if uid.strip()]

            if not user_ids:
                logger.warning("No active users configured for evening wrap")
                return

            for user_id in user_ids:
                if self.should_run_for_user(user_id):
                    logger.info(f"Sending evening wrap to {user_id}")
                    self.send_evening_wrap(user_id)

        except Exception as e:
            logger.error(f"Failed to run evening wrap job: {e}")
            log_event("error", "evening_wrap_job_error", {"error": str(e)})


def main():
    """Entry point for evening wrap job."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    job = EveningWrapJob()
    job.run_for_all_users()


if __name__ == "__main__":
    main()
