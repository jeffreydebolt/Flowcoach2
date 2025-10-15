"""
GTD Task Agent implementation using the FlowCoach Agent Framework.

This agent handles task capture, GTD formatting, and organization following
Getting Things Done principles, built on the BMAD-inspired framework.
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple

from framework.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class GTDTaskAgent(BaseAgent):
    """
    GTD Task Agent for capturing and organizing tasks according to GTD principles.
    
    Capabilities:
    - Natural language task capture
    - GTD formatting and next action creation
    - Time estimation and context assignment
    - Project detection and breakdown suggestions
    - Integration with Todoist for task storage
    """
    
    def __init__(self, config: Dict[str, Any], services: Dict[str, Any] = None):
        """Initialize GTD Task Agent."""
        super().__init__(config, services)
        
        # Get service dependencies
        self.todoist = self.get_service("todoist")
        self.openai = self.get_service("openai")
        
        # GTD configuration
        self.gtd_config = config.get("config", {})
        self.default_context = self.gtd_config.get("default_context", "@next")
        self.default_project = self.gtd_config.get("default_project", "Inbox")
        
        # Time estimation thresholds
        time_config = self.gtd_config.get("time_estimates", {})
        self.quick_threshold = time_config.get("quick_threshold", 5)
        self.medium_threshold = time_config.get("medium_threshold", 30)
        
        # Project detection
        self.project_detection = self.gtd_config.get("project_detection", {})
        self.project_keywords = self.project_detection.get("keywords", [])
        
        # Task patterns for message recognition
        self.message_patterns = config.get("message_patterns", {})
        
        if not self.todoist:
            self.logger.warning("Todoist service not available. Task creation will be limited.")
    
    def can_handle(self, message: Dict[str, Any]) -> bool:
        """
        Determine if this agent can handle the given message.
        
        Checks for:
        - Task creation patterns
        - Time estimation requests
        - GTD-related keywords
        - Action verbs with objects
        """
        text = message.get("text", "").strip().lower()
        
        if not text:
            return False
        
        # Check task creation patterns
        task_patterns = self.message_patterns.get("task_creation", [])
        for pattern in task_patterns:
            if isinstance(pattern, str):
                if pattern in text:
                    return True
            elif isinstance(pattern, dict) and "regex" in pattern:
                if re.search(pattern["regex"], text):
                    return True
        
        # Check for action verbs at the beginning
        action_verbs = [
            "call", "email", "write", "read", "buy", "make", "plan", "do", "get", "find",
            "create", "build", "review", "update", "prepare", "gather", "collect", "finish",
            "complete", "schedule", "book", "arrange", "setup", "configure", "install"
        ]
        
        first_word = text.split()[0] if text.split() else ""
        if first_word in action_verbs:
            return True
        
        # Check for GTD context indicators
        context_patterns = self.message_patterns.get("context_indicators", [])
        for pattern in context_patterns:
            if pattern in text:
                return True
        
        return False
    
    def _process_agent_message(self, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message that this agent can handle.
        
        Main entry point for GTD task processing.
        """
        text = message.get("text", "").strip()
        user_id = message.get("user", "unknown")
        
        # Check if we're in a specific flow
        if self.get_context("expecting_time_estimate"):
            return self._handle_time_estimate(text, user_id)
        
        if self.get_context("expecting_project_response"):
            return self._handle_project_response(text, user_id)
        
        # Check for multiple tasks
        tasks = self._extract_multiple_tasks(text)
        if len(tasks) > 1:
            return self._create_multiple_tasks(tasks, user_id)
        
        # Check for project breakdown request
        if self._is_project_breakdown_request(text):
            return self._suggest_project_breakdown(text, user_id)
        
        # Handle single task creation
        return self._create_single_task(text, user_id)
    
    # Command implementations (called via *command syntax)
    
    def cmd_capture(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle *capture command."""
        user_id = message.get("user", "unknown")
        return self._create_single_task(args, user_id)
    
    def cmd_format_gtd(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle *format-gtd command - show formatting without creating."""
        formatted_task = self._format_as_next_action(args)
        time_estimate = self._suggest_time_estimate(args)
        context_suggestion = self._suggest_context(args)
        
        return {
            "response_type": "gtd_preview",
            "original": args,
            "formatted": formatted_task,
            "time_estimate": time_estimate,
            "context": context_suggestion,
            "message": f"GTD Format Preview:\n**Original:** {args}\n**Formatted:** {formatted_task}\n**Suggested:** {time_estimate}, {context_suggestion}"
        }
    
    def cmd_project_check(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle *project-check command."""
        is_project, reason = self._is_likely_project(args)
        
        return {
            "response_type": "project_analysis",
            "task": args,
            "is_project": is_project,
            "reason": reason,
            "message": f"**Task:** {args}\n**Project?** {'Yes' if is_project else 'No'}\n**Reason:** {reason}"
        }
    
    def cmd_bulk_add(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle *bulk-add command."""
        user_id = message.get("user", "unknown")
        tasks = self._extract_multiple_tasks(args)
        
        if len(tasks) <= 1:
            return {
                "response_type": "bulk_add_error",
                "message": "Please provide multiple tasks. Example: *bulk-add 1) Call dentist 2) Buy groceries"
            }
        
        return self._create_multiple_tasks(tasks, user_id)
    
    # Core GTD processing methods
    
    def _create_single_task(self, task_text: str, user_id: str) -> Dict[str, Any]:
        """Create a single task with GTD formatting."""
        self.logger.info(f"Creating single task: '{task_text}' for user {user_id}")
        
        # Clean and format the task
        cleaned_task = self._clean_task_text(task_text)
        formatted_task = self._format_as_next_action(cleaned_task)
        
        # Extract or suggest GTD attributes
        time_estimate = self._extract_time_estimate(formatted_task)
        if not time_estimate:
            time_estimate = self._suggest_time_estimate(formatted_task)
        
        context = self._extract_context(formatted_task)
        if not context:
            context = self._suggest_context(formatted_task)
        
        # Check if this might be a project
        if time_estimate == "30+min" and self.project_detection.get("enabled", True):
            is_project, reason = self._is_likely_project(formatted_task)
            if is_project:
                return self._suggest_project_breakdown(formatted_task, user_id, reason)
        
        # Create task in Todoist
        if self.todoist:
            try:
                task_data = self._create_todoist_task(formatted_task, time_estimate, context)
                return {
                    "response_type": "task_created",
                    "task_id": task_data.get("id"),
                    "task_content": formatted_task,
                    "time_estimate": time_estimate,
                    "context": context,
                    "message": f"✅ Created: **{formatted_task}** ({time_estimate}, {context})"
                }
            except Exception as e:
                self.logger.error(f"Error creating task in Todoist: {e}")
                return {
                    "response_type": "task_creation_error",
                    "message": f"Failed to create task: {str(e)}"
                }
        
        # Fallback if no Todoist service
        return {
            "response_type": "task_formatted",
            "task_content": formatted_task,
            "time_estimate": time_estimate,
            "context": context,
            "message": f"📝 Formatted: **{formatted_task}** ({time_estimate}, {context})\n_Note: Todoist not available_"
        }
    
    def _create_multiple_tasks(self, tasks: List[str], user_id: str) -> Dict[str, Any]:
        """Create multiple tasks."""
        created_tasks = []
        failed_tasks = []
        
        for task_text in tasks:
            try:
                result = self._create_single_task(task_text, user_id)
                if result["response_type"] == "task_created":
                    created_tasks.append(result["task_content"])
                else:
                    failed_tasks.append(task_text)
            except Exception as e:
                self.logger.error(f"Error creating task '{task_text}': {e}")
                failed_tasks.append(task_text)
        
        message_parts = []
        if created_tasks:
            task_list = "\n".join(f"✅ {task}" for task in created_tasks)
            message_parts.append(f"Created {len(created_tasks)} tasks:\n{task_list}")
        
        if failed_tasks:
            failed_list = "\n".join(f"❌ {task}" for task in failed_tasks)
            message_parts.append(f"\nFailed to create {len(failed_tasks)} tasks:\n{failed_list}")
        
        return {
            "response_type": "multiple_tasks_created",
            "created_count": len(created_tasks),
            "failed_count": len(failed_tasks),
            "message": "\n".join(message_parts)
        }
    
    def _extract_multiple_tasks(self, text: str) -> List[str]:
        """Extract multiple tasks from text."""
        tasks = []
        
        # Try numbered lists first
        numbered_pattern = r'\d+[\.\)]'
        parts = re.split(numbered_pattern, text)
        
        if len(parts) > 2:  # Header + 2+ tasks
            for part in parts[1:]:
                cleaned = part.strip()
                if cleaned:
                    tasks.append(cleaned)
            return tasks
        
        # Try bullet points
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^[-\*•]\s+', line):
                task = re.sub(r'^[-\*•]\s+', '', line).strip()
                if task:
                    tasks.append(task)
        
        if len(tasks) > 1:
            return tasks
        
        # Try "then" separation
        if " then " in text.lower():
            tasks = [t.strip() for t in text.split(" then ") if t.strip()]
        
        return tasks if len(tasks) > 1 else [text]
    
    def _format_as_next_action(self, task_text: str) -> str:
        """Format task as a GTD next action."""
        # Remove common prefixes
        prefixes = ["create a task to", "add task to", "remind me to", "i need to", "i want to"]
        task_lower = task_text.lower()
        
        for prefix in prefixes:
            if task_lower.startswith(prefix):
                task_text = task_text[len(prefix):].strip()
                break
        
        # Ensure it starts with an action verb
        words = task_text.split()
        if not words:
            return task_text
        
        first_word = words[0].lower()
        action_verbs = [
            "call", "email", "write", "read", "buy", "make", "plan", "do", "get", "find",
            "create", "build", "review", "update", "prepare", "gather", "collect", "finish",
            "complete", "schedule", "book", "arrange", "setup", "configure", "install"
        ]
        
        if first_word not in action_verbs:
            # Try to infer action verb
            if "meeting" in task_text.lower() or "appointment" in task_text.lower():
                task_text = f"Schedule {task_text}"
            elif any(word in task_text.lower() for word in ["email", "mail", "message"]):
                task_text = f"Send {task_text}"
            elif any(word in task_text.lower() for word in ["call", "phone", "ring"]):
                task_text = f"Call {task_text}"
            else:
                task_text = f"Do {task_text}"
        
        return task_text.capitalize()
    
    def _extract_time_estimate(self, text: str) -> Optional[str]:
        """Extract explicit time estimate from task text."""
        # Look for explicit time patterns
        patterns = {
            "2min": [r"\b2\s*min", r"\bquick\b", r"\bfast\b", r"\b2m\b"],
            "10min": [r"\b10\s*min", r"\b15\s*min", r"\bmedium\b"],
            "30+min": [r"\b30\+?\s*min", r"\b1\s*hour", r"\blong\b", r"\bhour"]
        }
        
        text_lower = text.lower()
        for estimate, regex_list in patterns.items():
            for pattern in regex_list:
                if re.search(pattern, text_lower):
                    return estimate
        
        return None
    
    def _suggest_time_estimate(self, text: str) -> str:
        """Suggest time estimate based on task complexity."""
        word_count = len(text.split())
        
        # Simple heuristics based on task description
        if word_count <= 4:
            return "2min"
        elif word_count <= 8:
            return "10min"
        else:
            return "30+min"
    
    def _extract_context(self, text: str) -> Optional[str]:
        """Extract GTD context from task text."""
        contexts = {
            "@computer": ["computer", "laptop", "online", "internet", "email", "type", "code"],
            "@phone": ["call", "phone", "ring", "contact", "speak"],
            "@office": ["office", "work", "meeting", "colleague", "boss"],
            "@home": ["home", "house", "family", "personal"],
            "@errands": ["buy", "shop", "store", "bank", "post office", "pick up"],
            "@anywhere": ["read", "think", "plan", "brainstorm", "review"]
        }
        
        text_lower = text.lower()
        for context, keywords in contexts.items():
            if any(keyword in text_lower for keyword in keywords):
                return context
        
        return None
    
    def _suggest_context(self, text: str) -> str:
        """Suggest GTD context for a task."""
        extracted = self._extract_context(text)
        return extracted or self.default_context
    
    def _is_likely_project(self, text: str) -> Tuple[bool, str]:
        """Determine if task is likely a project."""
        text_lower = text.lower()
        
        # Check for project keywords
        project_indicators = self.project_keywords + [
            "build", "create", "develop", "design", "implement", "plan", 
            "organize", "setup", "establish", "launch", "complete"
        ]
        
        has_project_keyword = any(keyword in text_lower for keyword in project_indicators)
        
        # Check complexity indicators
        complexity_words = ["entire", "complete", "full", "comprehensive", "system", "website", "application"]
        has_complexity = any(word in text_lower for word in complexity_words)
        
        word_count = len(text.split())
        is_complex = word_count > 6
        
        if has_project_keyword and (has_complexity or is_complex):
            reason = f"Contains project keyword '{next(k for k in project_indicators if k in text_lower)}'"
            if has_complexity:
                reason += " and complexity indicators"
            return True, reason
        
        return False, "Appears to be a single action item"
    
    def _is_project_breakdown_request(self, text: str) -> bool:
        """Check if user is asking for project breakdown."""
        breakdown_phrases = ["break down", "breakdown", "split into", "divide into", "steps for"]
        return any(phrase in text.lower() for phrase in breakdown_phrases)
    
    def _suggest_project_breakdown(self, task: str, user_id: str, reason: str = None) -> Dict[str, Any]:
        """Suggest breaking down a task into a project."""
        return {
            "response_type": "project_suggestion",
            "task": task,
            "reason": reason or "Task appears complex and may benefit from breakdown",
            "message": f"🎯 **Project Detected:** {task}\n\n{reason}\n\nWould you like me to break this down into smaller tasks?",
            "actions": [
                {"label": "📋 Break it down", "value": "breakdown"},
                {"label": "✅ Keep as single task", "value": "single_task"}
            ],
            "context_update": {
                "pending_task": task,
                "expecting_project_response": True
            }
        }
    
    def _handle_project_response(self, response: str, user_id: str) -> Dict[str, Any]:
        """Handle user response to project suggestion."""
        response_lower = response.lower().strip()
        pending_task = self.get_context("pending_task", "")
        
        self.update_context({"expecting_project_response": False})
        
        if response_lower in ["breakdown", "break it down", "yes", "y"]:
            # Hand off to planning agent
            return self.handoff_to("gtd-planning-agent", {
                "task": pending_task,
                "user_id": user_id,
                "source": "project_detection"
            }, f"Breaking down project: {pending_task}")
        
        elif response_lower in ["single_task", "keep as task", "no", "n"]:
            # Create as single task
            return self._create_single_task(pending_task, user_id)
        
        return {
            "response_type": "unclear_response",
            "message": "Please choose 'breakdown' to split into tasks or 'single task' to keep as is."
        }
    
    def _handle_time_estimate(self, response: str, user_id: str) -> Dict[str, Any]:
        """Handle time estimate response."""
        # Implementation for interactive time estimation
        # This would be called when user is asked to provide time estimate
        pass
    
    def _create_todoist_task(self, task_content: str, time_estimate: str, context: str) -> Dict[str, Any]:
        """Create task in Todoist with GTD formatting."""
        # Format task with time estimate prefix
        formatted_content = f"[{time_estimate}] {task_content}"
        
        # Create task
        task_data = self.todoist.add_task(
            content=formatted_content,
            project=self.default_project,
            labels=[context, time_estimate] if context != self.default_context else [time_estimate]
        )
        
        return task_data
    
    def _clean_task_text(self, text: str) -> str:
        """Clean up task text."""
        return re.sub(r'\s+', ' ', text.strip())