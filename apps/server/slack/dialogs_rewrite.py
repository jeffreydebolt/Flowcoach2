"""Slack dialog handlers for project rewrite flow."""

import logging
from datetime import datetime
from typing import Any

from slack_bolt import App
from slack_sdk import WebClient

from ..core.dateparse import DateParser
from ..core.errors import log_event
from ..core.feature_flags import FeatureFlag, is_feature_enabled
from ..core.momentum import MomentumTracker
from ..todoist.client import TodoistClient

logger = logging.getLogger(__name__)


class ProjectRewriteDialog:
    """Handles the 2-message project rewrite flow."""

    def __init__(self):
        self.date_parser = DateParser()
        self.tracker = MomentumTracker()
        self.todoist = TodoistClient()

        # Simple state storage (in production, use Redis/database)
        self._rewrite_state = {}

    def start_rewrite_flow(
        self, user_id: str, project_id: str, project_name: str, client: WebClient
    ):
        """Start the rewrite flow for a project."""
        if not is_feature_enabled(FeatureFlag.PROJECT_REWRITE):
            client.chat_postMessage(
                channel=user_id, text=":warning: Project rewrite feature is currently disabled."
            )
            return False

        try:
            # Store initial state
            state_key = f"{user_id}:{project_id}"
            self._rewrite_state[state_key] = {
                "step": "awaiting_outcome",
                "project_id": project_id,
                "project_name": project_name,
                "user_id": user_id,
                "started_at": datetime.now().isoformat(),
            }

            # Send first message: ask for outcome
            client.chat_postMessage(
                channel=user_id,
                text=f":writing_hand: Let's rewrite *{project_name}*!",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":writing_hand: *Rewriting Project: {project_name}*",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":one: **What's the concrete outcome you want to achieve?**\n\nPlease describe in one clear sentence what success looks like for this project.",
                        },
                    },
                ],
            )

            log_event(
                severity="info",
                action="rewrite_flow_started",
                payload={
                    "project_id": project_id,
                    "project_name": project_name,
                    "step": "awaiting_outcome",
                },
                user_id=user_id,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to start rewrite flow: {e}")
            client.chat_postMessage(
                channel=user_id,
                text=":warning: Sorry, I couldn't start the rewrite flow. Please try again.",
            )
            return False

    def handle_user_message(self, event: dict[str, Any], client: WebClient) -> bool:
        """
        Handle user messages that might be part of rewrite flow.

        Returns:
            True if message was handled as part of rewrite flow
        """
        try:
            user_id = event["user"]
            text = event.get("text", "").strip()

            if not text:
                return False

            # Check if user has active rewrite flow
            state_key = self._find_active_state(user_id)
            if not state_key:
                return False

            state = self._rewrite_state[state_key]

            if state["step"] == "awaiting_outcome":
                return self._handle_outcome_response(state, text, client)
            elif state["step"] == "awaiting_due_date":
                return self._handle_due_date_response(state, text, client)

            return False

        except Exception as e:
            logger.error(f"Error handling rewrite message: {e}")
            return False

    def _handle_outcome_response(self, state: dict, outcome_text: str, client: WebClient) -> bool:
        """Handle the outcome response (step 1)."""
        try:
            user_id = state["user_id"]
            project_name = state["project_name"]

            # Validate outcome
            if len(outcome_text) < 10:
                client.chat_postMessage(
                    channel=user_id,
                    text=":thinking_face: That seems a bit brief. Could you describe the outcome in more detail? What specific result are you aiming for?",
                )
                return True

            if len(outcome_text) > 200:
                client.chat_postMessage(
                    channel=user_id,
                    text=":scissors: That's quite detailed! Could you summarize the core outcome in 1-2 sentences?",
                )
                return True

            # Store outcome and move to next step
            state["outcome"] = outcome_text
            state["step"] = "awaiting_due_date"

            # Ask for due date
            client.chat_postMessage(
                channel=user_id,
                text=":calendar: Great! Now when should this be completed?",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":white_check_mark: **Outcome:** {outcome_text}",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":two: **When should this be completed?**\n\nYou can say things like:\n• `12/15` or `3/20`\n• `next Friday` or `end of month`\n• `in 2 weeks` or `Jan 30`",
                        },
                    },
                ],
            )

            return True

        except Exception as e:
            logger.error(f"Error handling outcome response: {e}")
            return False

    def _handle_due_date_response(self, state: dict, due_date_text: str, client: WebClient) -> bool:
        """Handle the due date response (step 2) and complete rewrite."""
        try:
            user_id = state["user_id"]
            project_id = state["project_id"]
            project_name = state["project_name"]
            outcome = state["outcome"]

            # Parse the due date
            parsed_date = self.date_parser.parse(due_date_text)

            if not parsed_date:
                client.chat_postMessage(
                    channel=user_id,
                    text=f":calendar: I couldn't understand '{due_date_text}' as a date. Could you try again?\n\nExamples: `12/25`, `next Friday`, `end of month`, `in 3 weeks`",
                )
                return True

            # Validate future date
            is_valid, error_msg = self.date_parser.validate_future_date(parsed_date)
            if not is_valid:
                client.chat_postMessage(
                    channel=user_id,
                    text=f":warning: {error_msg}\n\nPlease choose a future date within the next 2 years.",
                )
                return True

            # Complete the rewrite
            success = self._complete_rewrite(state, outcome, parsed_date, client)

            if success:
                # Clean up state
                state_key = f"{user_id}:{project_id}"
                if state_key in self._rewrite_state:
                    del self._rewrite_state[state_key]

            return True

        except Exception as e:
            logger.error(f"Error handling due date response: {e}")
            return False

    def _complete_rewrite(
        self, state: dict, outcome: str, due_date: datetime, client: WebClient
    ) -> bool:
        """Complete the project rewrite by updating Todoist and momentum."""
        try:
            user_id = state["user_id"]
            project_id = state["project_id"]
            old_project_name = state["project_name"]

            # Format due date for project name
            due_date_str = self.date_parser.format_date_for_project_name(due_date)

            # Create new project name: "{Outcome} — due {MM/DD}"
            new_project_name = f"{outcome} — due {due_date_str}"

            # Update project in Todoist
            try:
                self.todoist.update_project(project_id, name=new_project_name)

                # Update momentum tracking
                self.tracker.update_project_outcome(
                    project_id, outcome_defined=True, due_date=due_date
                )

                # Check if project has open tasks
                tasks = self.todoist.get_tasks(project_id=project_id)
                open_tasks = [task for task in tasks if not task.get("completed", False)]

                # Create "Define deliverables" task if no open tasks
                if not open_tasks:
                    deliverables_task = f"Define deliverables for: {outcome}"
                    self.todoist.add_task(deliverables_task, project_id=project_id)

                    task_message = f"\n\n:point_right: I've added a task: *{deliverables_task}*"
                else:
                    task_message = f"\n\nYou have {len(open_tasks)} open task(s) to work with."

                # Send success message
                client.chat_postMessage(
                    channel=user_id,
                    text=":tada: Successfully rewrote your project!",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f":tada: **Project Rewrite Complete!**\n\n:arrow_right: *{old_project_name}*\n:arrow_down:\n:white_check_mark: *{new_project_name}*{task_message}",
                            },
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f":calendar: Due {due_date.strftime('%A, %B %d')} • :muscle: Momentum reset to 60+",
                                }
                            ],
                        },
                    ],
                )

                # Boost momentum for completing rewrite
                self.tracker.recommit_project(project_id, minimum_score=60)

                log_event(
                    severity="info",
                    action="rewrite_flow_completed",
                    payload={
                        "project_id": project_id,
                        "old_name": old_project_name,
                        "new_name": new_project_name,
                        "outcome": outcome,
                        "due_date": due_date.isoformat(),
                    },
                    user_id=user_id,
                )

                return True

            except Exception as todoist_error:
                logger.error(f"Failed to update project in Todoist: {todoist_error}")
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: I couldn't update your project in Todoist. Please check your integration and try again.",
                )
                return False

        except Exception as e:
            logger.error(f"Error completing rewrite: {e}")
            client.chat_postMessage(
                channel=user_id,
                text=":warning: Sorry, I couldn't complete the project rewrite. Please try again.",
            )
            return False

    def _find_active_state(self, user_id: str) -> str | None:
        """Find active rewrite state for user."""
        for state_key, state in self._rewrite_state.items():
            if state["user_id"] == user_id and state["step"] in [
                "awaiting_outcome",
                "awaiting_due_date",
            ]:
                return state_key
        return None

    def cancel_rewrite_flow(self, user_id: str, client: WebClient) -> bool:
        """Cancel active rewrite flow for user."""
        try:
            state_key = self._find_active_state(user_id)
            if not state_key:
                return False

            state = self._rewrite_state[state_key]
            project_name = state.get("project_name", "your project")

            # Clean up state
            del self._rewrite_state[state_key]

            client.chat_postMessage(
                channel=user_id, text=f":x: Cancelled rewrite flow for *{project_name}*."
            )

            log_event(
                severity="info",
                action="rewrite_flow_cancelled",
                payload={"project_id": state.get("project_id"), "project_name": project_name},
                user_id=user_id,
            )

            return True

        except Exception as e:
            logger.error(f"Error cancelling rewrite flow: {e}")
            return False


