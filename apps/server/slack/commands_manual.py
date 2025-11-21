"""Slack commands for manually triggering scheduled jobs."""

import logging

from slack_bolt import App
from slack_sdk import WebClient

from ..core.errors import log_event
from ..core.feature_flags import FeatureFlag, is_feature_enabled
from ..jobs.evening_wrap import EveningWrapJob
from ..jobs.morning_brief import MorningBriefJob
from ..jobs.weekly_outcomes import WeeklyOutcomesJob

logger = logging.getLogger(__name__)


class ManualCommandHandler:
    """Handles manual trigger slash commands."""

    def __init__(self):
        self.morning_brief = MorningBriefJob()
        self.evening_wrap = EveningWrapJob()
        self.weekly_outcomes = WeeklyOutcomesJob()

    def handle_brief_command(self, ack, command, client: WebClient):
        """Handle /flow brief and /brief slash commands."""
        ack()

        # Handle /brief command

        try:
            user_id = command["user_id"]

            logger.info(f"Processing manual brief command from user {user_id}")

            # Check if Slack commands feature is enabled
            if not is_feature_enabled(FeatureFlag.SLACK_COMMANDS):
                client.chat_postMessage(
                    channel=user_id, text=":warning: Slack commands are currently disabled."
                )
                return

            # Send morning brief
            success = self.morning_brief.send_morning_brief(user_id)

            if success:
                log_event(
                    severity="info",
                    action="manual_brief_completed",
                    payload={"user_id": user_id},
                    user_id=user_id,
                )
                logger.info(f"Manual brief sent to user {user_id}")
            else:
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: I couldn't generate your morning brief. Please try again in a moment.",
                )

        except Exception as e:
            logger.error(f"Manual brief command failed: {e}")
            try:
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: Sorry, I couldn't generate your morning brief. Please try again in a moment.",
                )
            except Exception as slack_error:
                logger.error(f"Failed to send error message: {slack_error}")

    def handle_wrap_command(self, ack, command, client: WebClient):
        """Handle /flow wrap and /wrap slash commands."""
        ack()

        # Handle /wrap command

        try:
            user_id = command["user_id"]

            logger.info(f"Processing manual wrap command from user {user_id}")

            # Check if Slack commands feature is enabled
            if not is_feature_enabled(FeatureFlag.SLACK_COMMANDS):
                client.chat_postMessage(
                    channel=user_id, text=":warning: Slack commands are currently disabled."
                )
                return

            # Send evening wrap
            success = self.evening_wrap.send_evening_wrap(user_id)

            if success:
                log_event(
                    severity="info",
                    action="manual_wrap_completed",
                    payload={"user_id": user_id},
                    user_id=user_id,
                )
                logger.info(f"Manual wrap sent to user {user_id}")
            else:
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: I couldn't generate your evening wrap. Please try again in a moment.",
                )

        except Exception as e:
            logger.error(f"Manual wrap command failed: {e}")
            try:
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: Sorry, I couldn't generate your evening wrap. Please try again in a moment.",
                )
            except Exception as slack_error:
                logger.error(f"Failed to send error message: {slack_error}")

    def handle_outcomes_command(self, ack, command, client: WebClient):
        """Handle /flow outcomes and /outcomes slash commands."""
        ack()

        # Handle /outcomes command

        try:
            user_id = command["user_id"]

            logger.info(f"Processing manual outcomes command from user {user_id}")

            # Check if Slack commands feature is enabled
            if not is_feature_enabled(FeatureFlag.SLACK_COMMANDS):
                client.chat_postMessage(
                    channel=user_id, text=":warning: Slack commands are currently disabled."
                )
                return

            # Send weekly outcomes prompt
            success = self.weekly_outcomes.send_weekly_prompt(user_id)

            if success:
                log_event(
                    severity="info",
                    action="manual_outcomes_completed",
                    payload={"user_id": user_id},
                    user_id=user_id,
                )
                logger.info(f"Manual outcomes prompt sent to user {user_id}")
            else:
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: I couldn't send your weekly outcomes prompt. Please try again in a moment.",
                )

        except Exception as e:
            logger.error(f"Manual outcomes command failed: {e}")
            try:
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: Sorry, I couldn't send your weekly outcomes prompt. Please try again in a moment.",
                )
            except Exception as slack_error:
                logger.error(f"Failed to send error message: {slack_error}")


def register_manual_commands(app: App):
    """Register manual trigger Slack commands."""
    handler = ManualCommandHandler()

    # Single-word commands
    app.command("/brief")(handler.handle_brief_command)
    app.command("/wrap")(handler.handle_wrap_command)
    app.command("/outcomes")(handler.handle_outcomes_command)
