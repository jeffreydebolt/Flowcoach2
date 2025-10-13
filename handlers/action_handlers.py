"""
Action handlers for FlowCoach.

This module contains handlers for Slack interactive actions (e.g., button clicks).
"""

import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

def register_action_handlers(app, services):
    """
    Register all action handlers with the Slack app.
    
    Args:
        app: Slack app instance
        services: Dictionary of service instances
    """
    # Get agent instances
    task_agent = services.get("agents", {}).get("task")
    
    # Import conversation state from message handlers
    from handlers.message_handlers import conversation_state
    
    @app.action(re.compile("^time_estimate_"))
    def handle_time_estimate_action(ack, body, client):
        """
        Handle time estimate button clicks.
        
        Args:
            ack: Function to acknowledge the action
            body: Action payload
            client: Slack client
        """
        try:
            ack()
            
            action_id = body["actions"][0]["action_id"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]
            
            logger.info(f"Received action: {action_id} from user {user_id}")
            
            # Extract task ID and time estimate from action ID
            match = re.match(r"^time_estimate_(\w+)_(\w+)", action_id)
            if not match:
                logger.error(f"Could not parse action ID: {action_id}")
                return
            
            task_id = match.group(1)
            time_estimate = match.group(2)
            
            # Get the task content from the message
            task_content = None
            if "blocks" in body["message"]:
                for block in body["message"]["blocks"]:
                    if block["type"] == "section":
                        text = block["text"]["text"]
                        if text.startswith("Task created:"):
                            # Extract just the task content, removing the question
                            task_content = text.split("\n")[0].replace("Task created:", "").strip()
                            break
            
            if not task_content:
                logger.error("Could not find task content in message")
                return
            
            # Update the task with the time estimate
            try:
                # Get current task content without any existing time estimate
                content = re.sub(r'^\[(2min|10min|30\+min)\]\s*', '', task_content)
                
                # Add time estimate at the start
                new_content = f"[{time_estimate}] {content}"
                logger.info(f"Updating task content to: {new_content}")
                
                # Update the task
                services["todoist"].update_task(task_id, content=new_content)
                
                # Update the message to show success
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"Added time estimate: {new_content}",
                    blocks=[{
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Added time estimate: {new_content}"
                        }
                    }]
                )
            except Exception as e:
                logger.error(f"Error updating task: {e}")
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="Sorry, I couldn't update the task with the time estimate."
                )
            
        except Exception as e:
            logger.error(f"Error handling time estimate action: {e}", exc_info=True)
            try:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="Sorry, something went wrong while processing your time estimate."
                )
            except:
                pass
    
    @app.action(re.compile("^project_"))
    def handle_project_action(ack, body, client):
        """
        Handle project detection button clicks.
        
        Args:
            ack: Function to acknowledge the action
            body: Action payload
            client: Slack client
        """
        try:
            ack()
            
            action_id = body["actions"][0]["action_id"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]
            
            logger.info(f"Received project action: {action_id} from user {user_id}")
            
            # Get user context
            context = conversation_state.get(user_id, {})
            logger.info(f"Project action handler context for {user_id}: {context}")
            
            # Handle project breakdown
            if action_id == "project_breakdown":
                response = task_agent.process_message({"text": "yes", "user": user_id}, context)
            elif action_id == "project_create_task":
                response = task_agent.process_message({"text": "no", "user": user_id}, context)
            else:
                return
            
            # Update message based on response
            if response:
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=response.get("message", "Processing..."),
                    blocks=[{
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": response.get("message", "Processing...")
                        }
                    }]
                )
                
                # Save updated context
                conversation_state[user_id] = context
                
        except Exception as e:
            logger.error(f"Error handling project action: {e}", exc_info=True)
    
    @app.action(re.compile("^breakdown_"))
    def handle_breakdown_action(ack, body, client):
        """
        Handle task breakdown button clicks.
        
        Args:
            ack: Function to acknowledge the action
            body: Action payload
            client: Slack client
        """
        try:
            ack()
            
            action_id = body["actions"][0]["action_id"]
            value = body["actions"][0]["value"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]
            
            logger.info(f"Received breakdown action: {action_id} from user {user_id}")
            
            # Get user context
            context = conversation_state.get(user_id, {})
            context["expecting_breakdown_response"] = True
            
            # Process the response
            response = task_agent.process_message({"text": value, "user": user_id}, context)
            
            # Update message based on response
            if response:
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=response.get("message", "Processing..."),
                    blocks=[{
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": response.get("message", "Processing...")
                        }
                    }]
                )
                
                # Save updated context
                conversation_state[user_id] = context
                
        except Exception as e:
            logger.error(f"Error handling breakdown action: {e}", exc_info=True)
