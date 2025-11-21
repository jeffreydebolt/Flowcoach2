"""Weekly Outcomes job - prompts for weekly goals on Monday mornings."""

import logging
import os
from datetime import datetime, time

import pytz
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..core.errors import log_event, retry
from ..db.dal import get_dal
from ..slack.messages import MessageBuilder

logger = logging.getLogger(__name__)


class WeeklyOutcomesJob:
    """Prompts users for weekly outcomes on Monday mornings."""

    def __init__(self):
        self.slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not self.slack_token:
            raise ValueError("SLACK_BOT_TOKEN not found in environment")

        self.slack = WebClient(token=self.slack_token)
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
    def send_weekly_prompt(self, user_id: str) -> bool:
        """
        Send weekly outcomes prompt to user.

        Args:
            user_id: Slack user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if outcomes already set this week
            existing_outcomes = self.dal.weekly_outcomes.get_current_outcomes(user_id)
            if existing_outcomes:
                logger.info(f"User {user_id} already has outcomes for this week")
                return True

            # Build and send prompt
            message = self.message_builder.build_weekly_outcomes_prompt()

            response = self.slack.chat_postMessage(channel=user_id, **message)

            log_event(
                "info",
                "weekly_outcomes_prompt_sent",
                {"user_id": user_id, "message_ts": response["ts"]},
            )

            return True

        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            log_event("error", "weekly_prompt_slack_error", {"user_id": user_id, "error": str(e)})
            return False
        except Exception as e:
            logger.error(f"Failed to send weekly prompt: {e}")
            log_event("error", "weekly_prompt_error", {"user_id": user_id, "error": str(e)})
            return False

    def should_run_for_user(self, user_id: str, check_time: time | None = None) -> bool:
        """
        Check if job should run for user at current time.

        Args:
            user_id: Slack user ID
            check_time: Time to check (default: 9:00 AM)

        Returns:
            True if job should run (Monday at specified time)
        """
        if check_time is None:
            check_time = time(9, 0)  # 9:00 AM

        user_tz = self.get_user_timezone(user_id)
        now = datetime.now(user_tz)

        # Check if it's Monday
        if now.weekday() != 0:  # 0 = Monday
            return False

        # Check if it's the right time (within 5 minute window)
        current_time = now.time()
        time_diff = abs(
            current_time.hour * 60 + current_time.minute - check_time.hour * 60 - check_time.minute
        )

        return time_diff <= 5

    def run_for_all_users(self) -> None:
        """Run weekly outcomes prompt for all active users."""
        try:
            # Get list of users from environment
            user_ids = os.getenv("FC_ACTIVE_USERS", "").split(",")
            user_ids = [uid.strip() for uid in user_ids if uid.strip()]

            if not user_ids:
                logger.warning("No active users configured for weekly outcomes")
                return

            for user_id in user_ids:
                if self.should_run_for_user(user_id):
                    logger.info(f"Sending weekly outcomes prompt to {user_id}")
                    self.send_weekly_prompt(user_id)

        except Exception as e:
            logger.error(f"Failed to run weekly outcomes job: {e}")
            log_event("error", "weekly_outcomes_job_error", {"error": str(e)})


def main():
    """Entry point for weekly outcomes job."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    job = WeeklyOutcomesJob()
    job.run_for_all_users()


if __name__ == "__main__":
    main()
