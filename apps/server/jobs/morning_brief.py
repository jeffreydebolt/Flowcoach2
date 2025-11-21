"""Morning Brief job - sends daily task priorities at 8:30 AM."""

import logging
import os
from datetime import datetime, time

import pytz
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..core.errors import log_event, retry
from ..core.sorting import TaskSorter
from ..db.dal import get_dal
from ..slack.messages import MessageBuilder
from ..todoist.client import TodoistClient

logger = logging.getLogger(__name__)


class MorningBriefJob:
    """Sends morning brief with top 3 prioritized tasks."""

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
    def send_morning_brief(self, user_id: str) -> bool:
        """
        Send morning brief to user.

        Args:
            user_id: Slack user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current weekly outcomes
            outcomes = self.dal.weekly_outcomes.get_current_outcomes(user_id) or []

            # Fetch tasks from Todoist
            tasks = self.todoist.get_tasks()
            if not tasks:
                logger.warning(f"No tasks found for user {user_id}")
                # Send fallback message
                message = self.message_builder.build_fallback_message("no_tasks")
                self.slack.chat_postMessage(channel=user_id, **message)
                return True

            # Sort and select top 3
            top_tasks = TaskSorter.sort_tasks(tasks, outcomes, limit=3)

            # Record surfaced tasks
            self.dal.morning_brief.record_surfaced_tasks(user_id, top_tasks)

            # Build and send message
            message = self.message_builder.build_morning_brief(top_tasks)

            response = self.slack.chat_postMessage(channel=user_id, **message)

            log_event(
                "info",
                "morning_brief_sent",
                {
                    "user_id": user_id,
                    "task_count": len(top_tasks),
                    "task_ids": [t["id"] for t in top_tasks],
                },
            )

            return True

        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            log_event("error", "morning_brief_slack_error", {"user_id": user_id, "error": str(e)})
            return False
        except Exception as e:
            logger.error(f"Failed to send morning brief: {e}")
            log_event("error", "morning_brief_error", {"user_id": user_id, "error": str(e)})
            # Try to send fallback
            try:
                message = self.message_builder.build_fallback_message("general")
                self.slack.chat_postMessage(channel=user_id, **message)
            except:
                pass
            return False

    def should_run_for_user(self, user_id: str, check_time: time | None = None) -> bool:
        """
        Check if job should run for user at current time.

        Args:
            user_id: Slack user ID
            check_time: Time to check (default: 8:30 AM)

        Returns:
            True if job should run
        """
        if check_time is None:
            check_time = time(8, 30)  # 8:30 AM

        user_tz = self.get_user_timezone(user_id)
        now = datetime.now(user_tz)

        # Check if it's the right time (within 5 minute window)
        current_time = now.time()
        time_diff = abs(
            current_time.hour * 60 + current_time.minute - check_time.hour * 60 - check_time.minute
        )

        return time_diff <= 5

    def run_for_all_users(self) -> None:
        """Run morning brief for all active users."""
        # Get list of users from Slack
        try:
            # For now, use a configured list of user IDs from environment
            # In production, this would query active users from database
            user_ids = os.getenv("FC_ACTIVE_USERS", "").split(",")
            user_ids = [uid.strip() for uid in user_ids if uid.strip()]

            if not user_ids:
                logger.warning("No active users configured for morning brief")
                return

            for user_id in user_ids:
                if self.should_run_for_user(user_id):
                    logger.info(f"Sending morning brief to {user_id}")
                    self.send_morning_brief(user_id)

        except Exception as e:
            logger.error(f"Failed to run morning brief job: {e}")
            log_event("error", "morning_brief_job_error", {"error": str(e)})


def main():
    """Entry point for morning brief job."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    job = MorningBriefJob()
    job.run_for_all_users()


if __name__ == "__main__":
    main()
