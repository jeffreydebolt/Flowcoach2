"""
Handlers package for FlowCoach.

This package contains modules for handling Slack events, messages, and actions.
"""

from .message_handlers import register_message_handlers
from .action_handlers import register_action_handlers
from .event_handlers import register_event_handlers

def register_handlers(app, services):
    """Register all handlers with the Slack app."""
    register_message_handlers(app, services)
    register_action_handlers(app, services)
    register_event_handlers(app, services)

__all__ = ["register_handlers"]
