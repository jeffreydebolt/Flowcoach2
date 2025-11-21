"""Slack interactive action handlers."""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..core.errors import log_event
from ..core.scoring import TaskScorer
from ..db.dal import get_dal
from ..todoist.client import TodoistClient

logger = logging.getLogger(__name__)


class SlackActionHandler:
    """Handle interactive Slack actions."""

    def __init__(self):
        self.slack_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack = WebClient(token=self.slack_token)
        self.todoist = TodoistClient()
        self.dal = get_dal()

    def handle_block_action(self, body: dict[str, Any]) -> None:
        """Handle block action from Slack."""
        try:
            action = body["actions"][0]
            action_id = action["action_id"]
            value = (
                action["selected_option"]["value"]
                if "selected_option" in action
                else action["value"]
            )
            user_id = body["user"]["id"]

            # Route based on action pattern
            if action_id.startswith("task_") and "_actions" in action_id:
                self._handle_morning_brief_action(body, value)
            elif action_id.startswith("wrap_actions_"):
                self._handle_evening_wrap_action(body, value)

            # Acknowledge the action
            response_url = body.get("response_url")
            if response_url:
                # Update the message to show action was processed
                pass

        except Exception as e:
            logger.error(f"Error handling block action: {e}")
            log_event(
                "error",
                "slack_action_error",
                {
                    "error": str(e),
                    "action": body.get("actions", [{}])[0].get("action_id", "unknown"),
                },
            )

    def _handle_morning_brief_action(self, body: dict[str, Any], value: str) -> None:
        """Handle morning brief task actions."""
        # Extract task number and action type
        parts = value.split("_")
        action_type = parts[0]
        task_num = int(parts[1]) - 1  # Convert to 0-based index

        # Get task ID from block
        blocks = body["message"]["blocks"]
        task_block = blocks[2 + task_num]  # Skip intro and divider
        task_id = task_block.get("block_id", "").replace("task_block_", "")

        if not task_id:
            logger.error("Could not extract task ID from block")
            return

        try:
            if action_type == "done":
                # Mark task as complete
                self.todoist.complete_task(task_id)
                self.dal.morning_brief.update_task_status(task_id, "completed")
                self._send_ephemeral(
                    body["channel"]["id"], body["user"]["id"], "✅ Task marked as done!"
                )

            elif action_type == "today":
                # Move to today (update due date)
                today = datetime.now().strftime("%Y-%m-%d")
                self.todoist.update_task(task_id, due_date=today)
                self._send_ephemeral(
                    body["channel"]["id"], body["user"]["id"], "📅 Task moved to today!"
                )

            elif action_type == "snooze":
                # Snooze to tomorrow
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                self.todoist.update_task(task_id, due_date=tomorrow)
                self.dal.morning_brief.update_task_status(task_id, "snoozed")
                self._send_ephemeral(
                    body["channel"]["id"], body["user"]["id"], "😴 Task snoozed to tomorrow!"
                )

        except Exception as e:
            logger.error(f"Error processing morning brief action: {e}")
            self._send_ephemeral(
                body["channel"]["id"], body["user"]["id"], "❌ Sorry, something went wrong."
            )

    def _handle_evening_wrap_action(self, body: dict[str, Any], value: str) -> None:
        """Handle evening wrap task actions."""
        parts = value.split("_", 1)
        action_type = parts[0]
        task_id = parts[1]

        try:
            if action_type == "tomorrow":
                # Move to tomorrow
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                self.todoist.update_task(task_id, due_date=tomorrow)
                self._send_ephemeral(
                    body["channel"]["id"], body["user"]["id"], "📅 Task moved to tomorrow!"
                )

            elif action_type == "pause":
                # Pause project (add label and optionally move to backlog)
                # For now, just add a paused label
                self.todoist.update_task(task_id, labels=["paused"])
                self._send_ephemeral(body["channel"]["id"], body["user"]["id"], "⏸️ Task paused!")

            elif action_type == "archive":
                # Complete/archive the task
                self.todoist.complete_task(task_id)
                self._send_ephemeral(body["channel"]["id"], body["user"]["id"], "📦 Task archived!")

        except Exception as e:
            logger.error(f"Error processing evening wrap action: {e}")
            self._send_ephemeral(
                body["channel"]["id"], body["user"]["id"], "❌ Sorry, something went wrong."
            )

    def handle_message(self, body: dict[str, Any]) -> None:
        """Handle incoming messages."""
        event = body.get("event", {})
        text = event.get("text", "")
        user_id = event.get("user")
        channel = event.get("channel")

        # Check if this is a weekly outcomes response
        if self._is_weekly_outcomes_response(channel, user_id):
            self._process_weekly_outcomes(text, user_id)

        # Check for /flow commands
        if text.startswith("/flow"):
            self._handle_flow_command(text, user_id, channel)

    def _is_weekly_outcomes_response(self, channel: str, user_id: str) -> bool:
        """Check if this is a response to weekly outcomes prompt."""
        # Check if we're waiting for outcomes from this user
        # For now, simple check if it's Monday morning
        now = datetime.now()
        is_monday = now.weekday() == 0
        is_morning = 8 <= now.hour < 12
        return is_monday and is_morning and channel == user_id  # DM channel

    def _process_weekly_outcomes(self, text: str, user_id: str) -> None:
        """Process weekly outcomes from user."""
        # Extract outcomes (numbered or bulleted list)
        outcomes = []

        # Try numbered list
        numbered_pattern = r"^\d+[\.\)]\s*(.+)$"
        # Try bullet points
        bullet_pattern = r"^[\*\-\•]\s*(.+)$"

        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            match = re.match(numbered_pattern, line) or re.match(bullet_pattern, line)
            if match:
                outcomes.append(match.group(1).strip())

        # If no formatted list, take first 3 lines
        if not outcomes and len(lines) <= 3:
            outcomes = [line.strip() for line in lines if line.strip()]

        if outcomes:
            # Store outcomes
            week_start = datetime.now() - timedelta(days=datetime.now().weekday())
            self.dal.weekly_outcomes.set_outcomes(user_id, outcomes[:3], week_start)

            # Confirm to user
            self.slack.chat_postMessage(
                channel=user_id,
                text="Great! I've saved your weekly outcomes:\n"
                + "\n".join(f"{i+1}. {outcome}" for i, outcome in enumerate(outcomes[:3])),
            )

            log_event("info", "weekly_outcomes_set", {"user_id": user_id, "outcomes": outcomes[:3]})

    def _handle_flow_command(self, text: str, user_id: str, channel: str) -> None:
        """Handle /flow commands."""
        parts = text.split()
        if len(parts) < 2:
            return

        command = parts[1].lower()

        if command == "week":
            # Show current weekly outcomes
            outcomes = self.dal.weekly_outcomes.get_current_outcomes(user_id)

            if outcomes:
                message = "*Your weekly outcomes:*\n" + "\n".join(
                    f"{i+1}. {outcome}" for i, outcome in enumerate(outcomes)
                )

                # Add option to update
                blocks = [
                    {"type": "section", "text": {"type": "mrkdwn", "text": message}},
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Update Outcomes"},
                                "value": "update_outcomes",
                                "action_id": "update_weekly_outcomes",
                            }
                        ],
                    },
                ]

                self.slack.chat_postMessage(channel=channel, blocks=blocks)
            else:
                self.slack.chat_postMessage(
                    channel=channel,
                    text="No weekly outcomes set yet. Reply with 3 outcomes to set them!",
                )

    def handle_score_prompt_response(self, text: str, task_id: str, user_id: str) -> None:
        """Handle response to deep work scoring prompt."""
        scores = TaskScorer.parse_score_input(text)

        if not scores:
            self.slack.chat_postMessage(
                channel=user_id,
                text="Invalid format. Please use: impact/urgency/energy (e.g., 4/3/am)",
            )
            return

        impact, urgency, energy = scores
        total_score = TaskScorer.calculate_total_score(impact, urgency, energy)

        # Save scores
        self.dal.task_scores.save_score(task_id, impact, urgency, energy, total_score)

        # Update task labels
        labels = TaskScorer.get_score_labels(impact, urgency, energy)
        self.todoist.update_task(task_id, labels=labels)

        self.slack.chat_postMessage(
            channel=user_id,
            text=f"✅ Scored! Total: {total_score} (Impact: {impact}, Urgency: {urgency}, Energy: {energy})",
        )

    def _send_ephemeral(self, channel: str, user: str, text: str) -> None:
        """Send ephemeral message to user."""
        try:
            self.slack.chat_postEphemeral(channel=channel, user=user, text=text)
        except SlackApiError as e:
            logger.error(f"Failed to send ephemeral message: {e}")
