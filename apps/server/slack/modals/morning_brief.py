"""Morning Brief Modal for FlowCoach - Simple V1."""

from typing import Dict, Any
from datetime import datetime, date

from slack_bolt import App
from slack_sdk import WebClient

# from ...platform.feature_flags import is_enabled, FlowCoachFlag  # Temporarily bypassed
from ...platform.logging import get_logger
from ...platform.errors import single_post_error_guard
from ...core.planning import PlanningService
from ...core.morning_brief import Task, select_morning_brief_tasks, apply_morning_brief_plan

logger = get_logger(__name__)


def build_morning_brief_modal(selection, today_str: str) -> dict:
    """
    Build simple checkbox-based morning brief modal.

    selection: dict from select_morning_brief_tasks(...)
    today_str: 'Tuesday, November 18' for the title/subtitle
    """
    blocks = []

    # Header / date
    blocks.append(
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Morning plan for {today_str}*"}}
    )
    blocks.append({"type": "divider"})

    # Carryover from yesterday
    if selection["carryover"]:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Carryover from yesterday*"}}
        )
        blocks.append(
            {
                "type": "input",
                "block_id": "mb_carryover",
                "label": {"type": "plain_text", "text": "Include in today's plan"},
                "element": {
                    "type": "checkboxes",
                    "action_id": "carryover_select",
                    "options": [
                        {
                            "text": {"type": "mrkdwn", "text": task.content},
                            "value": task.id,
                        }
                        for task in selection["carryover"]
                    ],
                },
                "optional": True,
            }
        )

    # Overdue P1/P2 tasks
    if selection["overdue"]:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Overdue P1/P2 tasks*"}}
        )
        blocks.append(
            {
                "type": "input",
                "block_id": "mb_overdue",
                "label": {"type": "plain_text", "text": "Include in today's plan"},
                "element": {
                    "type": "checkboxes",
                    "action_id": "overdue_select",
                    "options": [
                        {
                            "text": {"type": "mrkdwn", "text": task.content},
                            "value": task.id,
                        }
                        for task in selection["overdue"]
                    ],
                },
                "optional": True,
            }
        )

    # Today's P1 tasks
    if selection["today_p1"]:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Today's P1 tasks*"}})
        blocks.append(
            {
                "type": "input",
                "block_id": "mb_today_p1",
                "label": {"type": "plain_text", "text": "Include in today's plan"},
                "element": {
                    "type": "checkboxes",
                    "action_id": "today_p1_select",
                    "options": [
                        {
                            "text": {"type": "mrkdwn", "text": task.content},
                            "value": task.id,
                        }
                        for task in selection["today_p1"]
                    ],
                },
                "optional": True,
            }
        )

    # Suggested P1 tasks (undated)
    if selection["suggested_p1"]:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Suggested P1 tasks (undated)*"},
            }
        )
        blocks.append(
            {
                "type": "input",
                "block_id": "mb_suggested_p1",
                "label": {"type": "plain_text", "text": "Include in today's plan"},
                "element": {
                    "type": "checkboxes",
                    "action_id": "suggested_p1_select",
                    "options": [
                        {
                            "text": {"type": "mrkdwn", "text": task.content},
                            "value": task.id,
                        }
                        for task in selection["suggested_p1"]
                    ],
                },
                "optional": True,
            }
        )

    view = {
        "type": "modal",
        "callback_id": "morning_brief_submit",
        "title": {"type": "plain_text", "text": "Morning Brief"},
        "submit": {"type": "plain_text", "text": "Plan My Day"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks,
    }
    return view


class MorningBriefModal:
    """Handles the morning brief planning modal."""

    def __init__(self, planning_service: PlanningService):
        """Initialize morning brief modal handler."""
        self.planning_service = planning_service

    @single_post_error_guard()
    def open_modal(self, trigger_id: str, user_id: str, client: WebClient) -> None:
        """Open morning brief modal for task planning."""
        logger.info(f"MorningBrief.opening NEW for user {user_id}", user_id=user_id)

        # Feature flag temporarily bypassed for stabilization

        try:
            # Open loading modal INSTANTLY - inline definition, no variables
            response = client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "callback_id": "morning_brief_loading",
                    "title": {"type": "plain_text", "text": "Morning Brief"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {"type": "section", "text": {"type": "mrkdwn", "text": "⏳ *Loading...*"}}
                    ],
                },
            )
            view_id = response["view"]["id"]

            # 2) Fetch all tasks from Todoist via planning_service.todoist.get_tasks()
            #    and convert them into Task objects matching apps/server/core/morning_brief.py
            all_tasks_raw = self.planning_service.todoist.get_tasks()

            # Convert to Task objects
            all_tasks = []
            for t in all_tasks_raw:
                # Map Todoist priority (4=P1, 3=P2, etc) to our priority (1=P1, 2=P2)
                priority = 5 - t.get("priority", 1)  # Default to low priority

                # Parse due date
                due_date = None
                if t.get("due") and t["due"].get("date"):
                    try:
                        due_date = date.fromisoformat(t["due"]["date"])
                    except ValueError:
                        pass

                task = Task(
                    id=t["id"],
                    content=t["content"],
                    priority=priority,
                    due_date=due_date,
                    labels=t.get("labels", []),
                    completed=t.get("is_completed", False),
                    project=t.get("project_id"),
                )
                all_tasks.append(task)

            # 3) Use select_morning_brief_tasks(all_tasks, today=today)
            today = date.today()
            today_str = today.strftime("%A, %B %d")
            selection = select_morning_brief_tasks(all_tasks, today=today)

            # Debug logging to see what we found
            logger.info(
                "Morning Brief selection found",
                user_id=user_id,
                extra_fields={
                    "carryover": len(selection["carryover"]),
                    "overdue": len(selection["overdue"]),
                    "today_p1": len(selection["today_p1"]),
                    "suggested_p1": len(selection["suggested_p1"]),
                    "total_raw_tasks": len(all_tasks),
                },
            )

            # 4) If there are no tasks in any bucket, update modal to a "no tasks" message
            total_tasks = sum(len(tasks) for tasks in selection.values())
            if total_tasks == 0:
                self._update_to_no_tasks_modal(view_id, client)
                return

            # 5) Build the real modal with build_morning_brief_modal(selection, today_str)
            modal_view = build_morning_brief_modal(selection, today_str)
            modal_view["private_metadata"] = user_id  # Store user ID

            # 6) Use views_update(view_id=view_id, view=modal_view) to swap loading → real
            client.views_update(view_id=view_id, view=modal_view)

            logger.info(
                f"MorningBrief.opened successfully for user {user_id}",
                user_id=user_id,
                extra_fields={"task_count": total_tasks},
            )
        except Exception as e:
            logger.error(f"Failed to open morning brief modal: {e}", user_id=user_id)
            raise

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

    @single_post_error_guard()
    def handle_submission(self, body: Dict[str, Any], client: WebClient) -> None:
        """Handle morning brief modal submission."""
        user_id = body["user"]["id"]
        values = body["view"]["state"]["values"]

        logger.info(f"MorningBrief.submitting for user {user_id}", user_id=user_id)

        # Extract selected task IDs from the 4 sections
        plan_ids = []

        sections = [
            ("mb_carryover", "carryover_select"),
            ("mb_overdue", "overdue_select"),
            ("mb_today_p1", "today_p1_select"),
            ("mb_suggested_p1", "suggested_p1_select"),
        ]

        for block_id, action_id in sections:
            if block_id in values:
                selected = values[block_id].get(action_id, {}).get("selected_options", [])
                plan_ids.extend(opt["value"] for opt in selected)

        # Build the plan list and call apply_morning_brief_plan
        plan = [
            {"id": task_id, "include": True, "priority": 1, "time": None} for task_id in plan_ids
        ]

        today = date.today()
        apply_morning_brief_plan(
            user_id=user_id,
            plan=plan,
            todoist_client=self.planning_service.todoist,
            today=today,
        )

        # Save checkin time
        checkin_time = datetime.now().strftime("%H:%M")
        self.planning_service.save_checkin_time(user_id, checkin_time)

        # Send a DM to the user
        if plan_ids:
            message = f"Morning Brief complete. I set {len(plan_ids)} tasks as today's focus."
        else:
            message = "Morning Brief complete. You didn't select any tasks for today's focus."

        try:
            client.chat_postMessage(channel=user_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send completion message: {e}", user_id=user_id)

        logger.info(
            f"MorningBrief.submitted successfully for user {user_id}",
            user_id=user_id,
            extra_fields={"planned_tasks": len(plan_ids)},
        )


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

    # Modal submission handlers
    @app.view("morning_brief_submit")
    @single_post_error_guard()
    def handle_morning_brief_submit(ack, body, client):
        """Handle morning brief submission."""
        ack()  # Acknowledge the request immediately
        handler.handle_submission(body, client)

    @app.view("morning_brief_empty")
    def handle_empty_morning_brief(body, client):
        """Handle empty morning brief modal (no action needed)."""
        pass
