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

    @app.action(re.compile("^set_time_"))
    def handle_set_time_action(ack, body, client):
        """
        Handle time chip selection (Phase 2.0 conversational priorities).

        Args:
            ack: Function to acknowledge the action
            body: Action payload
            client: Slack client
        """
        # Acknowledge immediately
        ack()

        try:
            action_id = body["actions"][0]["action_id"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]

            # Parse action_id: set_time_{task_id}_{time_label}
            match = re.match(r"^set_time_(\w+)_(.+)", action_id)
            if not match:
                logger.error(f"Could not parse set_time action ID: {action_id}")
                return

            task_id = match.group(1)
            time_label = match.group(2)

            logger.info(f"Setting time {time_label} for task {task_id} by user {user_id}")

            # Get current task to check if time already set
            current_task = services["todoist"].get_task(task_id)
            if not current_task:
                logger.error(f"Task {task_id} not found")
                return

            current_labels = current_task.get("labels", [])
            time_labels = ["2min", "10min", "30+min"]

            # Check if time already set (idempotent)
            if time_label in current_labels:
                logger.info(f"Time {time_label} already set for task {task_id}")
                # Just update UI to reflect current state
                _update_time_chip_message(
                    client, channel_id, message_ts, current_task, time_label, services
                )
                return

            # Remove existing time labels and add new one
            filtered_labels = [label for label in current_labels if label not in time_labels]
            updated_labels = filtered_labels + [time_label]

            # Update task in Todoist
            success = services["todoist"].update_task(task_id, labels=updated_labels)
            if not success:
                logger.error(f"Failed to update task {task_id} with time {time_label}")
                return

            # Update the message with new chip state
            updated_task = {**current_task, "labels": updated_labels}
            _update_time_chip_message(
                client, channel_id, message_ts, updated_task, time_label, services
            )

            logger.info(f"Successfully set time {time_label} for task {task_id}")

        except Exception as e:
            logger.error(f"Error handling set_time action: {e}", exc_info=True)

    @app.action(re.compile("^set_priority_"))
    def handle_set_priority_action(ack, body, client):
        """
        Handle priority chip selection (Phase 2.0 conversational priorities).

        Args:
            ack: Function to acknowledge the action
            body: Action payload
            client: Slack client
        """
        # Acknowledge immediately
        ack()

        try:
            action_id = body["actions"][0]["action_id"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]

            # Parse action_id: set_priority_{task_id}_P{level}
            match = re.match(r"^set_priority_(\w+)_P([1-4])", action_id)
            if not match:
                logger.error(f"Could not parse set_priority action ID: {action_id}")
                return

            task_id = match.group(1)
            user_priority = int(match.group(2))

            logger.info(f"Setting priority P{user_priority} for task {task_id} by user {user_id}")

            # Get current task
            current_task = services["todoist"].get_task(task_id)
            if not current_task:
                logger.error(f"Task {task_id} not found")
                return

            # Check current priority (idempotent)
            current_todoist_priority = current_task.get("priority", 2)
            current_user_priority = services["todoist"].get_priority_human(current_todoist_priority)

            if current_user_priority == user_priority:
                logger.info(f"Priority P{user_priority} already set for task {task_id}")
                # Just update UI to reflect current state
                _update_priority_chip_message(
                    client, channel_id, message_ts, current_task, user_priority, services
                )
                return

            # Update priority in Todoist
            success = services["todoist"].set_priority_human(task_id, user_priority)
            if not success:
                logger.error(f"Failed to update priority for task {task_id}")
                return

            # Update the message with new chip state
            todoist_priority = 5 - user_priority
            updated_task = {**current_task, "priority": todoist_priority}
            _update_priority_chip_message(
                client, channel_id, message_ts, updated_task, user_priority, services
            )

            logger.info(f"Successfully set priority P{user_priority} for task {task_id}")

        except Exception as e:
            logger.error(f"Error handling set_priority action: {e}", exc_info=True)

    @app.action(re.compile("^bulk_set_priority_"))
    def handle_bulk_set_priority_action(ack, body, client):
        """
        Handle bulk priority setting from priority review list.

        Args:
            ack: Function to acknowledge the action
            body: Action payload
            client: Slack client
        """
        # Acknowledge immediately
        ack()

        try:
            action_id = body["actions"][0]["action_id"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]

            # Parse action_id: bulk_set_priority_{task_id}_P{level}
            match = re.match(r"^bulk_set_priority_(\w+)_P([1-4])", action_id)
            if not match:
                logger.error(f"Could not parse bulk_set_priority action ID: {action_id}")
                return

            task_id = match.group(1)
            user_priority = int(match.group(2))

            logger.info(
                f"Bulk setting priority P{user_priority} for task {task_id} by user {user_id}"
            )

            # Update priority in Todoist
            success = services["todoist"].set_priority_human(task_id, user_priority)
            if not success:
                logger.error(f"Failed to update priority for task {task_id}")
                return

            # Update just this task row in the bulk list
            _update_bulk_priority_row(
                client, channel_id, message_ts, task_id, user_priority, services
            )

            logger.info(f"Successfully bulk set priority P{user_priority} for task {task_id}")

        except Exception as e:
            logger.error(f"Error handling bulk_set_priority action: {e}", exc_info=True)

    @app.action(re.compile("^page_priorities_"))
    def handle_page_priorities_action(ack, body, client):
        """
        Handle pagination for bulk priority review.

        Args:
            ack: Function to acknowledge the action
            body: Action payload
            client: Slack client
        """
        # Acknowledge immediately
        ack()

        try:
            action_id = body["actions"][0]["action_id"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]

            # Parse action_id: page_priorities_{page_num}
            match = re.match(r"^page_priorities_(\d+)", action_id)
            if not match:
                logger.error(f"Could not parse page_priorities action ID: {action_id}")
                return

            page = int(match.group(1))

            # Re-fetch tasks for the requested page
            response = _handle_bulk_priority_page(user_id, page, services)
            if not response or response.get("response_type") != "bulk_priorities":
                logger.error(f"Failed to get page {page} for bulk priorities")
                return

            # Update the message with new page
            from apps.server.slack.blocks import render_bulk_priority_list

            message_payload = render_bulk_priority_list(
                response["tasks"], response["page"], response["total_pages"]
            )

            client.chat_update(
                channel=channel_id, ts=message_ts, text="🎯 Task Priorities", **message_payload
            )

            logger.info(f"Successfully paged to {page} for bulk priorities")

        except Exception as e:
            logger.error(f"Error handling page_priorities action: {e}", exc_info=True)


