"""Morning Brief Modal for FlowCoach Phase 1."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from slack_bolt import App
from slack_sdk import WebClient

from ...platform.feature_flags import is_enabled, FlowCoachFlag
from ...platform.logging import get_logger
from ...platform.errors import single_post_error_guard
from ...core.planning import PlanningService, TaskCandidate
from ...integrations.todoist_client import TodoistClient

logger = get_logger(__name__)


class MorningBriefModal:
    """Handles the morning brief planning modal."""

    def __init__(self, planning_service: PlanningService):
        """Initialize morning brief modal handler."""
        self.planning_service = planning_service

    @single_post_error_guard()
    def open_modal(self, trigger_id: str, user_id: str, client: WebClient) -> None:
        """Open morning brief modal for task planning."""
        if not is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1):
            logger.warning(f"Morning brief modal not enabled for user {user_id}", user_id=user_id)
            return

        logger.info(f"MorningBrief.opening for user {user_id}", user_id=user_id)

        # First, open a loading modal to prevent trigger_id expiration
        loading_view = {
            "type": "modal",
            "callback_id": "morning_brief_loading",
            "title": {"type": "plain_text", "text": "Morning Brief"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⏳ *Loading your tasks...*\n\nFetching tasks from Todoist...",
                    },
                }
            ],
        }

        try:
            # Open loading modal immediately
            response = client.views_open(trigger_id=trigger_id, view=loading_view)
            view_id = response["view"]["id"]

            # Now fetch tasks (this might take a moment)
            tasks = self.planning_service.get_morning_brief_tasks(user_id)

            if not tasks:
                # Update to no tasks view
                self._update_to_no_tasks_modal(view_id, client)
                return

            # Build modal with task selection
            modal_view = self._build_planning_modal(tasks, user_id)

            # Update the loading modal with the real content
            client.views_update(view_id=view_id, view=modal_view)

            logger.info(
                f"MorningBrief.opened successfully for user {user_id}",
                user_id=user_id,
                extra_fields={"task_count": len(tasks)},
            )
        except Exception as e:
            logger.error(f"Failed to open morning brief modal: {e}", user_id=user_id)
            raise

    def _build_planning_modal(self, tasks: List[TaskCandidate], user_id: str) -> Dict[str, Any]:
        """Build modal view for task planning."""
        blocks = []

        # Header
        today = datetime.now().strftime("%A, %B %d")
        blocks.extend(
            [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"🌅 Morning Brief - {today}"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Plan your day by setting priorities and time windows for your key tasks.",
                    },
                },
                {"type": "divider"},
            ]
        )

        # Task planning sections
        for i, task in enumerate(tasks):
            task_blocks = self._build_task_section(task, i)
            blocks.extend(task_blocks)

            # Add divider between tasks (except last)
            if i < len(tasks) - 1:
                blocks.append({"type": "divider"})

        return {
            "type": "modal",
            "callback_id": "flowcoach_morning_brief_submit",
            "title": {"type": "plain_text", "text": "Morning Brief"},
            "submit": {"type": "plain_text", "text": "Plan My Day"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": blocks,
            "private_metadata": user_id,  # Store user ID for submission
        }

    def _build_task_section(self, task: TaskCandidate, index: int) -> List[Dict[str, Any]]:
        """Build planning section for a single task."""
        # Task info with context
        task_context = self._format_task_context(task)
        task_text = f"*{task.content}*\n{task_context}"

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": task_text}},
            {
                "type": "actions",
                "block_id": f"task_plan_{index}",
                "elements": [
                    {
                        "type": "static_select",
                        "placeholder": {"type": "plain_text", "text": "Priority"},
                        "action_id": f"priority_{index}",
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "P1 - Must do today"},
                                "value": "p1",
                            },
                            {
                                "text": {"type": "plain_text", "text": "P2 - Should do today"},
                                "value": "p2",
                            },
                            {
                                "text": {"type": "plain_text", "text": "P3 - Nice to do today"},
                                "value": "p3",
                            },
                            {"text": {"type": "plain_text", "text": "Skip today"}, "value": "skip"},
                        ],
                    },
                    {
                        "type": "timepicker",
                        "action_id": f"time_{index}",
                        "placeholder": {"type": "plain_text", "text": "Time window"},
                        "initial_time": self._suggest_time_for_task(task, index),
                    },
                ],
            },
        ]

        # Store task ID in hidden input
        blocks.append(
            {
                "type": "input",
                "block_id": f"task_id_{index}",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "task_id",
                    "initial_value": task.id,
                },
                "label": {"type": "plain_text", "text": "Task ID"},
                "optional": True,
                "dispatch_action": False,
            }
        )

        return blocks

    def _format_task_context(self, task: TaskCandidate) -> str:
        """Format task context for display."""
        context_parts = []

        # Project
        if task.project_name != "Inbox":
            context_parts.append(f"📁 {task.project_name}")

        # Due date / overdue status
        if task.is_overdue:
            context_parts.append("🔴 Overdue")
        elif task.due_date:
            context_parts.append(f"📅 Due {task.due_date}")

        # Priority
        if task.is_priority_1:
            context_parts.append("⭐ Priority 1")

        # Flow labels
        flow_labels = []
        if task.is_flow_tomorrow:
            flow_labels.append("@flow_tomorrow")
        if task.is_flow_weekly:
            flow_labels.append("@flow_weekly")
        if flow_labels:
            context_parts.append(f"🏷️ {', '.join(flow_labels)}")

        return " • ".join(context_parts) if context_parts else "📋 General task"

    def _suggest_time_for_task(self, task: TaskCandidate, index: int) -> str:
        """Suggest time window based on task characteristics and user preferences."""
        # Simple time suggestion logic
        base_hour = 9 + index  # Start at 9 AM, stagger by hour
        if base_hour > 17:  # Don't go past 5 PM
            base_hour = 9 + (index % 8)

        return f"{base_hour:02d}:00"

    def _update_to_no_tasks_modal(self, view_id: str, client: WebClient) -> None:
        """Update loading modal to show no tasks message."""
        modal_view = {
            "type": "modal",
            "callback_id": "morning_brief_empty",
            "title": {"type": "plain_text", "text": "Morning Brief"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "🎉 All Clear!"}},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "No tasks need planning right now.\n\n"
                        + "Tasks that appear here:\n"
                        + "• @flow_tomorrow tasks\n"
                        + "• Overdue tasks\n"
                        + "• Priority 1 tasks\n"
                        + "• @flow_weekly tasks (on Mondays)",
                    },
                },
            ],
        }

        try:
            client.views_update(view_id=view_id, view=modal_view)
        except Exception as e:
            logger.error(f"Failed to update to no tasks modal: {e}")

    def _show_no_tasks_modal(self, trigger_id: str, client: WebClient) -> None:
        """Show modal when no tasks need planning."""
        modal_view = {
            "type": "modal",
            "callback_id": "morning_brief_empty",
            "title": {"type": "plain_text", "text": "Morning Brief"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "🎉 All Clear!"}},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "No tasks need planning right now.\n\n"
                        + "Tasks that appear here:\n"
                        + "• @flow_tomorrow tasks\n"
                        + "• Overdue tasks\n"
                        + "• Priority 1 tasks\n"
                        + "• @flow_weekly tasks (on Mondays)",
                    },
                },
            ],
        }

        try:
            client.views_open(trigger_id=trigger_id, view=modal_view)
        except Exception as e:
            logger.error(f"Failed to show empty morning brief modal: {e}")

    @single_post_error_guard()
    def handle_submission(self, body: Dict[str, Any], client: WebClient) -> None:
        """Handle morning brief modal submission."""
        user_id = body["view"]["private_metadata"]
        values = body["view"]["state"]["values"]

        logger.info(f"MorningBrief.submitting for user {user_id}", user_id=user_id)

        # Extract task planning data
        planned_tasks = self._extract_planning_data(values)

        # Process each planned task
        success_count = 0
        total_count = len([task for task in planned_tasks if task["priority"] != "skip"])

        for task_data in planned_tasks:
            if task_data["priority"] == "skip":
                continue

            success = self.planning_service.mark_task_as_planned(
                task_data["task_id"], task_data["priority"], task_data["time"]
            )

            if success:
                success_count += 1

        # Save checkin time
        checkin_time = datetime.now().strftime("%H:%M")
        self.planning_service.save_checkin_time(user_id, checkin_time)

        # Send success message
        self._send_completion_message(client, user_id, success_count, total_count)

        logger.info(
            f"MorningBrief.submitted successfully for user {user_id}",
            user_id=user_id,
            extra_fields={"planned_tasks": success_count, "total_tasks": total_count},
        )

    def _extract_planning_data(self, values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract planning data from modal submission."""
        planning_data = []

        # Find all task planning blocks
        task_index = 0
        while f"task_plan_{task_index}" in values:
            plan_block = values[f"task_plan_{task_index}"]
            id_block = values.get(f"task_id_{task_index}")

            if not id_block:
                task_index += 1
                continue

            task_id = id_block["task_id"]["value"]
            priority = plan_block[f"priority_{task_index}"]["selected_option"]["value"]
            time_selected = plan_block[f"time_{task_index}"]["selected_time"]

            planning_data.append({"task_id": task_id, "priority": priority, "time": time_selected})

            task_index += 1

        return planning_data

    def _send_completion_message(
        self, client: WebClient, user_id: str, success_count: int, total_count: int
    ) -> None:
        """Send completion message to user."""
        if success_count == total_count:
            message = f"✅ Morning brief complete! Planned {success_count} tasks for today."
        elif success_count > 0:
            message = f"⚠️ Partially complete: planned {success_count} of {total_count} tasks. Some updates failed."
        else:
            message = "❌ Planning failed. Please try again or check your tasks manually."

        try:
            client.chat_postMessage(channel=user_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send completion message: {e}", user_id=user_id)


# Global planning service instance (will be improved with dependency injection later)
_planning_service = None


def get_planning_service():
    """Get or create the planning service."""
    global _planning_service
    if _planning_service is None:
        from ...integrations.todoist_client import TodoistClient
        import os

        todoist_client = TodoistClient(os.environ.get("TODOIST_API_TOKEN"))
        _planning_service = PlanningService(todoist_client)
    return _planning_service


def open_morning_brief(client: WebClient, trigger_id: str, user_id: str) -> None:
    """Open the morning brief modal (exposed function for home tab)."""
    planning_service = get_planning_service()
    handler = MorningBriefModal(planning_service)
    handler.open_modal(trigger_id, user_id, client)


def register_morning_brief_handlers(app: App) -> None:
    """Register morning brief modal handlers."""
    planning_service = get_planning_service()
    handler = MorningBriefModal(planning_service)

    # Note: start_morning_brief action is handled by home.py which calls open_morning_brief()

    # Modal submission handler
    @app.view("flowcoach_morning_brief_submit")
    @single_post_error_guard()
    def handle_flowcoach_morning_brief_submit(body, client):
        """Handle morning brief submission with flowcoach callback ID."""
        handler.handle_submission(body, client)

    @app.view("morning_brief_empty")
    def handle_empty_morning_brief(body, client):
        """Handle empty morning brief modal (no action needed)."""
        pass
