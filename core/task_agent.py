"""
Task agent for FlowCoach.

This module defines the TaskAgent class that handles task management functionality.
"""

import logging
import re
from typing import Dict, Any, Optional, List

from core.base_agent import BaseAgent

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
    
    def __init__(self, config: Dict[str, Any], services: Dict[str, Any]):
        """
        Initialize the task agent.
        
        Args:
            config: Configuration dictionary
            services: Dictionary of service instances
        """
        super().__init__(config, services)
        self.todoist_service = services.get("todoist")
        self.openai_service = services.get("openai")
        
        if not self.todoist_service:
            self.logger.error("Todoist service not available. Task agent functionality will be limited.")
        
        # Task-related keywords for intent detection
        self.task_keywords = [
            "add", "create", "task", "todo", "to-do", "to do", 
            "remind", "remember", "capture", "track", "schedule"
        ]
        
        # Time estimate patterns
        self.time_estimate_patterns = {
            "2min": [r"\b2\s*min", r"\btwo\s*min", r"\bquick\b", r"\bfast\b", r"\bshort\b"],
            "10min": [r"\b10\s*min", r"\bten\s*min", r"\bmedium\b"],
            "30+min": [r"\b30\+?\s*min", r"\bthirty\+?\s*min", r"\blong\b", r"\bbig\b"]
        }
    
    def process_message(self, message: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
        
        # Check if we're in a task creation flow
        if context.get("expecting_time_estimate") and context.get("last_task_id"):
            self.logger.info("Handling time estimate for existing task")
            return self._handle_time_estimate(text, context)
        
        # Check if this is a task creation request
        if self._is_task_creation_request(text):
            self.logger.info("Detected task creation request")
            # Extract the actual task content from the command
            task_content = self._extract_task_content(text)
            self.logger.info(f"Extracted task content: '{task_content}'")
            return self._create_task(task_content, user_id)
        
        # Check if this is a task breakdown request
        if "break down" in text.lower() and "task" in text.lower():
            self.logger.info("Detected task breakdown request")
            return self._break_down_task(text, user_id)
        
        # Check if this is a task review request
        if any(keyword in text.lower() for keyword in ["review", "show", "list"]) and any(keyword in text.lower() for keyword in ["task", "todo", "to-do", "to do"]):
            self.logger.info("Detected task review request")
            return self._review_tasks(user_id)
        
        self.logger.info("No task-related intent detected")
        return None
    
    def get_capabilities(self) -> Dict[str, Any]:
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
                    "examples": ["Add a task to write documentation", "Remind me to call John"]
                },
                {
                    "name": "break_down_task",
                    "description": "Break down a complex task into smaller tasks",
                    "examples": ["Break down the website redesign task"]
                },
                {
                    "name": "review_tasks",
                    "description": "Review current tasks",
                    "examples": ["Show my tasks", "Review my to-dos"]
                }
            ]
        }
    
    def can_handle(self, message: Dict[str, Any]) -> bool:
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
        if any(keyword in text for keyword in ["review", "show", "list"]) and any(keyword in text for keyword in ["task", "todo", "to-do", "to do"]):
            return True
        
        # Check for task breakdown keywords
        if "break down" in text and "task" in text:
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
        text_lower = text.lower()
        
        # Check for explicit task creation keywords at the beginning
        for keyword in ["add", "create", "new task", "remind me"]:
            if text_lower.startswith(keyword):
                return True
        
        # Check for task-like structure (verb + object)
        # This is a simple heuristic and could be improved with NLP
        words = text_lower.split()
        if len(words) >= 2 and words[0].endswith(("e", "ing")):
            return True
        
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
                return text[len(prefix):].strip()
        
        return text
    
    def _create_task(self, text: str, user_id: str) -> Dict[str, Any]:
        """
        Create a new task in Todoist.
        
        Args:
            text: The task description
            user_id: The user ID
            
        Returns:
            Response data
        """
        self.logger.info(f"Creating task: '{text}'")
        
        # Format task according to GTD principles if OpenAI is available
        formatted_task = text
        if self.openai_service:
            try:
                formatted_task = self._format_task_with_gtd(text)
                # Remove any quotes that OpenAI might have added
                formatted_task = formatted_task.strip('"').strip("'")
                self.logger.info(f"Formatted task: '{formatted_task}'")
            except Exception as e:
                self.logger.error(f"Error formatting task with GTD: {e}")
        
        # Create task in Todoist
        try:
            task = self.todoist_service.add_task(formatted_task)
            task_id = task.get("id")
            
            # Always ask for time estimate
            return {
                "response_type": "task_created_need_estimate",
                "task_id": task_id,
                "task_content": formatted_task,
                "message": f"Task created: {formatted_task}\nHow long do you think this will take?",
                "actions": [
                    {"label": "[2min]", "value": "2min"},
                    {"label": "[10min]", "value": "10min"},
                    {"label": "[30+min]", "value": "30+min"}
                ]
            }
        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't create the task. Please try again."
            }
    
    def _format_task_with_gtd(self, task_text: str) -> str:
        """
        Format a task according to GTD principles using OpenAI.
        
        Args:
            task_text: Original task text
            
        Returns:
            Formatted task text
        """
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
        
        response = self.openai_service.generate_text(prompt)
        return response.strip()
    
    def _extract_time_estimate(self, text: str) -> Optional[str]:
        """
        Extract time estimate from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Time estimate label or None if not found
        """
        text_lower = text.lower()
        
        for estimate, patterns in self.time_estimate_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return estimate
        
        return None
    
    def _handle_time_estimate(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle time estimate response.
        
        Args:
            text: The user's response
            context: Conversation context
            
        Returns:
            Response data
        """
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
                    {"label": "[30+min]", "value": "30+min"}
                ]
            }
        
        # Apply time estimate to task
        try:
            self._apply_time_estimate(task_id, time_estimate)
            return {
                "response_type": "time_estimate_applied",
                "task_id": task_id,
                "time_estimate": time_estimate,
                "message": f"Great! I've tagged '{task_content}' as {time_estimate}."
            }
        except Exception as e:
            self.logger.error(f"Error applying time estimate: {e}")
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't apply the time estimate. The task was created, but not tagged."
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
            content = task['content']
            content = re.sub(r'^\[(2min|10min|30\+min)\]\s*', '', content)
            
            # Add time estimate at the start
            new_content = f"[{time_estimate}] {content}"
            self.logger.info(f"Updating task content to: {new_content}")
            
            # Update the task
            self.todoist_service.update_task(task_id, content=new_content)
            
        except Exception as e:
            self.logger.error(f"Error applying time estimate: {e}")
            raise
    
    def _break_down_task(self, text: str, user_id: str) -> Dict[str, Any]:
        """
        Break down a complex task into smaller tasks.
        
        Args:
            text: The message text
            user_id: The user ID
            
        Returns:
            Response data
        """
        # Extract task ID or description from text
        # This is a placeholder implementation
        task_id = None
        task_description = None
        
        # If we have OpenAI service, use it to break down the task
        if self.openai_service:
            subtasks = self._generate_subtasks(task_description or text)
            
            # Create subtasks in Todoist
            created_tasks = []
            for subtask in subtasks:
                try:
                    task = self.todoist_service.add_task(subtask)
                    created_tasks.append(task)
                except Exception as e:
                    self.logger.error(f"Error creating subtask: {e}")
            
            return {
                "response_type": "tasks_broken_down",
                "subtasks": created_tasks,
                "message": f"I've broken down the task into {len(created_tasks)} subtasks:"
            }
        
        return {
            "response_type": "error",
            "message": "Sorry, I couldn't break down the task. This feature requires OpenAI integration."
        }
    
    def _generate_subtasks(self, task_description: str) -> List[str]:
        """
        Generate subtasks for a complex task using OpenAI.
        
        Args:
            task_description: The task description
            
        Returns:
            List of subtask descriptions
        """
        prompt = f"""
        Break down this complex task into 3-5 smaller, actionable subtasks according to GTD principles:
        
        Complex task: "{task_description}"
        
        For each subtask:
        1. Start with an action verb
        2. Make it specific and clear
        3. Ensure it's achievable in one sitting
        
        Return only the list of subtasks, one per line, without numbering or additional explanation.
        """
        
        response = self.openai_service.generate_text(prompt)
        subtasks = [line.strip() for line in response.strip().split("\n") if line.strip()]
        return subtasks
    
    def _review_tasks(self, user_id: str) -> Dict[str, Any]:
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
                "untagged": self.todoist_service.get_tasks_without_time_estimate()
            }
            
            # Count tasks in each category
            counts = {category: len(tasks) for category, tasks in tasks_by_estimate.items()}
            
            return {
                "response_type": "task_review",
                "tasks_by_estimate": tasks_by_estimate,
                "counts": counts,
                "message": "Here are your current tasks by time estimate:"
            }
        except Exception as e:
            self.logger.error(f"Error reviewing tasks: {e}")
            return {
                "response_type": "error",
                "message": "Sorry, I couldn't retrieve your tasks. Please try again."
            }
