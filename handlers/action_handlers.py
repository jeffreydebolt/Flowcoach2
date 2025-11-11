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
        Handle time estimate button clicks with idempotency.

        Args:
            ack: Function to acknowledge the action
            body: Action payload
            client: Slack client
        """
        # Acknowledge immediately to prevent timeout
        ack()

        try:
            action_id = body["actions"][0]["action_id"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]

            logger.info(f"Received action: {action_id} from user {user_id}")

            # Extract task ID and time estimate from action ID
            match = re.match(r"^time_estimate_(\w+)_([\w\+]+)", action_id)
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

            # Update the task with the time estimate as a label (idempotent)
            try:
                # Get or create the time estimate label
                label_id = services["todoist"].get_or_create_label(time_estimate)
                if not label_id:
                    logger.error(f"Failed to create/get label for {time_estimate}")
                    return

                # Get current task to preserve existing labels
                current_task = services["todoist"].get_task(task_id)
                if not current_task:
                    logger.error(f"Could not get task {task_id}")
                    return

                # Check if label already applied
                existing_labels = current_task.get("labels", [])
                if time_estimate in existing_labels:
                    logger.info(f"Label {time_estimate} already applied to task {task_id}")
                    # Update message to show it was already applied
                    client.chat_update(
                        channel=channel_id,
                        ts=message_ts,
                        text=f"✅ {time_estimate} label already applied to task",
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"✅ **{time_estimate}** label already applied to: {task_content}",
                                },
                            }
                        ],
                    )
                    return

                # Remove any existing time estimate labels first
                time_estimate_labels = ["2min", "10min", "30+min"]
                filtered_labels = [
                    label for label in existing_labels if label not in time_estimate_labels
                ]

                # Add the new time estimate label
                updated_labels = filtered_labels + [time_estimate]

                logger.info(f"Updating task {task_id} with labels: {updated_labels}")

                # Update the task with the new labels
                services["todoist"].update_task(task_id, labels=updated_labels)

                # Replace the message to show success (not append)
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"✅ Added {time_estimate} label to task",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"✅ Added **{time_estimate}** label to: {task_content}",
                            },
                        }
                    ],
                )
            except Exception as e:
                logger.error(f"Error updating task: {e}")
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="Sorry, I couldn't update the task with the time estimate.",
                )

        except Exception as e:
            logger.error(f"Error handling time estimate action: {e}", exc_info=True)
            try:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="Sorry, something went wrong while processing your time estimate.",
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
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": response.get("message", "Processing..."),
                            },
                        }
                    ],
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
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": response.get("message", "Processing..."),
                            },
                        }
                    ],
                )

                # Save updated context
                conversation_state[user_id] = context

        except Exception as e:
            logger.error(f"Error handling breakdown action: {e}", exc_info=True)

    @app.action(re.compile("^calendar_"))
    def handle_calendar_action(ack, body, client):
        """
        Handle calendar scheduling button clicks.

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

            logger.info(f"Received calendar action: {action_id} from user {user_id}")

            # Get user context
            context = conversation_state.get(user_id, {})
            task_info = context.get("task_for_calendar", {})

            if not task_info:
                logger.error("No task info found for calendar scheduling")
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="Sorry, I couldn't find the task information for scheduling.",
                )
                return

            # Handle different calendar actions
            if value == "schedule_now":
                # Schedule the task immediately in the next available slot
                calendar_service = services.get("calendar")
                if not calendar_service:
                    client.chat_update(
                        channel=channel_id,
                        ts=message_ts,
                        text="📅 Calendar service not available. Task created successfully without scheduling.",
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "📅 Calendar service not available. Task created successfully without scheduling.",
                                },
                            }
                        ],
                    )
                    return

                # Create calendar event
                result = calendar_service.create_task_time_block(
                    user_id=user_id,
                    task_title=task_info["task_content"],
                    duration_minutes=task_info["duration_minutes"],
                    description=f"GTD Task: {task_info['task_content']}\nEstimate: {task_info['time_estimate']}",
                )

                if result:
                    client.chat_update(
                        channel=channel_id,
                        ts=message_ts,
                        text=f"✅ Task scheduled! {task_info['task_content']} is now on your calendar.",
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"✅ **Task scheduled!** {task_info['task_content']} is now on your calendar.",
                                },
                            }
                        ],
                    )
                else:
                    client.chat_update(
                        channel=channel_id,
                        ts=message_ts,
                        text="📅 Couldn't find an available time slot. Task created successfully.",
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "📅 Couldn't find an available time slot. Task created successfully.",
                                },
                            }
                        ],
                    )

            elif value == "schedule_later":
                # Just acknowledge and suggest scheduling later
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"✅ Task created: {task_info['task_content']} - Schedule it when you're ready!",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"✅ Task created: {task_info['task_content']} - Schedule it when you're ready!",
                            },
                        }
                    ],
                )

            elif value == "task_complete":
                # Just show completion message
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"✅ Task created: {task_info['task_content']}",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"✅ Task created: {task_info['task_content']}",
                            },
                        }
                    ],
                )

            # Clear the calendar task context
            context.pop("task_for_calendar", None)
            conversation_state[user_id] = context

        except Exception as e:
            logger.error(f"Error handling calendar action: {e}", exc_info=True)
            try:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="Sorry, something went wrong while processing your calendar request.",
                )
            except:
                pass
