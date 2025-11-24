"""
Task agent for FlowCoach.

This module defines the TaskAgent class that handles task management functionality.
"""

import re
from typing import Any

from core.base_agent import BaseAgent
from core.bmad_client import plan as bmad_plan


class TaskAgent(BaseAgent):
    """
    Agent responsible for task management functionality.

    This agent handles:
    - Task creation and formatting according to GTD principles
    - Task breakdown for complex tasks
    - Time estimation tagging
    - Task prioritization
    - Task review and completion
    """

    def __init__(self, config: dict[str, Any], services: dict[str, Any]):
        """
        Initialize the task agent.

        Args:
            config: Configuration dictionary
            services: Dictionary of service instances
        """
        super().__init__(config, services)
        self.todoist_service = services.get("todoist")
        self.openai_service = services.get("openai")
        self.claude_service = services.get("claude")

        if not self.todoist_service:
            self.logger.error(
                "Todoist service not available. Task agent functionality will be limited."
            )

        # Log which AI service is available
        if self.claude_service:
            self.logger.info("Claude service available - will use Claude for AI features")
        elif self.openai_service:
            self.logger.info("OpenAI service available - will use OpenAI for AI features")
        else:
            self.logger.warning(
                "No AI service available - GTD formatting and task breakdown will be limited"
            )

        # Task-related keywords for intent detection - MUST be very specific
        # Only trigger on explicit task creation requests, not general words
        self.task_keywords = [
            "add task",
            "create task", 
            "new task",
            "add todo",
            "create todo",
            "add to-do",
            "remind me to",
            "make a task",
        ]

        # List indicator patterns
        self.list_indicators = [
            r"create these tasks:",
            r"here('s| is) (what|my list|the list)",
            r"tasks?( for | to do)?:",
            r"todo( list)?:",
            r"to-?do( list)?:",
            r"here('s| are) my tasks?:",
        ]

        # Task line patterns
        self.task_line_patterns = [
            r"^\d+[\.\)]",  # Numbered lists (1., 1), etc.)
            r"^[-\*•]",  # Bullet points
            r"^✓",  # Checkmark
            r"^[\[\(][ x\*][\]\)]",  # Checkbox patterns: [ ], [x], (*), etc.
            r"^[A-Za-z]+\)",  # Letter lists (a), B., etc.)
        ]

        # Time estimate patterns - enhanced to catch more natural language patterns
        self.time_estimate_patterns = {
            "2min": [
                r"\b2\s*min(?:ute)?s?\b",
                r"\btwo\s*min(?:ute)?s?\b",
                r"\bquick\b",
                r"\bfast\b",
                r"\bshort\b",
                r"\b2m\b",
            ],
            "10min": [
                r"\b10\s*min(?:ute)?s?\b",
                r"\bten\s*min(?:ute)?s?\b",
                r"\bmedium\b",
                r"\b10m\b",
                r"\b15\s*min(?:ute)?s?\b",
                r"\bfifteen\s*min(?:ute)?s?\b",
            ],
            "30+min": [
                r"\b30\s*min(?:ute)?s?\s*(?:\+|plus)?\b",
                r"\bthirty\s*min(?:ute)?s?\s*(?:\+|plus)?\b",
                r"\b(?:30|45|60)\s*min(?:ute)?s?\b",
                r"\b1\s*h(?:ou)?r?\b",
                r"\bone\s*h(?:ou)?r?\b",
                r"\blong\b",
                r"\bbig\b",
                r"\b30m\+?\b",
                r"\b(?:hour|hrs?)\b",
                r"\bextended\b",
            ],
        }

    def process_message(
        self, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Process a task-related message.

        Args:
            message: The message to process
            context: Additional context for processing

        Returns:
            Optional response data or None if no response
        """
        text = message.get("text", "").strip()
        user_id = message.get("user")

        self.logger.info(f"Processing message: '{text}' from user: {user_id}")

        # Check if we're in a specific flow
        if context.get("expecting_project_response"):
            return self._handle_project_response(text, context)

        if context.get("expecting_time_estimate"):
            return self._handle_time_estimate(text, context)

        if context.get("expecting_breakdown_response"):
            return self._handle_breakdown_response(text, context)

        # First check if this is a multi-task message BEFORE any formatting
        tasks = self._extract_tasks_from_message(text)
        self.logger.info(f"Extracted {len(tasks)} tasks from message")
        if len(tasks) > 1:
            return self._create_multiple_tasks(tasks, user_id)

        # Check for explicit task breakdown request
        if ("break down" in text.lower() or "breakdown" in text.lower()) and "task" in text.lower():
            return self._break_down_task(text, user_id)

        # If it's a single task, proceed with normal flow
        if self._is_task_creation_request(text):
            task_content = self._extract_task_content(text)
            return self._create_task(task_content, user_id)

        return None

    def _extract_tasks_from_message(self, text: str) -> list[str]:
        """
        Extract tasks from a message, handling both explicit lists and implicit task sequences.

        Args:
            text: The message text

        Returns:
            List of task descriptions
        """
        tasks = []

        # First check for numbered lists in the format "1) task 2) task" on a single line
        # Split by numbered items like "1)", "2)", etc.
        numbered_pattern = r"\d+\)"
        parts = re.split(numbered_pattern, text)

        # If we have multiple parts (header + tasks), extract them
        if len(parts) > 2:  # At least header + 2 tasks
            # Skip the first part (header) and take the rest
            for part in parts[1:]:
                cleaned = part.strip()
                if cleaned:
                    tasks.append(cleaned)

            if tasks:
                return tasks

        # Try splitting by "then" or similar sequence indicators
        if " then " in text.lower():
            tasks = [t.strip() for t in text.split(" then ")]
            return tasks

        # Try splitting by newlines for multi-line lists
        lines = text.split("\n")

        for i, line in enumerate(lines):
            # Clean up the line
            line = line.strip()
            if not line:
                continue

            # Skip header lines that introduce lists
            if any(re.search(pattern, line.lower()) for pattern in self.list_indicators):
                continue

            # Check if this line looks like a task (has a list marker)
            if re.match(
                r"^\d+[\.\)]|^\s*[-\*•]|^\s*✓|^\s*[\[\(][ x\*][\]\)]|^[A-Za-z]+[\.\)]", line
            ):
                # Remove the list marker
                cleaned_line = re.sub(
                    r"^\d+\)|^\d+\.|^\s*[-\*•]|^\s*✓|^\s*[\[\(][ x\*][\]\)]|^[A-Za-z]+[\.\)]",
                    "",
                    line,
                ).strip()

                # Remove task creation prefixes
                for prefix in [
                    "create a task to",
                    "add task to",
                    "create task to",
                    "add a task to",
                ]:
                    if cleaned_line.lower().startswith(prefix):
                        cleaned_line = cleaned_line[len(prefix) :].strip()

                if cleaned_line:
                    tasks.append(cleaned_line)

        # If we still don't have multiple tasks, check for other separators
        if len(tasks) <= 1:
            # Split by other common separators
            for separator in [". ", "; "]:
                if separator in text:
                    tasks = [t.strip() for t in text.split(separator) if t.strip()]
                    break

        # Clean up tasks
        cleaned_tasks = []
        for task in tasks:
            # Remove common prefixes
            task = re.sub(r"^(create|add)( a)? task (to|for) ", "", task, flags=re.IGNORECASE)
            if task:
                cleaned_tasks.append(task)

        return cleaned_tasks

    def _create_multiple_tasks(self, tasks: list[str], user_id: str) -> dict[str, Any]:
        """
        Create multiple tasks in Todoist.

        Args:
            tasks: List of task descriptions
            user_id: The user ID

        Returns:
            Response data with results
        """
        created_tasks = []
        failed_tasks = []

        for task_text in tasks:
            try:
                result = self._create_task(task_text, user_id)
                if result["response_type"] == "task_created":
                    created_tasks.append(result["task_content"])
                else:
                    failed_tasks.append(task_text)
            except Exception as e:
                self.logger.error(f"Error creating task '{task_text}': {e}")
                failed_tasks.append(task_text)

        # Prepare response message
        message_parts = []
        if created_tasks:
            tasks_list = "\n".join(f"✓ {task}" for task in created_tasks)
            message_parts.append(f"Created {len(created_tasks)} tasks:\n{tasks_list}")

        if failed_tasks:
            failed_list = "\n".join(f"❌ {task}" for task in failed_tasks)
            message_parts.append(f"\nFailed to create {len(failed_tasks)} tasks:\n{failed_list}")

        return {
            "response_type": "multiple_tasks_created",
            "created_tasks": created_tasks,
            "failed_tasks": failed_tasks,
            "message": "\n".join(message_parts),
        }

    def get_capabilities(self) -> dict[str, Any]:
        """
        Get the capabilities of this agent.

        Returns:
            Dictionary describing agent capabilities
        """
        return {
            "name": "Task Agent",
            "description": "Manages tasks and GTD workflow",
            "commands": [
                {
                    "name": "create_task",
                    "description": "Create a new task",
                    "examples": ["Add a task to write documentation", "Remind me to call John"],
                },
                {
                    "name": "break_down_task",
                    "description": "Break down a complex task into smaller tasks",
                    "examples": ["Break down the website redesign task"],
                },
                {
                    "name": "review_tasks",
                    "description": "Review current tasks",
                    "examples": ["Show my tasks", "Review my to-dos"],
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

        # Check for task-related keywords
        if any(keyword in text for keyword in self.task_keywords):
            return True

        # Check for task review keywords
        if any(keyword in text for keyword in ["review", "show", "list"]) and any(
            keyword in text for keyword in ["task", "todo", "to-do", "to do"]
        ):
            return True

        # Check for task breakdown keywords
        if "break down" in text and "task" in text:
            return True

        # Check if this looks like a task creation request (action verb + object)
        if self._is_task_creation_request(text):
            return True

        return False

    def _is_task_creation_request(self, text: str) -> bool:
        """
        Determine if the text is a task creation request.

        Args:
            text: The message text

        Returns:
            True if this is a task creation request, False otherwise
        """
        text_lower = text.lower().strip()

        # Check for empty text
        if not text_lower:
            return False

        # Check if this is a question about adding tasks (not an actual task)
        question_patterns = [
            r"^(can|could|would|will) you",
            r"^how (do|can) i",
            r"^what (can|do)",
            r"^help",
            r"\?$",
        ]
        if any(re.search(pattern, text_lower) for pattern in question_patterns):
            return False

        # Check for list indicators
        if any(re.search(pattern, text_lower) for pattern in self.list_indicators):
            return True

        # Check for task line patterns
        if any(re.match(pattern, text_lower) for pattern in self.task_line_patterns):
            return True

        # Check for explicit task creation keywords at the beginning
        if any(
            text_lower.startswith(keyword) for keyword in ["add", "create", "new task", "remind me"]
        ):
            return True

        # Check for task-like phrases
        task_phrases = [
            r"i (need|want|have) to",
            r"i should",
            r"we (need|should|must)",
            r"let'?s",
            r"going to",
            r"will do",
            r"must do",
            r"have to",
        ]
        if any(re.match(pattern, text_lower) for pattern in task_phrases):
            return True

        # DISABLED - This was catching every message!
        # Only explicit task creation requests should trigger
        return False

    def _extract_task_content(self, text: str) -> str:
        """
        Extract the actual task content from the command.

        Args:
            text: The full message text

        Returns:
            The actual task content
        """
        text_lower = text.lower()

        # Remove common task creation prefixes
        prefixes = ["add", "create", "new task", "remind me to", "remind me"]
        for prefix in prefixes:
            if text_lower.startswith(prefix):
                return text[len(prefix) :].strip()

        return text

    def _create_task(self, task_text: str, user_id: str) -> dict[str, Any]:
        """
        Create a task in Todoist.

        Args:
            task_text: Task description
            user_id: The user ID

        Returns:
            Response data
        """
        self.logger.info(f"Creating task: '{task_text}' for user {user_id}")

        try:
            # Check if BMAD planning is enabled
            bmad_result = bmad_plan("capture", task_text, user_id)
            if bmad_result and bmad_result.get("tasks"):
                # Use BMAD's planned task
                bmad_task = bmad_result["tasks"][0]
                task_text = bmad_task.get("title") or task_text

                # Extract BMAD suggestions
                bmad_labels = bmad_task.get("labels", [])
                bmad_project = bmad_task.get("project", "Inbox")
                bmad_estimate = bmad_task.get("estimate_minutes")
                bmad_notes = bmad_task.get("notes", "")

                self.logger.info(f"BMAD planned task: {task_text} with labels {bmad_labels}")

            # Remove common task creation prefixes
            task_text = re.sub(
                r"^(i want to |create a task to |create task to |add task to )",
                "",
                task_text,
                flags=re.IGNORECASE,
            ).strip()

            # Skip GTD formatting for now - it's causing issues
            formatted_task = task_text

            # Extract time estimate if present and clean the task text
            time_estimate, cleaned_task = self._extract_time_estimate(formatted_task)

            # Use the cleaned task text (NO longer adding time estimate to content)
            formatted_task = cleaned_task

            # Keep the original task description as-is for now

            # Check if this might be a project, especially for 30+ min tasks
            if time_estimate == "30+min":
                # For testing, be more aggressive about project detection
                project_keywords = [
                    "create",
                    "build",
                    "develop",
                    "design",
                    "implement",
                    "establish",
                    "forecast",
                    "model",
                    "plan",
                    "strategy",
                ]
                is_potential_project = any(
                    keyword in cleaned_task.lower() for keyword in project_keywords
                )

                if is_potential_project:
                    reason = f"This task involves creating something substantial ('{cleaned_task}') and is estimated to take 30+ minutes, which suggests it might have multiple steps."
                    return {
                        "response_type": "project_detected",
                        "task_content": formatted_task,
                        "reason": reason,
                        "message": f"This looks like a project: '{cleaned_task}' (30+ min task). Would you like me to break this down into smaller tasks?",
                        "actions": [
                            {"label": "Yes, break it down", "value": "breakdown"},
                            {"label": "No, create as task", "value": "create_task"},
                        ],
                        "context_update": {
                            "pending_task": formatted_task,
                            "expecting_project_response": True,
                        },
                    }

            # Create task in Todoist
            task_data = self.todoist_service.add_task(formatted_task)

            if not task_data:
                return {"response_type": "error", "message": "Failed to create task in Todoist."}

            # Add time estimate as label if we have one
            if time_estimate:
                try:
                    # Get or create the time estimate label
                    label_id = self.todoist_service.get_or_create_label(time_estimate)
                    if label_id:
                        # Update the task with the time estimate label
                        self.todoist_service.update_task(
                            task_data.get("id"), labels=[time_estimate]
                        )
                        self.logger.info(
                            f"Added {time_estimate} label to task {task_data.get('id')}"
                        )
                except Exception as e:
                    self.logger.error(f"Failed to add time estimate label: {e}")

            # Build response message
            message = f"Created task: {formatted_task}"
            if bmad_result and bmad_result.get("tasks"):
                message += " (via BMAD planner)"

            # If we have a time estimate, offer calendar scheduling
            if time_estimate:
                # Parse time estimate to minutes for calendar scheduling
                duration_minutes = self._parse_time_estimate_to_minutes(time_estimate)

                response = {
                    "response_type": "task_created_with_calendar_option",
                    "task_id": task_data.get("id"),
                    "task_content": formatted_task,
                    "time_estimate": time_estimate,
                    "duration_minutes": duration_minutes,
                    "message": f"✅ Task created: {formatted_task} (labeled as {time_estimate})\n\nWould you like to schedule this on your calendar?",
                    "actions": [
                        {"label": "📅 Schedule Now", "value": "schedule_now"},
                        {"label": "📅 Schedule Later", "value": "schedule_later"},
                        {"label": "✅ Done", "value": "task_complete"},
                    ],
                }
            else:
                # If no time estimate was found, ask for one
                response = {
                    "response_type": "task_created_need_estimate",
                    "task_id": task_data.get("id"),
                    "task_content": formatted_task,
                    "message": f"Task created: {formatted_task}\nHow long will this task take?",
                }

            return response

        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            return {
                "response_type": "error",
                "message": f"Sorry, I couldn't create that task: {str(e)}",
            }

    def _get_ai_service(self):
        """
        Get the available AI service, preferring Claude over OpenAI.

        Returns:
            AI service instance or None if neither is available
        """
        if self.claude_service:
            return self.claude_service
        elif self.openai_service:
            return self.openai_service
        return None

    def _format_task_with_gtd(self, task_text: str) -> str:
        """
        Format a task according to GTD principles using Claude or OpenAI.

        Args:
            task_text: Original task text

        Returns:
            Formatted task text
        """
        ai_service = self._get_ai_service()
        if not ai_service:
            # Fallback to original text if no AI service
            return task_text

        prompt = f"""
        Reformat this task description according to Getting Things Done (GTD) principles:

        Original task: "{task_text}"

        A good GTD task should:
        1. Start with an action verb
        2. Be specific and clear
        3. Be achievable in one sitting
        4. Include context if appropriate

        Return only the reformatted task text without additional explanation.
        """

        try:
            if self.claude_service:
                response = self.claude_service.format_task_with_gtd(task_text)
            else:
                response = self.openai_service.generate_text(prompt)
            return response.strip()
        except Exception as e:
            self.logger.error(f"Error formatting task with AI: {e}")
            return task_text  # Fallback to original

    def _extract_time_estimate(self, text: str) -> tuple[str | None, str]:
        """
        Extract time estimate from text and return cleaned text.

        Args:
            text: The text to analyze

        Returns:
            Tuple of (time_estimate, cleaned_text)
        """
        original_text = text
        text_lower = text.lower()

        # First check for explicit time patterns and remove them
        explicit_patterns = [
            (r"[-–]\s*(\d+\s*(?:min(?:ute)?s?|m)\s*(?:\+|plus)?)", None),
            (r"[-–]\s*(\d+\s*h(?:ou)?rs?)", "30+min"),
            (r"\((\d+\s*(?:min(?:ute)?s?|m)\s*(?:\+|plus)?)\)", None),
            (r"\[(\d+\s*(?:min(?:ute)?s?|m)\s*(?:\+|plus)?)\]", None),
        ]

        for pattern, default_estimate in explicit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                time_str = match.group(1).lower()
                # Remove the time estimate from the text
                cleaned_text = text[: match.start()] + text[match.end() :]
                cleaned_text = cleaned_text.strip()

                # Extract number
                num_match = re.search(r"\d+", time_str)
                if num_match:
                    minutes = int(num_match.group())
                    if minutes <= 5:
                        return "2min", cleaned_text
                    elif minutes <= 15:
                        return "10min", cleaned_text
                    else:
                        return "30+min", cleaned_text
                if default_estimate:
                    return default_estimate, cleaned_text

        # Fall back to keyword matching (don't remove keywords)
        for estimate, patterns in self.time_estimate_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return estimate, original_text

        return None, original_text

    def _parse_time_estimate_to_minutes(self, time_estimate: str) -> int:
        """
        Convert time estimate string to minutes.

        Args:
            time_estimate: Time estimate string like "2min", "10min", "30+min"

        Returns:
            Duration in minutes
        """
        if time_estimate == "2min":
            return 2
        elif time_estimate == "10min":
            return 10
        elif time_estimate == "30+min":
            return 30
        else:
            # Default to 10 minutes for unknown estimates
            return 10

    def _handle_time_estimate(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Handle time estimate response.

        Args:
            text: The user's response
            context: Conversation context

        Returns:
            Response data
        """
        # Check if we're handling multiple tasks
        if context.get("multiple_tasks"):
            return self._handle_multiple_task_estimates(text, context)

        task_id = context.get("last_task_id")
        task_content = context.get("last_task_content", "your task")

        # Determine time estimate from text
        time_estimate = None
        text_lower = text.lower()

        # Check for direct matches to our time estimate options
        if "2min" in text_lower or "two min" in text_lower or "quick" in text_lower:
            time_estimate = "2min"
        elif "10min" in text_lower or "ten min" in text_lower or "medium" in text_lower:
            time_estimate = "10min"
        elif "30" in text_lower or "thirty" in text_lower or "long" in text_lower:
            time_estimate = "30+min"

        if not time_estimate:
            return {
                "response_type": "invalid_time_estimate",
                "message": "I didn't understand that time estimate. Please choose 2min, 10min, or 30+min.",
                "actions": [
                    {"label": "[2min]", "value": "2min"},
                    {"label": "[10min]", "value": "10min"},
                    {"label": "[30+min]", "value": "30+min"},
                ],
            }

        # Apply time estimate to task
        try:
            self._apply_time_estimate(task_id, time_estimate)
            return {
                "response_type": "time_estimate_applied",
                "task_id": task_id,
                "time_estimate": time_estimate,
                "message": f"Great! I've tagged '{task_content}' as {time_estimate}.",
            }
        except Exception as e:
            self.logger.error(f"Error applying time estimate: {e}")
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't apply the time estimate. The task was created, but not tagged.",
            }

    def _handle_multiple_task_estimates(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Handle time estimates for multiple tasks.

        Args:
            text: The user's response
            context: Conversation context

        Returns:
            Response data
        """
        text_lower = text.lower()
        tasks = context.get("created_tasks", [])

        # Handle bulk estimate
        if text_lower.startswith("all"):
            time_estimate = None
            if "2min" in text_lower or "two min" in text_lower or "quick" in text_lower:
                time_estimate = "2min"
            elif "10min" in text_lower or "ten min" in text_lower or "medium" in text_lower:
                time_estimate = "10min"
            elif "30" in text_lower or "thirty" in text_lower or "long" in text_lower:
                time_estimate = "30+min"

            if time_estimate:
                updated_tasks = []
                failed_tasks = []

                for task in tasks:
                    try:
                        self._apply_time_estimate(task["id"], time_estimate)
                        updated_tasks.append(task["content"])
                    except Exception as e:
                        self.logger.error(f"Error applying time estimate to task {task['id']}: {e}")
                        failed_tasks.append(task["content"])

                message_parts = [f"Applied {time_estimate} estimate to {len(updated_tasks)} tasks."]
                if failed_tasks:
                    message_parts.append(f"\nNote: Failed to update {len(failed_tasks)} tasks:")
                    for task in failed_tasks:
                        message_parts.append(f"• {task}")

                return {
                    "response_type": "multiple_time_estimates_applied",
                    "message": "\n".join(message_parts),
                }

        # Handle individual estimates or invalid input
        if text_lower == "individual" or not text_lower.startswith("all"):
            next_task = next((task for task in tasks if task.get("needs_estimate")), None)

            if next_task:
                return {
                    "response_type": "need_individual_estimate",
                    "task_id": next_task["id"],
                    "task_content": next_task["content"],
                    "message": f"How long will this task take: {next_task['content']}?",
                    "actions": [
                        {"label": "[2min]", "value": "2min"},
                        {"label": "[10min]", "value": "10min"},
                        {"label": "[30+min]", "value": "30+min"},
                    ],
                }

        return {
            "response_type": "invalid_time_estimate",
            "message": "Please choose to either apply the same estimate to all tasks or estimate them individually:",
            "actions": [
                {"label": "All [2min]", "value": "all_2min"},
                {"label": "All [10min]", "value": "all_10min"},
                {"label": "All [30+min]", "value": "all_30+min"},
                {"label": "Estimate individually", "value": "individual"},
            ],
        }

    def _apply_time_estimate(self, task_id: str, time_estimate: str) -> None:
        """
        Apply time estimate to a task by adding it to the task name.

        Args:
            task_id: The task ID
            time_estimate: The time estimate (e.g., "2min", "10min", "30+min")
        """
        try:
            # Get current task
            task = self.todoist_service.get_task(task_id)
            if not task:
                self.logger.error(f"Could not find task {task_id}")
                return

            # Get current content without any existing time estimate
            content = task["content"]
            content = re.sub(r"^\[(2min|10min|30\+min)\]\s*", "", content)

            # Add time estimate at the start
            new_content = f"[{time_estimate}] {content}"
            self.logger.info(f"Updating task content to: {new_content}")

            # Update the task
            self.todoist_service.update_task(task_id, content=new_content)

        except Exception as e:
            self.logger.error(f"Error applying time estimate: {e}")
            raise

    def _break_down_task(self, text: str, user_id: str) -> dict[str, Any]:
        """
        Break down a complex task into smaller tasks.

        Args:
            text: The message text
            user_id: The user ID

        Returns:
            Response data
        """
        # Extract task description from text
        task_description = self._extract_task_for_breakdown(text)

        # If we have an AI service, use it to break down the task
        ai_service = self._get_ai_service()
        if ai_service:
            try:
                subtasks = self._generate_subtasks(task_description)

                if not subtasks:
                    return {
                        "response_type": "error",
                        "message": "I couldn't generate any subtasks. Please try rephrasing the task.",
                    }

                # Format message with subtasks
                message_parts = ["Here's how I would break down this task:"]
                for i, subtask in enumerate(subtasks, 1):
                    message_parts.append(f"{i}. {subtask}")
                message_parts.append("\nWould you like me to create these subtasks?")

                # Store subtasks in context for later use
                return {
                    "response_type": "breakdown_suggestion",
                    "message": "\n".join(message_parts),
                    "subtasks": subtasks,
                    "original_task": task_description,
                    "actions": [
                        {"label": "✓ Create all", "value": "create_all"},
                        {"label": "✏️ Edit first", "value": "edit"},
                        {"label": "❌ Cancel", "value": "cancel"},
                    ],
                    "context_update": {
                        "pending_subtasks": subtasks,
                        "original_task": task_description,
                        "expecting_breakdown_response": True,
                    },
                }

            except Exception as e:
                self.logger.error(f"Error generating subtasks: {e}")
                return {
                    "response_type": "error",
                    "message": "Sorry, I encountered an error while breaking down the task. Please try again.",
                }

        return {
            "response_type": "error",
            "message": "Sorry, I couldn't break down the task. This feature requires AI integration (Claude or OpenAI).",
        }

    def _extract_task_for_breakdown(self, text: str) -> str:
        """
        Extract the task description for breakdown from the message.

        Args:
            text: The message text

        Returns:
            Task description
        """
        text_lower = text.lower()

        # Remove common prefixes
        prefixes = ["break down", "breakdown", "split", "divide", "separate"]

        for prefix in prefixes:
            if text_lower.startswith(prefix):
                # Remove the prefix and "task" or "into" if present
                cleaned = text[len(prefix) :].strip()
                cleaned = re.sub(r"^(the\s+)?task\s+", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"^into\s+", "", cleaned, flags=re.IGNORECASE)
                return cleaned

        return text

    def _handle_breakdown_response(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Handle user response to task breakdown suggestion.

        Args:
            text: The user's response
            context: Conversation context

        Returns:
            Response data
        """
        text_lower = text.lower().strip()
        subtasks = context.get("pending_subtasks", [])
        original_task = context.get("original_task", "")

        if not subtasks:
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't find the subtasks to create. Please try breaking down the task again.",
            }

        # Handle different response types
        if text_lower in ["create all", "yes", "create", "✓", "create_all", "create them", "do it"]:
            created_tasks = []
            failed_tasks = []

            # Create parent task if it doesn't exist
            parent_task_id = None
            try:
                parent_response = self._create_task(original_task, context.get("user_id"))
                if parent_response.get("response_type") != "error":
                    parent_task_id = parent_response.get("task_id")
            except Exception as e:
                self.logger.error(f"Error creating parent task: {e}")

            # Create each subtask
            for subtask in subtasks:
                try:
                    # Format subtask with parent task reference if available
                    formatted_subtask = self._format_task_with_gtd(subtask)
                    task_data = self.todoist_service.add_task(
                        formatted_subtask, parent_id=parent_task_id
                    )
                    created_tasks.append(
                        {
                            "id": task_data.get("id"),
                            "content": formatted_subtask,
                            "needs_estimate": True,
                        }
                    )
                except Exception as e:
                    self.logger.error(f"Error creating subtask '{subtask}': {e}")
                    failed_tasks.append(subtask)

            # Clear the breakdown context
            context.clear()

            if not created_tasks:
                return {
                    "response_type": "error",
                    "message": "Sorry, I couldn't create any of the subtasks. Please try again.",
                }

            # Prepare success message
            message_parts = []
            if parent_task_id:
                message_parts.append(f"Created main task: {original_task}")
            message_parts.append(f"Created {len(created_tasks)} subtasks:")
            for task in created_tasks:
                message_parts.append(f"• {task['content']}")

            if failed_tasks:
                message_parts.append(f"\nNote: Failed to create {len(failed_tasks)} subtasks:")
                for task in failed_tasks:
                    message_parts.append(f"• {task}")

            message_parts.append("\nWould you like to add time estimates to these tasks?")

            return {
                "response_type": "multiple_tasks_created",
                "message": "\n".join(message_parts),
                "created_tasks": created_tasks,
                "failed_tasks": failed_tasks,
                "actions": [
                    {"label": "All [2min]", "value": "all_2min"},
                    {"label": "All [10min]", "value": "all_10min"},
                    {"label": "All [30+min]", "value": "all_30+min"},
                    {"label": "Estimate individually", "value": "individual"},
                ],
            }

        elif text_lower in ["edit", "edit first", "modify", "✏️", "edit_first"]:
            # Prepare for editing mode
            return {
                "response_type": "edit_subtasks",
                "message": "Here are the subtasks. Edit them as needed (one per line):",
                "subtasks": subtasks,
                "original_task": original_task,
                "context_update": {"editing_subtasks": True, "original_task": original_task},
            }

        elif text_lower in ["cancel", "no", "❌", "cancel_breakdown"]:
            # Clear the breakdown context
            context.clear()
            return {
                "response_type": "breakdown_cancelled",
                "message": "Task breakdown cancelled. Let me know if you need anything else!",
            }

        # Handle invalid responses
        return {
            "response_type": "invalid_breakdown_response",
            "message": "Please choose to either create the subtasks, edit them, or cancel:",
            "actions": [
                {"label": "✓ Create all", "value": "create_all"},
                {"label": "✏️ Edit first", "value": "edit"},
                {"label": "❌ Cancel", "value": "cancel"},
            ],
        }

    def _generate_subtasks(self, task_description: str) -> list[str]:
        """
        Generate subtasks for a complex task using Claude or OpenAI.

        Args:
            task_description: The task description

        Returns:
            List of subtask descriptions
        """
        ai_service = self._get_ai_service()
        if not ai_service:
            return []

        try:
            if self.claude_service:
                # Use Claude's built-in method
                subtasks = self.claude_service.generate_subtasks(task_description)
            else:
                # Use OpenAI with prompt
                prompt = f"""
                Break down this complex task into 3-5 smaller, actionable subtasks according to GTD principles:

                Complex task: "{task_description}"

                Requirements:
                - Each subtask should be a clear next action
                - Start with research/planning tasks if needed
                - Include implementation tasks
                - End with review/finalization tasks
                - Each subtask should take 2-30 minutes
                - Use specific action verbs

                Examples:
                For "build cash flow forecast for client":
                - Review client's historical financial data
                - Create cash flow forecast template in Excel
                - Input revenue projections for next 12 months
                - Calculate expense projections based on historicals
                - Review forecast with team and finalize

                Return only the list of subtasks, one per line, without numbering or bullet points."""

                response = self.openai_service.generate_text(prompt)
                subtasks = [line.strip() for line in response.strip().split("\n") if line.strip()]

            return subtasks
        except Exception as e:
            self.logger.error(f"Error generating subtasks: {e}")
            return []

    def _review_tasks(self, user_id: str) -> dict[str, Any]:
        """
        Review current tasks.

        Args:
            user_id: The user ID

        Returns:
            Response data
        """
        try:
            # Get tasks by time estimate
            tasks_by_estimate = {
                "2min": self.todoist_service.get_tasks_by_label("2min"),
                "10min": self.todoist_service.get_tasks_by_label("10min"),
                "30+min": self.todoist_service.get_tasks_by_label("30+min"),
                "untagged": self.todoist_service.get_tasks_without_time_estimate(),
            }

            # Count tasks in each category
            counts = {category: len(tasks) for category, tasks in tasks_by_estimate.items()}

            return {
                "response_type": "task_review",
                "tasks_by_estimate": tasks_by_estimate,
                "counts": counts,
                "message": "Here are your current tasks by time estimate:",
            }
        except Exception as e:
            self.logger.error(f"Error reviewing tasks: {e}")
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't retrieve your tasks. Please try again.",
            }

    def _is_likely_project(self, text: str) -> tuple[bool, str]:
        """
        Determine if a task description sounds like a project.

        Args:
            text: The task description

        Returns:
            Tuple of (is_project: bool, reason: str)
        """
        prompt = f"""
        Analyze this task description and determine if it sounds more like a project (multiple steps/phases) or a single task.

        Task: "{text}"

        Consider these specific factors:
        1. Does it involve multiple distinct steps or phases? (e.g., research, design, build, test)
        2. Would it typically take more than 2-3 hours to complete?
        3. Does it require creating something substantial from scratch?
        4. Common project indicators:
           - "build/create/develop" + "system/app/website/forecast/model/plan"
           - "redesign/refactor/migrate/implement" + major component
           - "establish/set up" + process/workflow/system
           - Words like "entire", "complete", "full", "comprehensive"
        5. Examples that ARE projects:
           - "build cash flow forecast for client"
           - "create new website for company"
           - "develop marketing strategy"
           - "implement new CRM system"
        6. Examples that are NOT projects:
           - "review cash flow spreadsheet"
           - "update website contact page"
           - "send marketing email"
           - "add user to CRM"
           - "system", "platform", "website", "application"
           - "strategy", "framework", "infrastructure"

        Respond in this exact format:
        IS_PROJECT: true/false
        REASON: One clear sentence explaining why, mentioning specific phases or components if relevant
        """

        ai_service = self._get_ai_service()
        if not ai_service:
            return False, "AI service not available for project detection"

        try:
            if self.claude_service:
                response = self.claude_service.generate_text(prompt, max_tokens=200)
            else:
                response = self.openai_service.generate_text(prompt)

            lines = response.strip().split("\n")

            is_project = False
            reason = "This appears to be a single task."

            for line in lines:
                if line.startswith("IS_PROJECT:"):
                    is_project = "true" in line.lower()
                elif line.startswith("REASON:"):
                    reason = line[7:].strip()

            # Enhance the reason if it's a website-related project
            if is_project and any(
                word in text.lower() for word in ["website", "web", "site", "redesign"]
            ):
                reason += " It would typically involve requirements gathering, design mockups, development, testing, and deployment phases."

            return is_project, reason

        except Exception as e:
            self.logger.error(f"Error determining if task is a project: {e}")
            return False, "Could not analyze task complexity"

    def _create_project(self, name: str, user_id: str) -> dict[str, Any]:
        """
        Create a new project in Todoist.

        Args:
            name: Project name
            user_id: The user ID

        Returns:
            Response data
        """
        try:
            # Format project name
            formatted_name = self._format_project_name(name)

            # Create project
            project = self.todoist_service.create_project(formatted_name)

            if not project:
                return {
                    "response_type": "error",
                    "message": "Sorry, I couldn't create the project. Please try again.",
                }

            return {
                "response_type": "project_created",
                "project_id": project["id"],
                "project_name": project["name"],
                "message": f"Created project: {project['name']}\n\nWould you like me to help break this down into tasks?",
                "actions": [
                    {"label": "✓ Break down now", "value": "break_down"},
                    {"label": "⏳ Later", "value": "later"},
                ],
            }

        except Exception as e:
            self.logger.error(f"Error creating project: {e}")
            return {
                "response_type": "error",
                "message": "Sorry, I encountered an error while creating the project.",
            }

    def _format_project_name(self, name: str) -> str:
        """
        Format a project name according to best practices.

        Args:
            name: Original project name

        Returns:
            Formatted project name
        """
        prompt = f"""
        Format this project name according to best practices:

        Original name: "{name}"

        Guidelines:
        1. Use title case
        2. Remove unnecessary words like "Project" unless part of the actual name
        3. Keep it concise but descriptive
        4. Ensure it starts with a meaningful word (not "The", "A", etc.)

        Return only the formatted name without explanation.
        """

        ai_service = self._get_ai_service()
        if not ai_service:
            return name  # Fallback to original if no AI service

        try:
            if self.claude_service:
                # Use Claude's generate_text with a simple prompt
                formatted = self.claude_service.generate_text(prompt, max_tokens=50).strip()
            else:
                formatted = self.openai_service.generate_text(prompt).strip()
            return formatted or name  # Fallback to original if formatting fails
        except Exception as e:
            self.logger.error(f"Error formatting project name: {e}")
            return name

    def _handle_project_response(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Handle response to project detection (whether to break down or create as task).

        Args:
            text: The user's response
            context: Conversation context

        Returns:
            Response data
        """
        text_lower = text.lower().strip()
        pending_task = context.get("pending_task")

        # Debug logging
        self.logger.info(f"_handle_project_response: context keys = {list(context.keys())}")
        self.logger.info(f"_handle_project_response: pending_task = {pending_task}")

        if not pending_task:
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't find the task details. Please try creating your task again.",
            }

        # Clear the context
        context["expecting_project_response"] = False

        if text_lower in ["yes", "break it down", "breakdown", "yes, break it down"]:
            # Break down the task into subtasks
            return self._break_down_task(pending_task, context.get("user_id"))

        elif text_lower in ["no", "create as task", "create_task", "no, create as task"]:
            # Create as a single task
            task_data = self.todoist_service.add_task(pending_task)

            if not task_data:
                return {"response_type": "error", "message": "Failed to create task in Todoist."}

            return {
                "response_type": "task_created",
                "task_id": task_data.get("id"),
                "task_content": pending_task,
                "message": f"Created task: {pending_task}",
            }

        # Handle invalid responses
        return {
            "response_type": "invalid_project_response",
            "message": "Please choose how you'd like to handle this:",
            "actions": [
                {"label": "📁 Create as project", "value": "create_project"},
                {"label": "✓ Create as task", "value": "create_task"},
                {"label": "🔄 Break down into tasks", "value": "break_down"},
            ],
        }
