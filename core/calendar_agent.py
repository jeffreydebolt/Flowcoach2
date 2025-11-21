"""
Calendar agent for FlowCoach.

This module defines the CalendarAgent class that handles calendar integration functionality.
"""

from datetime import datetime, time
from typing import Any

from core.base_agent import BaseAgent


class CalendarAgent(BaseAgent):
    """
    Agent responsible for calendar integration functionality.

    This agent handles:
    - Calendar event retrieval and summarization
    - Focus block identification
    - Task scheduling based on calendar availability
    - Calendar-based task prioritization
    """

    def __init__(self, config: dict[str, Any], services: dict[str, Any]):
        """
        Initialize the calendar agent.

        Args:
            config: Configuration dictionary
            services: Dictionary of service instances
        """
        super().__init__(config, services)
        self.calendar_service = services.get("calendar")
        self.todoist_service = services.get("todoist")

        if not self.calendar_service:
            self.logger.error(
                "Calendar service not available. Calendar agent functionality will be limited."
            )

        # Calendar-related keywords for intent detection
        self.calendar_keywords = [
            "calendar",
            "schedule",
            "meeting",
            "appointment",
            "event",
            "free time",
            "availability",
            "focus",
            "block",
            "time",
        ]

        # Work hours configuration
        self.work_start_hour = config["calendar"]["work_start_hour"]
        self.work_end_hour = config["calendar"]["work_end_hour"]
        self.min_focus_block_minutes = config["calendar"]["min_focus_block_minutes"]

    def process_message(
        self, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Process a calendar-related message.

        Args:
            message: The message to process
            context: Additional context for processing

        Returns:
            Optional response data or None if no response
        """
        text = message.get("text", "").strip().lower()
        user_id = message.get("user")

        # Check for calendar summary request
        if any(keyword in text for keyword in ["today", "schedule", "calendar"]) and any(
            keyword in text for keyword in ["show", "what", "summary"]
        ):
            return self._get_calendar_summary(user_id)

        # Check for focus time request
        if any(keyword in text for keyword in ["focus", "free time", "availability"]):
            return self._find_focus_blocks(user_id)

        # Check for task scheduling request
        if "schedule" in text and any(
            keyword in text for keyword in ["task", "todo", "to-do", "to do"]
        ):
            return self._schedule_task(text, user_id)

        # No calendar-related intent detected
        return None

    def get_capabilities(self) -> dict[str, Any]:
        """
        Get the capabilities of this agent.

        Returns:
            Dictionary describing agent capabilities
        """
        return {
            "name": "Calendar Agent",
            "description": "Handles calendar integration and scheduling",
            "commands": [
                {
                    "name": "calendar_summary",
                    "description": "Get a summary of your calendar",
                    "examples": ["Show my calendar for today", "What's my schedule?"],
                },
                {
                    "name": "find_focus_blocks",
                    "description": "Find available focus time blocks",
                    "examples": ["When do I have focus time today?", "Show my availability"],
                },
                {
                    "name": "schedule_task",
                    "description": "Schedule a task on your calendar",
                    "examples": [
                        "Schedule the documentation task",
                        "Add time for project planning",
                    ],
                },
            ],
        }

    def can_handle(self, message: dict[str, Any]) -> bool:
        """
        Determine if this agent can handle the given message.

        Args:
            message: The message to check

        Returns:
            True if this agent can handle the message, False otherwise
        """
        text = message.get("text", "").lower()

        # Check for calendar-related keywords
        if any(keyword in text for keyword in self.calendar_keywords):
            return True

        return False

    def _get_calendar_summary(self, user_id: str) -> dict[str, Any]:
        """
        Get a summary of the user's calendar.

        Args:
            user_id: The user ID

        Returns:
            Response data
        """
        if not self.calendar_service:
            return {
                "response_type": "error",
                "message": "Sorry, calendar integration is not available.",
            }

        try:
            # Get today's date
            today = datetime.now().date()

            # Get events for today
            events = self.calendar_service.get_events(
                user_id=user_id, start_date=today, end_date=today
            )

            if not events:
                return {
                    "response_type": "calendar_summary",
                    "events": [],
                    "message": "You have no events scheduled for today.",
                }

            # Format events for display
            formatted_events = []
            for event in events:
                start_time = event["start_time"].strftime("%I:%M %p")
                end_time = event["end_time"].strftime("%I:%M %p")
                formatted_events.append(
                    {
                        "summary": event["summary"],
                        "time": f"{start_time} - {end_time}",
                        "duration_minutes": event["duration_minutes"],
                        "is_all_day": event["is_all_day"],
                    }
                )

            return {
                "response_type": "calendar_summary",
                "events": formatted_events,
                "message": f"Here's your calendar for today ({today.strftime('%A, %B %d')}):",
            }
        except Exception as e:
            self.logger.error(f"Error getting calendar summary: {e}")
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't retrieve your calendar. Please make sure you're connected to Google Calendar.",
            }

    def _find_focus_blocks(self, user_id: str) -> dict[str, Any]:
        """
        Find available focus time blocks.

        Args:
            user_id: The user ID

        Returns:
            Response data
        """
        if not self.calendar_service:
            return {
                "response_type": "error",
                "message": "Sorry, calendar integration is not available.",
            }

        try:
            # Get today's date
            today = datetime.now().date()

            # Get events for today
            events = self.calendar_service.get_events(
                user_id=user_id, start_date=today, end_date=today
            )

            # Find focus blocks
            focus_blocks = self._calculate_focus_blocks(
                events, self.work_start_hour, self.work_end_hour, self.min_focus_block_minutes
            )

            if not focus_blocks:
                return {
                    "response_type": "focus_blocks",
                    "focus_blocks": [],
                    "message": "I couldn't find any focus blocks of at least "
                    f"{self.min_focus_block_minutes} minutes in your calendar today.",
                }

            # Format focus blocks for display
            formatted_blocks = []
            for block in focus_blocks:
                start_time = block["start"].strftime("%I:%M %p")
                end_time = block["end"].strftime("%I:%M %p")
                formatted_blocks.append(
                    {
                        "time": f"{start_time} - {end_time}",
                        "duration_minutes": block["duration_minutes"],
                    }
                )

            return {
                "response_type": "focus_blocks",
                "focus_blocks": formatted_blocks,
                "message": f"Here are your focus blocks for today ({today.strftime('%A, %B %d')}):",
            }
        except Exception as e:
            self.logger.error(f"Error finding focus blocks: {e}")
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't find focus blocks in your calendar. Please make sure you're connected to Google Calendar.",
            }

    def _calculate_focus_blocks(
        self,
        events: list[dict[str, Any]],
        work_start_hour: int,
        work_end_hour: int,
        min_block_minutes: int,
    ) -> list[dict[str, Any]]:
        """
        Calculate available focus blocks based on calendar events.

        Args:
            events: List of calendar events
            work_start_hour: Start of work day (e.g., 9 for 9 AM)
            work_end_hour: End of work day (e.g., 17 for 5 PM)
            min_block_minutes: Minimum duration in minutes to consider a block

        Returns:
            List of focus blocks with start and end times
        """
        # Get the date from the first event, or use today if no events
        if events:
            day = events[0]["start_time"].date()
        else:
            day = datetime.now().date()

        # Set work day boundaries
        work_start = datetime.combine(day, time(hour=work_start_hour))
        work_end = datetime.combine(day, time(hour=work_end_hour))

        # Initialize available time with full work day
        available_blocks = [{"start": work_start, "end": work_end}]

        # Sort events by start time
        sorted_events = sorted(events, key=lambda x: x["start_time"])

        # Remove event times from available blocks
        for event in sorted_events:
            event_start = max(event["start_time"], work_start)
            event_end = min(event["end_time"], work_end)

            # Skip events outside work hours
            if event_end <= work_start or event_start >= work_end:
                continue

            new_blocks = []
            for block in available_blocks:
                # Event is completely outside this block
                if event_end <= block["start"] or event_start >= block["end"]:
                    new_blocks.append(block)
                # Event splits block in two
                elif event_start > block["start"] and event_end < block["end"]:
                    new_blocks.append({"start": block["start"], "end": event_start})
                    new_blocks.append({"start": event_end, "end": block["end"]})
                # Event removes start of block
                elif (
                    event_start <= block["start"]
                    and event_end > block["start"]
                    and event_end < block["end"]
                ):
                    new_blocks.append({"start": event_end, "end": block["end"]})
                # Event removes end of block
                elif (
                    event_start > block["start"]
                    and event_start < block["end"]
                    and event_end >= block["end"]
                ):
                    new_blocks.append({"start": block["start"], "end": event_start})
                # Event completely covers block
                elif event_start <= block["start"] and event_end >= block["end"]:
                    pass  # Block is completely covered, don't add anything

            available_blocks = new_blocks

        # Filter blocks to find focus time (blocks >= min duration)
        focus_blocks = []
        for block in available_blocks:
            duration_minutes = int((block["end"] - block["start"]).total_seconds() / 60)

            if duration_minutes >= min_block_minutes:
                focus_blocks.append(
                    {
                        "start": block["start"],
                        "end": block["end"],
                        "duration_minutes": duration_minutes,
                    }
                )

        return focus_blocks

    def _schedule_task(self, text: str, user_id: str) -> dict[str, Any]:
        """
        Schedule a task on the calendar.

        Args:
            text: The message text
            user_id: The user ID

        Returns:
            Response data
        """
        if not self.calendar_service or not self.todoist_service:
            return {
                "response_type": "error",
                "message": "Sorry, calendar integration or task service is not available.",
            }

        try:
            # Extract task ID or description from text
            # This is a placeholder implementation
            task_id = None
            task_description = None

            # If we have a task ID, get the task details
            if task_id:
                task = self.todoist_service.get_task(task_id)
                if task:
                    task_description = task.get("content")

            if not task_description:
                return {
                    "response_type": "error",
                    "message": "Sorry, I couldn't identify which task to schedule. Please specify the task.",
                }

            # Find available focus blocks
            focus_blocks = self._find_focus_blocks(user_id)
            if focus_blocks.get("response_type") == "error" or not focus_blocks.get("focus_blocks"):
                return {
                    "response_type": "error",
                    "message": "Sorry, I couldn't find any available time to schedule this task.",
                }

            # Get the first available focus block
            block = focus_blocks["focus_blocks"][0]

            # Create calendar event
            event = self.calendar_service.create_event(
                user_id=user_id,
                summary=f"Work on: {task_description}",
                start_time=block["start"],
                end_time=block["end"],
                description=f"Scheduled work time for task: {task_description}",
            )

            return {
                "response_type": "task_scheduled",
                "event": event,
                "message": f"I've scheduled time to work on '{task_description}' from {block['time']}.",
            }
        except Exception as e:
            self.logger.error(f"Error scheduling task: {e}")
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't schedule the task. Please try again.",
            }
