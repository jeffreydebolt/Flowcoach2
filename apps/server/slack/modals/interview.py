"""Interview modal for collecting user preferences."""

from typing import Dict, Any, Optional
from slack_bolt import App
from slack_sdk import WebClient

from ...platform.feature_flags import is_enabled, FlowCoachFlag
from ...platform.logging import get_logger
from ...platform.errors import single_post_error_guard, handle_preferences_error
from ...core.prefs import WorkPreferences, EnergyWindow, save_user_prefs

logger = get_logger(__name__)


class InterviewModal:
    """Handles the 3-step interview modal for user preferences."""

    def __init__(self):
        """Initialize interview modal handler."""
        pass

    @single_post_error_guard()
    def start_interview(self, user_id: str, client: WebClient) -> None:
        """Start the interview process."""
        if not is_enabled(FlowCoachFlag.FC_INTERVIEW_MODAL_V1):
            logger.warning(f"Interview modal disabled for user {user_id}")
            return

        # Create step 1 modal - Basics
        modal_view = self._create_basics_modal()

        try:
            response = client.views_open(
                trigger_id=user_id, view=modal_view  # This would need to come from a trigger
            )
            logger.info(f"Started interview for user {user_id}", user_id=user_id)
        except Exception as e:
            logger.error(f"Failed to open interview modal: {e}", user_id=user_id)
            raise

    def _create_basics_modal(self) -> Dict[str, Any]:
        """Create the basics (step 1) modal."""
        return {
            "type": "modal",
            "callback_id": "interview_basics",
            "title": {"type": "plain_text", "text": "FlowCoach Setup (1/3)"},
            "submit": {"type": "plain_text", "text": "Next"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Welcome to FlowCoach! 👋"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Let's set up your personalized productivity system. This will take about 2 minutes.",
                    },
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "block_id": "timezone_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "timezone_select",
                        "placeholder": {"type": "plain_text", "text": "Select your timezone"},
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Eastern (EST/EDT)"},
                                "value": "America/New_York",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Central (CST/CDT)"},
                                "value": "America/Chicago",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Mountain (MST/MDT)"},
                                "value": "America/Denver",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Pacific (PST/PDT)"},
                                "value": "America/Los_Angeles",
                            },
                            {"text": {"type": "plain_text", "text": "UTC"}, "value": "UTC"},
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Timezone"},
                },
                {
                    "type": "input",
                    "block_id": "work_days_block",
                    "element": {
                        "type": "checkboxes",
                        "action_id": "work_days_select",
                        "options": [
                            {"text": {"type": "plain_text", "text": "Monday"}, "value": "mon"},
                            {"text": {"type": "plain_text", "text": "Tuesday"}, "value": "tue"},
                            {"text": {"type": "plain_text", "text": "Wednesday"}, "value": "wed"},
                            {"text": {"type": "plain_text", "text": "Thursday"}, "value": "thu"},
                            {"text": {"type": "plain_text", "text": "Friday"}, "value": "fri"},
                            {"text": {"type": "plain_text", "text": "Saturday"}, "value": "sat"},
                            {"text": {"type": "plain_text", "text": "Sunday"}, "value": "sun"},
                        ],
                        "initial_options": [
                            {"text": {"type": "plain_text", "text": "Monday"}, "value": "mon"},
                            {"text": {"type": "plain_text", "text": "Tuesday"}, "value": "tue"},
                            {"text": {"type": "plain_text", "text": "Wednesday"}, "value": "wed"},
                            {"text": {"type": "plain_text", "text": "Thursday"}, "value": "thu"},
                            {"text": {"type": "plain_text", "text": "Friday"}, "value": "fri"},
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Work Days"},
                },
            ],
        }

    def _create_rhythm_modal(self, basics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create the daily rhythm (step 2) modal."""
        return {
            "type": "modal",
            "callback_id": "interview_rhythm",
            "title": {"type": "plain_text", "text": "Daily Rhythm (2/3)"},
            "submit": {"type": "plain_text", "text": "Next"},
            "close": {"type": "plain_text", "text": "Back"},
            "private_metadata": str(basics_data),  # Pass along basics data
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "When do you work best? 📅"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Tell us about your daily schedule so we can send notifications at the right times.",
                    },
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "block_id": "morning_window_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "morning_start",
                        "initial_time": "07:00",
                    },
                    "label": {"type": "plain_text", "text": "Morning brief window starts"},
                },
                {
                    "type": "input",
                    "block_id": "morning_end_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "morning_end",
                        "initial_time": "10:00",
                    },
                    "label": {"type": "plain_text", "text": "Morning brief window ends"},
                },
                {
                    "type": "input",
                    "block_id": "wrap_window_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "wrap_start",
                        "initial_time": "16:00",
                    },
                    "label": {"type": "plain_text", "text": "Evening wrap starts"},
                },
                {
                    "type": "input",
                    "block_id": "wrap_end_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "wrap_end",
                        "initial_time": "18:00",
                    },
                    "label": {"type": "plain_text", "text": "Evening wrap ends"},
                },
                {
                    "type": "input",
                    "block_id": "quiet_hours_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "quiet_start",
                        "initial_time": "18:00",
                    },
                    "label": {"type": "plain_text", "text": "Quiet hours start (no notifications)"},
                },
                {
                    "type": "input",
                    "block_id": "quiet_end_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "quiet_end",
                        "initial_time": "09:00",
                    },
                    "label": {"type": "plain_text", "text": "Quiet hours end"},
                },
            ],
        }

    def _create_energy_modal(self, combined_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create the energy windows (step 3) modal."""
        return {
            "type": "modal",
            "callback_id": "interview_energy",
            "title": {"type": "plain_text", "text": "Energy Windows (3/3)"},
            "submit": {"type": "plain_text", "text": "Complete Setup"},
            "close": {"type": "plain_text", "text": "Back"},
            "private_metadata": str(combined_data),  # Pass along all previous data
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "When is your energy best? ⚡"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Help us schedule the right work at the right times by defining your energy windows.",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Deep Work Window* (complex, focused tasks)",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "deep_window_block",
                    "elements": [
                        {"type": "timepicker", "action_id": "deep_start", "initial_time": "09:00"},
                        {
                            "type": "static_select",
                            "action_id": "deep_duration",
                            "placeholder": {"type": "plain_text", "text": "Duration"},
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "60 minutes"},
                                    "value": "60",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "90 minutes"},
                                    "value": "90",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "120 minutes"},
                                    "value": "120",
                                },
                            ],
                            "initial_option": {
                                "text": {"type": "plain_text", "text": "90 minutes"},
                                "value": "90",
                            },
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Calls Window* (meetings, phone calls)"},
                },
                {
                    "type": "actions",
                    "block_id": "calls_window_block",
                    "elements": [
                        {"type": "timepicker", "action_id": "calls_start", "initial_time": "14:00"},
                        {
                            "type": "static_select",
                            "action_id": "calls_duration",
                            "placeholder": {"type": "plain_text", "text": "Duration"},
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "60 minutes"},
                                    "value": "60",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "90 minutes"},
                                    "value": "90",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "120 minutes"},
                                    "value": "120",
                                },
                            ],
                            "initial_option": {
                                "text": {"type": "plain_text", "text": "60 minutes"},
                                "value": "60",
                            },
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Admin Window* (email, quick tasks)"},
                },
                {
                    "type": "actions",
                    "block_id": "admin_window_block",
                    "elements": [
                        {"type": "timepicker", "action_id": "admin_start", "initial_time": "16:00"},
                        {
                            "type": "static_select",
                            "action_id": "admin_duration",
                            "placeholder": {"type": "plain_text", "text": "Duration"},
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "30 minutes"},
                                    "value": "30",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "60 minutes"},
                                    "value": "60",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "90 minutes"},
                                    "value": "90",
                                },
                            ],
                            "initial_option": {
                                "text": {"type": "plain_text", "text": "30 minutes"},
                                "value": "30",
                            },
                        },
                    ],
                },
            ],
        }

    @handle_preferences_error
    def handle_interview_submission(self, body: Dict[str, Any], client: WebClient) -> None:
        """Handle final interview submission and save preferences."""
        view = body["view"]
        user_id = body["user"]["id"]
        callback_id = view["callback_id"]

        if callback_id == "interview_basics":
            # Move to step 2
            basics_data = self._extract_basics_data(view)
            rhythm_modal = self._create_rhythm_modal(basics_data)
            client.views_update(view_id=view["id"], view=rhythm_modal)

        elif callback_id == "interview_rhythm":
            # Move to step 3
            basics_data = eval(view["private_metadata"])
            rhythm_data = self._extract_rhythm_data(view)
            combined_data = {**basics_data, **rhythm_data}
            energy_modal = self._create_energy_modal(combined_data)
            client.views_update(view_id=view["id"], view=energy_modal)

        elif callback_id == "interview_energy":
            # Complete the interview
            combined_data = eval(view["private_metadata"])
            energy_data = self._extract_energy_data(view)
            all_data = {**combined_data, **energy_data}

            # Convert to WorkPreferences and save
            prefs = self._create_preferences(all_data)
            success = save_user_prefs(user_id, prefs)

            if success:
                # Send completion message
                client.chat_postMessage(
                    channel=user_id,
                    text="🎉 FlowCoach setup complete! Your personalized productivity system is ready.",
                )
                logger.info(f"Interview completed for user {user_id}", user_id=user_id)
            else:
                raise Exception("Failed to save preferences")

    def _extract_basics_data(self, view: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from basics modal."""
        values = view["state"]["values"]

        timezone = values["timezone_block"]["timezone_select"]["selected_option"]["value"]
        work_days = [
            opt["value"]
            for opt in values["work_days_block"]["work_days_select"]["selected_options"]
        ]

        return {"timezone": timezone, "work_days": ",".join(work_days)}

    def _extract_rhythm_data(self, view: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from rhythm modal."""
        values = view["state"]["values"]

        return {
            "morning_window_start": values["morning_window_block"]["morning_start"][
                "selected_time"
            ],
            "morning_window_end": values["morning_end_block"]["morning_end"]["selected_time"],
            "wrap_window_start": values["wrap_window_block"]["wrap_start"]["selected_time"],
            "wrap_window_end": values["wrap_end_block"]["wrap_end"]["selected_time"],
            "quiet_hours_start": values["quiet_hours_block"]["quiet_start"]["selected_time"],
            "quiet_hours_end": values["quiet_end_block"]["quiet_end"]["selected_time"],
        }

    def _extract_energy_data(self, view: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from energy modal."""
        values = view["state"]["values"]

        # Extract energy windows
        deep_start = values["deep_window_block"]["deep_start"]["selected_time"]
        deep_duration = int(
            values["deep_window_block"]["deep_duration"]["selected_option"]["value"]
        )

        calls_start = values["calls_window_block"]["calls_start"]["selected_time"]
        calls_duration = int(
            values["calls_window_block"]["calls_duration"]["selected_option"]["value"]
        )

        admin_start = values["admin_window_block"]["admin_start"]["selected_time"]
        admin_duration = int(
            values["admin_window_block"]["admin_duration"]["selected_option"]["value"]
        )

        return {
            "energy_windows": [
                {"name": "deep", "start_time": deep_start, "duration_minutes": deep_duration},
                {"name": "calls", "start_time": calls_start, "duration_minutes": calls_duration},
                {"name": "admin", "start_time": admin_start, "duration_minutes": admin_duration},
            ]
        }

    def _create_preferences(self, data: Dict[str, Any]) -> WorkPreferences:
        """Create WorkPreferences from collected data."""
        # Convert energy windows
        energy_windows = []
        for ew_data in data["energy_windows"]:
            # Calculate end time from start + duration
            start_hour, start_min = map(int, ew_data["start_time"].split(":"))
            duration_mins = ew_data["duration_minutes"]

            end_total_mins = start_hour * 60 + start_min + duration_mins
            end_hour = (end_total_mins // 60) % 24
            end_min = end_total_mins % 60
            end_time = f"{end_hour:02d}:{end_min:02d}"

            energy_windows.append(
                EnergyWindow(
                    name=ew_data["name"],
                    start_time=ew_data["start_time"],
                    end_time=end_time,
                    max_session_minutes=duration_mins,
                )
            )

        return WorkPreferences(
            timezone=data["timezone"],
            work_days=data["work_days"],
            morning_window_start=data["morning_window_start"],
            morning_window_end=data["morning_window_end"],
            wrap_window_start=data["wrap_window_start"],
            wrap_window_end=data["wrap_window_end"],
            quiet_hours_start=data["quiet_hours_start"],
            quiet_hours_end=data["quiet_hours_end"],
            energy_windows=energy_windows,
        )


def register_interview_handlers(app: App) -> None:
    """Register interview modal handlers."""
    handler = InterviewModal()

    # View submission handlers
    app.view("interview_basics")(handler.handle_interview_submission)
    app.view("interview_rhythm")(handler.handle_interview_submission)
    app.view("interview_energy")(handler.handle_interview_submission)
