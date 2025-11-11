"""Slack commands for project audit functionality."""

import os
import json
import logging
from typing import Dict, List, Any
from datetime import datetime

from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..core.audit import ProjectAuditor, ProjectAuditItem
from ..core.momentum import MomentumTracker
from ..todoist.client import TodoistClient
from ..core.errors import log_event
from ..core.feature_flags import FeatureFlag, is_feature_enabled

logger = logging.getLogger(__name__)


class AuditCommandHandler:
    """Handles /flow audit slash command and interactions."""

    def __init__(self):
        self.auditor = ProjectAuditor()
        self.tracker = MomentumTracker()
        self.todoist = TodoistClient()

        # Load message templates
        template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "audit.json")
        with open(template_path, "r") as f:
            self.templates = json.load(f)

    def handle_audit_command(self, ack, command, client: WebClient):
        """Handle /audit slash command."""
        ack()
        self._process_audit_command(command, client)

    def _process_audit_command(self, command, client: WebClient):
        """Process audit command logic."""

        # Check if audit feature is enabled
        if not is_feature_enabled(FeatureFlag.PROJECT_AUDIT):
            client.chat_postMessage(
                channel=command["user_id"],
                text=":warning: Project audit feature is currently disabled.",
            )
            return

        try:
            user_id = command["user_id"]
            channel_id = command["channel_id"]

            logger.info(f"Processing audit command from user {user_id}")

            # Get user's projects from Todoist
            projects = self.todoist.get_projects()

            # Classify projects for audit
            categorized = self.auditor.classify_projects(projects)
            summary = self.auditor.get_audit_summary(categorized)

            # Build Slack message
            blocks = self._build_audit_message(categorized, summary)

            # Send audit message
            client.chat_postMessage(
                channel=user_id, blocks=blocks, text="FlowCoach Project Audit"  # Send as DM
            )

            # Log audit completion
            log_event(
                severity="info",
                action="audit_command_completed",
                payload={
                    "user_id": user_id,
                    "total_projects": summary["total_projects"],
                    "healthy_count": summary["healthy_count"],
                    "stalled_count": summary["stalled_count"],
                },
                user_id=user_id,
            )

            logger.info(f"Audit completed for user {user_id}: {summary['total_projects']} projects")

        except Exception as e:
            logger.error(f"Audit command failed: {e}")

            # Send error message to user
            try:
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: Sorry, I couldn't generate your project audit. Please try again in a moment.",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": ":warning: *Project Audit Failed*\n\nI encountered an error while analyzing your projects. Please try again in a moment.",
                            },
                        }
                    ],
                )
            except Exception as slack_error:
                logger.error(f"Failed to send error message: {slack_error}")

    def handle_audit_action(self, ack, body, client: WebClient):
        """Handle audit action button clicks."""
        ack()

        try:
            user_id = body["user"]["id"]
            action_id = body["actions"][0]["action_id"]
            project_id = body["actions"][0]["value"]

            if action_id.startswith("recommit"):
                project_id = project_id.replace("recommit_", "")
                self._handle_recommit_action(user_id, project_id, client)

            elif action_id.startswith("pause"):
                project_id = project_id.replace("pause_", "")
                self._handle_pause_action(user_id, project_id, client)

            elif action_id.startswith("rewrite"):
                project_id = project_id.replace("rewrite_", "")
                self._handle_rewrite_action(user_id, project_id, client)

            # Update the original message to show action taken
            self._update_audit_message_with_action(body, action_id, project_id, client)

        except Exception as e:
            logger.error(f"Audit action failed: {e}")

    def _handle_recommit_action(self, user_id: str, project_id: str, client: WebClient):
        """Handle recommit action."""
        if not is_feature_enabled(FeatureFlag.PROJECT_MOMENTUM):
            client.chat_postMessage(
                channel=user_id, text=":warning: Project momentum feature is currently disabled."
            )
            return

        try:
            # Boost momentum
            success = self.tracker.recommit_project(project_id, minimum_score=60)

            if success:
                # Get project info
                projects = self.todoist.get_projects()
                project_name = next(
                    (p["name"] for p in projects if str(p["id"]) == project_id),
                    f"Project {project_id}",
                )

                # Create a "next action" task
                task_content = f"Next action for: {project_name}"

                try:
                    self.todoist.add_task(task_content, project_id=project_id)

                    client.chat_postMessage(
                        channel=user_id,
                        text=f":muscle: Recommitted to *{project_name}*! I've boosted its momentum and created a task: '{task_content}'",
                    )

                except Exception as task_error:
                    logger.warning(f"Failed to create next action task: {task_error}")
                    client.chat_postMessage(
                        channel=user_id,
                        text=f":muscle: Recommitted to *{project_name}*! Momentum boosted to 60+.",
                    )

                log_event(
                    severity="info",
                    action="audit_recommit_completed",
                    payload={"project_id": project_id, "project_name": project_name},
                    user_id=user_id,
                )
            else:
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: I couldn't recommit to that project. It might not exist in your momentum tracking.",
                )

        except Exception as e:
            logger.error(f"Recommit action failed: {e}")
            client.chat_postMessage(
                channel=user_id,
                text=":warning: Sorry, I couldn't complete the recommit action. Please try again.",
            )

    def _handle_pause_action(self, user_id: str, project_id: str, client: WebClient):
        """Handle pause action."""
        try:
            # Pause project
            success = self.tracker.pause_project(project_id)

            if success:
                # Get project info
                projects = self.todoist.get_projects()
                project_name = next(
                    (p["name"] for p in projects if str(p["id"]) == project_id),
                    f"Project {project_id}",
                )

                client.chat_postMessage(
                    channel=user_id,
                    text=f":pause_button: Paused *{project_name}*. It won't lose momentum while on hold.",
                )

                log_event(
                    severity="info",
                    action="audit_pause_completed",
                    payload={"project_id": project_id, "project_name": project_name},
                    user_id=user_id,
                )
            else:
                client.chat_postMessage(
                    channel=user_id,
                    text=":warning: I couldn't pause that project. It might not exist in your momentum tracking.",
                )

        except Exception as e:
            logger.error(f"Pause action failed: {e}")
            client.chat_postMessage(
                channel=user_id,
                text=":warning: Sorry, I couldn't complete the pause action. Please try again.",
            )

    def _handle_rewrite_action(self, user_id: str, project_id: str, client: WebClient):
        """Handle rewrite action by starting rewrite dialog."""
        if not is_feature_enabled(FeatureFlag.PROJECT_REWRITE):
            client.chat_postMessage(
                channel=user_id, text=":warning: Project rewrite feature is currently disabled."
            )
            return

        try:
            # Get project info
            projects = self.todoist.get_projects()
            project_name = next(
                (p["name"] for p in projects if str(p["id"]) == project_id), f"Project {project_id}"
            )

            # Import and start rewrite flow
            from .dialogs_rewrite import start_rewrite_for_project

            success = start_rewrite_for_project(user_id, project_id, project_name, client)

            if success:
                log_event(
                    severity="info",
                    action="audit_rewrite_started",
                    payload={"project_id": project_id, "project_name": project_name},
                    user_id=user_id,
                )

        except Exception as e:
            logger.error(f"Rewrite action failed: {e}")
            client.chat_postMessage(
                channel=user_id,
                text=":warning: Sorry, I couldn't start the rewrite flow. Please try again.",
            )

    def _build_audit_message(
        self, categorized: Dict[str, List[ProjectAuditItem]], summary: Dict[str, Any]
    ) -> List[Dict]:
        """Build Slack message blocks for audit report."""
        blocks = []

        # Header with summary
        summary_text = f"*{summary['healthy_count']} healthy* • *{summary['needs_definition_count']} need definition* • *{summary['stalled_count']} stalled*"

        header_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":chart_with_upwards_trend: *FlowCoach Project Audit*\n\n{summary_text}",
            },
        }
        blocks.append(header_block)
        blocks.append({"type": "divider"})

        # Healthy projects
        if categorized["healthy"]:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":green_heart: *Healthy Projects* ({len(categorized['healthy'])})",
                    },
                }
            )
            for project in categorized["healthy"][:5]:  # Limit to 5 for brevity
                blocks.append(self._build_project_block(project))

        # Needs definition projects
        if categorized["needs_definition"]:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":yellow_heart: *Needs Definition* ({len(categorized['needs_definition'])})",
                    },
                }
            )
            for project in categorized["needs_definition"][:5]:
                blocks.append(self._build_project_block(project))

        # Stalled projects
        if categorized["stalled"]:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":red_circle: *Stalled Projects* ({len(categorized['stalled'])})",
                    },
                }
            )
            for project in categorized["stalled"][:5]:
                blocks.append(self._build_project_block(project))

        # Summary footer
        timestamp = datetime.now().strftime("%m/%d at %I:%M %p")
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f":bar_chart: {summary['healthy_percentage']}% healthy • {summary['total_projects']} total projects • Updated {timestamp}",
                    }
                ],
            }
        )

        return blocks

    def _build_project_block(self, project: ProjectAuditItem) -> Dict:
        """Build a single project block with actions."""
        # Status emoji
        if project.momentum_score >= 80:
            status_emoji = ":fire:"
        elif project.momentum_score >= 60:
            status_emoji = ":zap:"
        elif project.momentum_score >= 40:
            status_emoji = ":warning:"
        else:
            status_emoji = ":zzz:"

        # Days idle text
        if project.last_activity_days == 0:
            idle_text = "active today"
        elif project.last_activity_days == 1:
            idle_text = "1 day idle"
        else:
            idle_text = f"{project.last_activity_days} days idle"

        block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{project.project_name}* • Score: {project.momentum_score} • {status_emoji} {idle_text}",
            },
        }

        # Add actions for stalled/needs definition projects
        if project.category in ["stalled", "needs_definition"]:
            block["accessory"] = {
                "type": "overflow",
                "options": [
                    {
                        "text": {"type": "plain_text", "text": ":muscle: Recommit"},
                        "value": f"recommit_{project.project_id}",
                    },
                    {
                        "text": {"type": "plain_text", "text": ":pause_button: Pause"},
                        "value": f"pause_{project.project_id}",
                    },
                    {
                        "text": {"type": "plain_text", "text": ":writing_hand: Rewrite"},
                        "value": f"rewrite_{project.project_id}",
                    },
                ],
            }

        return block

    def _update_audit_message_with_action(
        self, body, action_id: str, project_id: str, client: WebClient
    ):
        """Update the audit message to show action was taken."""
        try:
            # Simple approach: just add a small confirmation
            # In production, you might want to regenerate the full audit
            pass  # For MVP, we'll send separate confirmation messages
        except Exception as e:
            logger.error(f"Failed to update audit message: {e}")


def register_audit_commands(app: App):
    """Register audit-related Slack commands and actions."""
    handler = AuditCommandHandler()

    # Only single-word command
    app.command("/audit")(handler.handle_audit_command)

    # Action handlers
    app.action("audit_recommit")(handler.handle_audit_action)
    app.action("audit_pause")(handler.handle_audit_action)
    app.action("audit_rewrite")(handler.handle_audit_action)

    # Overflow menu actions
    app.action("recommit_*")(handler.handle_audit_action)
    app.action("pause_*")(handler.handle_audit_action)
    app.action("rewrite_*")(handler.handle_audit_action)