def _update_time_chip_message(client, channel_id, message_ts, task, selected_time, services):
    """Update message to reflect current time chip selection."""
    try:
        from apps.server.slack.blocks import render_time_chips, render_priority_chips

        # Get current priority
        todoist_priority = task.get("priority", 2)
        user_priority = services["todoist"].get_priority_human(todoist_priority)

        # Rebuild blocks with updated time selection
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":white_check_mark: Added *{task['content']}*"},
            }
        ]

        # Add time chips with current selection
        time_blocks = render_time_chips(task["id"], selected_time)
        blocks.extend(time_blocks)

        # Add priority chips
        priority_blocks = render_priority_chips(task["id"], user_priority)
        blocks.extend(priority_blocks)

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f":white_check_mark: Added {task['content']}",
            blocks=blocks,
        )

    except Exception as e:
        logger.error(f"Failed to update time chip message: {e}")


def _update_priority_chip_message(
    client, channel_id, message_ts, task, selected_priority, services
):
    """Update message to reflect current priority chip selection."""
    try:
        from apps.server.slack.blocks import render_time_chips, render_priority_chips

        # Get current time from labels
        time_labels = ["2min", "10min", "30+min"]
        current_labels = task.get("labels", [])
        selected_time = None

        for time_label in time_labels:
            if time_label in current_labels:
                selected_time = time_label
                break

        if not selected_time:
            selected_time = "10min"  # Default

        # Rebuild blocks with updated priority selection
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":white_check_mark: Added *{task['content']}*"},
            }
        ]

        # Add time chips
        time_blocks = render_time_chips(task["id"], selected_time)
        blocks.extend(time_blocks)

        # Add priority chips with current selection
        priority_blocks = render_priority_chips(task["id"], selected_priority)
        blocks.extend(priority_blocks)

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f":white_check_mark: Added {task['content']}",
            blocks=blocks,
        )

    except Exception as e:
        logger.error(f"Failed to update priority chip message: {e}")


def _update_bulk_priority_row(client, channel_id, message_ts, task_id, new_priority, services):
    """Update a single task row in bulk priority list."""
    try:
        # For bulk updates, we would need to re-render the entire message
        # since we can't easily update just one row in Slack
        # This is a simplified version that would need the full message context
        logger.info(f"Bulk priority updated for task {task_id} to P{new_priority}")

        # In a full implementation, we would:
        # 1. Parse the current message blocks
        # 2. Find the specific task row
        # 3. Update just that row's priority buttons
        # 4. Use chat_update with the modified blocks

    except Exception as e:
        logger.error(f"Failed to update bulk priority row: {e}")


def _handle_bulk_priority_page(user_id, page, services):
    """Handle pagination for bulk priority review."""
    try:
        todoist = services.get("todoist")
        if not todoist:
            return None

        # Fetch open tasks
        tasks = todoist.get_tasks(filter="!completed")
        if not tasks:
            return None

        # Sort by due date, then created date
        def sort_key(task):
            due = task.get("due")
            if due and due.get("date"):
                return (0, due["date"])
            return (1, task.get("created_at", ""))

        tasks.sort(key=sort_key)

        # Pagination
        page_size = 10
        start_idx = page * page_size
        end_idx = start_idx + page_size
        page_tasks = tasks[start_idx:end_idx]
        total_pages = (len(tasks) + page_size - 1) // page_size

        # Format tasks
        formatted_tasks = []
        for task in page_tasks:
            todoist_priority = task.get("priority", 2)
            human_priority = todoist.get_priority_human(todoist_priority)

            formatted_tasks.append(
                {"id": task["id"], "content": task["content"], "priority_human": human_priority}
            )

        return {
            "response_type": "bulk_priorities",
            "tasks": formatted_tasks,
            "page": page,
            "total_pages": total_pages,
        }

    except Exception as e:
        logger.error(f"Failed to handle bulk priority page {page}: {e}")
        return None
