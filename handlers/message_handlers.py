"""
Message handlers for FlowCoach.

This module contains handlers for Slack messages.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Module-level conversation state storage
conversation_state = {}

def _detect_new_intent(message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Detect if a message indicates a new conversation intent.
    
    Args:
        message: Slack message
        
    Returns:
        Tuple of (has_new_intent: bool, intent_type: Optional[str])
    """
    text = message.get("text", "").strip().lower()
    
    # Task creation intents
    task_patterns = [
        r"^(create|add|make|set up|start)\s+.*task",  # Explicit task creation
        r"^(remind me to|i need to|i want to|i should)",  # Implicit task creation
        r"^[✓✔️]\s+.*",  # Checkmark prefix
        r"^\d+[\.\)]\s+.*",  # Numbered list item
        r"^[-\*]\s+.*"  # Bullet point
    ]
    
    # Calendar intents
    calendar_patterns = [
        r"^(schedule|book|plan|set up)\s+.*meeting",
        r"^what('s|\s+is)\s+my\s+schedule",
        r"^show\s+my\s+(calendar|meetings)",
        r"^when\s+is\s+.*meeting"
    ]
    
    # Help/info intents
    help_patterns = [
        r"^help",
        r"^what\s+can\s+you\s+do",
        r"^how\s+do\s+i"
    ]
    
    # Check task patterns
    for pattern in task_patterns:
        if re.match(pattern, text):
            return True, "task_creation"
    
    # Check calendar patterns        
    for pattern in calendar_patterns:
        if re.match(pattern, text):
            return True, "calendar"
            
    # Check help patterns
    for pattern in help_patterns:
        if re.match(pattern, text):
            return True, "help"
    
    return False, None

def register_message_handlers(app, services):
    """
    Register all message handlers with the Slack app.
    
    Args:
        app: Slack app instance
        services: Dictionary of service instances
    """
    # Create agent instances
    task_agent = services.get("agents", {}).get("task")
    calendar_agent = services.get("agents", {}).get("calendar")
    communication_agent = services.get("agents", {}).get("communication")
    
    # Use the module-level conversation state
    
    @app.message("")
    def handle_message(message, say, client):
        """
        Handle all direct messages.
        
        Args:
            message: Slack message
            say: Function to send a message
            client: Slack client
        """
        try:
            logger.info(f"Received message: {message}")
            
            # Log channel type for debugging
            channel_type = message.get("channel_type")
            logger.info(f"Channel type: {channel_type}")
            
            # Only respond to direct messages
            if channel_type != "im":
                logger.info(f"Ignoring non-DM message in channel type: {channel_type}")
                return
            
            user_id = message.get("user")
            text = message.get("text", "").strip()
            channel_id = message.get("channel")
            
            # Skip bot messages
            if message.get("bot_id"):
                logger.info("Skipping bot message")
                return
            
            logger.info(f"Processing DM from {user_id}: {text}")
            
            # Get or initialize conversation context
            if user_id not in conversation_state:
                conversation_state[user_id] = {}
            context = conversation_state[user_id]
            
            # Detect new intent
            has_new_intent, intent_type = _detect_new_intent(message)
            
            # Clear existing state if new intent detected
            if has_new_intent:
                logger.info(f"New intent detected: {intent_type}. Clearing existing state.")
                context.clear()
                # Optionally set new intent in context
                context["current_intent"] = intent_type
            
            # Try each agent in priority order
            response = None
            
            # First try task agent if available
            if task_agent and task_agent.can_handle(message):
                response = task_agent.process_message(message, context)
                # Update conversation state immediately if task was created
                if response and response.get("response_type") == "task_created_need_estimate":
                    context["expecting_time_estimate"] = True
                    context["last_task_id"] = response.get("task_id")
                    context["last_task_content"] = response.get("task_content")
                    context["current_intent"] = "task_creation"
                    conversation_state[user_id] = context
            
            # Then try calendar agent if available and no task response
            if not response and calendar_agent and calendar_agent.can_handle(message):
                response = calendar_agent.process_message(message, context)
                if response:
                    context["current_intent"] = "calendar"
            
            # Finally, use communication agent as fallback
            if not response and communication_agent:
                response = communication_agent.process_message(message, context)
                if response:
                    context["current_intent"] = "communication"
            
            # If no agent could handle the message, provide a fallback response
            if not response:
                say("I'm not sure how to help with that. Try asking for help to see what I can do!")
                context.clear()  # Clear context on fallback
                return
            
            # Handle the response based on its type
            handle_agent_response(response, say, client, channel_id, user_id, context)
            
            # Update conversation state
            conversation_state[user_id] = context
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            say("I encountered an error, but I'm still here to help! Let's try that again. 💪")
            # Clear context on error
            if user_id in conversation_state:
                conversation_state[user_id].clear()