# Global dialog instance
_rewrite_dialog = ProjectRewriteDialog()


def handle_message_for_rewrite(event: dict[str, Any], client: WebClient) -> bool:
    """Handle incoming message that might be part of rewrite flow."""
    return _rewrite_dialog.handle_user_message(event, client)


def start_rewrite_for_project(
    user_id: str, project_id: str, project_name: str, client: WebClient
) -> bool:
    """Start rewrite flow for a project."""
    return _rewrite_dialog.start_rewrite_flow(user_id, project_id, project_name, client)


def cancel_user_rewrite_flow(user_id: str, client: WebClient) -> bool:
    """Cancel active rewrite flow for user."""
    return _rewrite_dialog.cancel_rewrite_flow(user_id, client)


def register_rewrite_handlers(app: App):
    """Register rewrite-related message handlers."""

    # Message handler for rewrite flow responses
    @app.message("")
    def handle_rewrite_messages(message, client):
        # Only handle DM messages
        if message.get("channel_type") == "im":
            handle_message_for_rewrite(message, client)

    # Command to cancel rewrite flow
    @app.command("/cancel")
    def handle_cancel_command(ack, command, client):
        ack()
        user_id = command["user_id"]
        cancelled = cancel_user_rewrite_flow(user_id, client)
        if not cancelled:
            client.chat_postMessage(
                channel=user_id, text=":shrug: No active rewrite flow to cancel."
            )
