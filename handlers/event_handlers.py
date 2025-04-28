"""
Event handlers for FlowCoach.

This module contains handlers for Slack events (e.g., app_mention, team_join).
"""

import logging

logger = logging.getLogger(__name__)

def register_event_handlers(app, services):
    """
    Register all event handlers with the Slack app.
    
    Args:
        app: Slack app instance
        services: Dictionary of service instances
    """
    # Get agent instances
    communication_agent = services.get("agents", {}).get("communication")
    
    @app.event("app_mention")
    def handle_app_mention(event, say):
        """
        Handle app mention events.
        
        Args:
            event: Event payload
            say: Function to send a message
        """
        try:
            user_id = event.get("user")
            text = event.get("text", "").strip()
            
            logger.info(f"Received app_mention from {user_id}: {text}")
            
            # Remove the app mention from the text
            # This assumes the app mention is at the beginning of the text
            # In a real app, you would use a more robust method
            if "<@" in text and ">" in text:
                mention_end = text.find(">") + 1
                text = text[mention_end:].strip()
            
            # Process the message using the Communication Agent
            if communication_agent:
                response = communication_agent.process_message(
                    {"user": user_id, "text": text},
                    {}  # Empty context for now
                )
                
                if response:
                    say(response.get("message", "I'm here to help!"))
                else:
                    say("I'm not sure how to help with that in a channel. Try sending me a direct message!")
            else:
                say("I'm here to help with your productivity! Send me a direct message to get started.")
            
        except Exception as e:
            logger.error(f"Error handling app_mention: {e}", exc_info=True)
            say("I encountered an error, but I'm still here to help! Let's try that again. 💪")
    
    @app.event("team_join")
    def handle_team_join(event, client):
        """
        Handle team join events.
        
        Args:
            event: Event payload
            client: Slack client
        """
        try:
            user_id = event.get("user", {}).get("id")
            
            if not user_id:
                logger.error("No user ID found in team_join event")
                return
            
            logger.info(f"New user joined: {user_id}")
            
            # Send welcome message
            welcome_message = (
                "Welcome to the team! 👋\n\n"
                "I'm FlowCoach, your productivity assistant. I can help you manage your tasks "
                "using GTD principles, schedule focus time, and more.\n\n"
                "Try sending me a task like \"Write documentation for the project\" or "
                "ask me \"What's my schedule today?\"\n\n"
                "Type \"help\" anytime to see what else I can do!"
            )
            
            client.chat_postMessage(
                channel=user_id,
                text=welcome_message
            )
            
        except Exception as e:
            logger.error(f"Error handling team_join: {e}", exc_info=True)
