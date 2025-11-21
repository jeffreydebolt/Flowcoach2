"""Slack Home tab for FlowCoach dashboard."""

from typing import Any

from slack_bolt import App
from slack_sdk import WebClient

from ..core.prefs import get_user_prefs_or_defaults
from ..platform.errors import single_post_error_guard
from ..platform.feature_flags import FlowCoachFlag, is_enabled
from ..platform.logging import get_logger

logger = get_logger(__name__)


class HomeTab:
    """Renders and manages the FlowCoach Home tab."""

    def __init__(self):
        """Initialize home tab handler."""
        pass

    @single_post_error_guard()
    def render_home_tab(self, user_id: str, client: WebClient) -> None:
        """Render the home tab for a user."""
        logger.info(f"Rendering home tab for user {user_id}", user_id=user_id)

        # Load user preferences (or defaults)
        prefs = get_user_prefs_or_defaults(user_id)

        # Build home tab view
        home_view = self._build_home_view(user_id, prefs)

        try:
            client.views_publish(user_id=user_id, view=home_view)
            logger.info(f"Home tab rendered for user {user_id}", user_id=user_id)
        except Exception as e:
            logger.error(f"Failed to publish home tab: {e}", user_id=user_id)
            raise

    def _build_home_view(self, user_id: str, prefs) -> dict[str, Any]:
        """Build the home tab view based on user preferences and feature flags."""
        blocks = []

        # Header
        blocks.extend(
            [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "FlowCoach Dashboard 🎯"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Good day! Your productivity system is ready to help you focus.",
                    },
                },
                {"type": "divider"},
            ]
        )

        # Preferences summary
        if prefs:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Your Settings:*\n"
                        + f"🌍 Timezone: {prefs.timezone}\n"
                        + f"📅 Work days: {prefs.work_days.replace(',', ', ')}\n"
                        + f"🌅 Morning brief: {prefs.morning_window_start} - {prefs.morning_window_end}\n"
                        + f"🌆 Evening wrap: {prefs.wrap_window_start} - {prefs.wrap_window_end}",
                    },
                }
            )
        else:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Setup needed:* Complete the FlowCoach interview to personalize your experience.",
                    },
                }
            )

        # Action buttons (gated by feature flags)
        action_elements = []

        # Morning Brief button (if enabled)
        if is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1):
            action_elements.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Start Morning Brief"},
                    "action_id": "start_morning_brief",
                    "style": "primary",
                }
            )

        # Setup button (if interview enabled)
        if is_enabled(FlowCoachFlag.FC_INTERVIEW_MODAL_V1):
            action_elements.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Update Setup"},
                    "action_id": "open_interview",
                    # No style specified - uses default button style
                }
            )

        # Add actions if any are available
        if action_elements:
            blocks.extend([{"type": "divider"}, {"type": "actions", "elements": action_elements}])

        # Current commands section (always show existing functionality)
        blocks.extend(
            [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n"
                        + "• `/audit` - Review project health\n"
                        + "• `/brief` - Get morning brief\n"
                        + "• `/wrap` - Evening wrap-up\n"
                        + "• `/outcomes` - Set weekly outcomes",
                    },
                },
            ]
        )

        return {"type": "home", "blocks": blocks}

    def handle_home_action(self, ack: Any, body: dict[str, Any], client: WebClient) -> None:
        """Handle action button clicks from home tab."""
        # Acknowledge the action immediately
        ack()

        action_id = body["actions"][0]["action_id"]
        user_id = body["user"]["id"]

        logger.info(
            f"Home action: {action_id} for user {user_id}", user_id=user_id, action=action_id
        )

        if action_id == "open_interview":
            if is_enabled(FlowCoachFlag.FC_INTERVIEW_MODAL_V1):
                # Would trigger interview modal (needs trigger_id from interaction)
                logger.info(f"Interview modal requested by user {user_id}", user_id=user_id)
                # For now, just send a message
                client.chat_postMessage(
                    channel=user_id, text="Interview modal would open here (feature in development)"
                )
            else:
                logger.warning(f"Interview modal not enabled for user {user_id}", user_id=user_id)

        elif action_id == "start_morning_brief":
            if is_enabled(FlowCoachFlag.FC_MORNING_MODAL_V1):
                logger.info(f"Morning brief requested by user {user_id}", user_id=user_id)
                # Import here to avoid circular imports
                from ..slack.modals.morning_brief import open_morning_brief

                trigger_id = body.get("trigger_id")
                if trigger_id:
                    open_morning_brief(client, trigger_id, user_id)
                else:
                    logger.error("No trigger_id in morning brief request", user_id=user_id)
            else:
                logger.warning(
                    f"Morning brief modal not enabled for user {user_id}", user_id=user_id
                )


def register_home_handlers(app: App) -> None:
    """Register home tab handlers."""
    handler = HomeTab()

    # Home tab opened event
    @app.event("app_home_opened")
    @single_post_error_guard()
    def handle_app_home_opened(body, client):
        """Handle when user opens the Home tab."""
        if not is_enabled(FlowCoachFlag.FC_HOME_TAB_V1):
            logger.info("Home tab disabled, using default")
            return

        user_id = body["event"]["user"]
        handler.render_home_tab(user_id, client)

    # Home tab action handlers
    app.action("open_interview")(handler.handle_home_action)
    app.action("start_morning_brief")(handler.handle_home_action)
