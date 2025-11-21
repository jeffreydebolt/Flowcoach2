"""
Handlers package for FlowCoach.

This package contains modules for handling Slack events, messages, and actions.
"""

# Import FlowCoach-specific handlers
from apps.server.slack.commands_audit import register_audit_commands
from apps.server.slack.commands_manual import register_manual_commands
from apps.server.slack.dialogs_rewrite import register_rewrite_handlers

# Import FlowCoach v1 (BMAD) handlers
from apps.server.slack.home import register_home_handlers
from apps.server.slack.modals.interview import register_interview_handlers
from apps.server.slack.modals.morning_brief import register_morning_brief_handlers

from .action_handlers import register_action_handlers
from .event_handlers import register_event_handlers
from .message_handlers import register_message_handlers


def register_handlers(app, services):
    """Register all handlers with the Slack app."""
    register_message_handlers(app, services)
    register_action_handlers(app, services)
    register_event_handlers(app, services)

    # Register FlowCoach-specific handlers
    register_audit_commands(app)
    register_manual_commands(app)
    register_rewrite_handlers(app)

    # Register FlowCoach v1 (BMAD) handlers
    register_home_handlers(app)
    register_interview_handlers(app)
    register_morning_brief_handlers(app)


__all__ = ["register_handlers"]