def handle_agent_response(response, say, client, channel_id, user_id, context):
    """
    Handle agent response based on its type.
    
    Args:
        response: Agent response
        say: Function to send a message
        client: Slack client
        channel_id: Channel ID
        user_id: User ID
        context: Conversation context (will be updated)
    """
    response_type = response.get("response_type", "")
    message = response.get("message", "")
    
    # Handle task creation responses
    if response_type == "task_created_need_estimate":
        # Update context for time estimate follow-up
        context["expecting_time_estimate"] = True
        context["last_task_id"] = response.get("task_id")
        context["last_task_content"] = response.get("task_content")
        
        # Create interactive message with time estimate buttons
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "[2min]"},
                        "value": "2min",
                        "action_id": f"time_estimate_{response.get('task_id')}_2min"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "[10min]"},
                        "value": "10min",
                        "action_id": f"time_estimate_{response.get('task_id')}_10min"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "[30+min]"},
                        "value": "30+min",
                        "action_id": f"time_estimate_{response.get('task_id')}_30+min"
                    }
                ]
            }
        ]
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle task created with estimate
    elif response_type == "task_created_with_estimate":
        say(message)
        # Clear context
        context.pop("expecting_time_estimate", None)
        context.pop("last_task_id", None)
        context.pop("last_task_content", None)
    
    # Handle task created with calendar option
    elif response_type == "task_created_with_calendar_option":
        # Update context from response
        if response.get("context_update"):
            context.update(response["context_update"])
        
        # Store task info for calendar scheduling
        context.update({
            "task_for_calendar": {
                "task_id": response.get("task_id"),
                "task_content": response.get("task_content"),
                "time_estimate": response.get("time_estimate"),
                "duration_minutes": response.get("duration_minutes")
            }
        })
        
        # Create interactive message with calendar scheduling buttons
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "actions",
                "elements": []
            }
        ]
        
        # Add action buttons
        for action in response.get("actions", []):
            blocks[1]["elements"].append({
                "type": "button",
                "text": {"type": "plain_text", "text": action["label"]},
                "value": action["value"],
                "action_id": f"calendar_{action['value']}",
                "style": "primary" if action["value"] == "schedule_now" else None
            })
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle project detection
    elif response_type == "project_detected":
        # Update context from response
        if response.get("context_update"):
            context.update(response["context_update"])
        
        # Create interactive message with buttons
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Yes, break it down"},
                        "value": "breakdown",
                        "action_id": "project_breakdown",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "No, create as task"},
                        "value": "create_task",
                        "action_id": "project_create_task"
                    }
                ]
            }
        ]
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle time estimate applied
    elif response_type == "time_estimate_applied":
        say(message)
        # Clear context
        context.pop("expecting_time_estimate", None)
        context.pop("last_task_id", None)
        context.pop("last_task_content", None)
    
    # Handle invalid time estimate
    elif response_type == "invalid_time_estimate":
        # Keep context for time estimate follow-up
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "[2min]"},
                        "value": "2min",
                        "action_id": f"time_estimate_{context.get('last_task_id')}_2min"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "[10min]"},
                        "value": "10min",
                        "action_id": f"time_estimate_{context.get('last_task_id')}_10min"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "[30+min]"},
                        "value": "30+min",
                        "action_id": f"time_estimate_{context.get('last_task_id')}_30+min"
                    }
                ]
            }
        ]
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle calendar summary
    elif response_type == "calendar_summary":
        events = response.get("events", [])
        
        if not events:
            say(message)
            return
        
        # Create blocks for calendar summary
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
        # Add events to blocks
        for event in events:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{event['summary']}*\n{event['time']}"
                }
            })
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle focus blocks
    elif response_type == "focus_blocks":
        focus_blocks = response.get("focus_blocks", [])
        
        if not focus_blocks:
            say(message)
            return
        
        # Create blocks for focus blocks
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
        # Add focus blocks to blocks
        for block in focus_blocks:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{block['time']}* ({block['duration_minutes']} minutes)"
                }
            })
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle task review
    elif response_type == "task_review":
        tasks_by_estimate = response.get("tasks_by_estimate", {})
        counts = response.get("counts", {})
        
        # Create blocks for task review
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*2min tasks:* {counts.get('2min', 0)}\n*10min tasks:* {counts.get('10min', 0)}\n*30+min tasks:* {counts.get('30+min', 0)}\n*Untagged tasks:* {counts.get('untagged', 0)}"
                }
            }
        ]
        
        # Add tasks by time estimate
        for estimate, tasks in tasks_by_estimate.items():
            if tasks:
                blocks.append({
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{estimate} tasks"
                    }
                })
                
                for task in tasks[:5]:  # Limit to 5 tasks per category
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"• {task['content']}"
                        }
                    })
                
                if len(tasks) > 5:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"_...and {len(tasks) - 5} more {estimate} tasks_"
                        }
                    })
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle tasks broken down
    elif response_type == "tasks_broken_down":
        subtasks = response.get("subtasks", [])
        
        if not subtasks:
            say(message)
            return
        
        # Create blocks for subtasks
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
        # Add subtasks to blocks
        for subtask in subtasks:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {subtask['content']}"
                }
            })
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle task scheduled
    elif response_type == "task_scheduled":
        event = response.get("event", {})
        
        if not event:
            say(message)
            return
        
        # Create blocks for scheduled task
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{event['summary']}*\n{event['start_time'].strftime('%I:%M %p')} - {event['end_time'].strftime('%I:%M %p')}"
                }
            }
        ]
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle help
    elif response_type == "help":
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
        )
    
    # Handle breakdown suggestion
    elif response_type == "breakdown_suggestion":
        # Update context from response
        if response.get("context_update"):
            context.update(response["context_update"])
        
        # Create interactive message with buttons
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "actions",
                "elements": []
            }
        ]
        
        # Add action buttons
        for action in response.get("actions", []):
            blocks[1]["elements"].append({
                "type": "button",
                "text": {"type": "plain_text", "text": action["label"]},
                "value": action["value"],
                "action_id": f"breakdown_{action['value']}",
                "style": "primary" if action["value"] == "create_all" else None
            })
        
        client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks
        )
    
    # Handle all other response types with simple message
    else:
        # Update context if provided
        if response.get("context_update"):
            context.update(response["context_update"])
        say(message)
