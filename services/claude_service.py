"""
Claude service for FlowCoach.

This module provides a service for interacting with the Anthropic Claude API.
"""

import logging
from typing import Dict, Any, Optional, List

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

class ClaudeService:
    """Service for interacting with Anthropic Claude API."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Claude service.

        Args:
            config: Claude configuration
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = config["api_key"]
        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.temperature = config.get("temperature", 0.7)

        if Anthropic is None:
            raise ImportError("Anthropic SDK not installed. Run: pip install anthropic")

        # Initialize API client
        try:
            self.client = Anthropic(api_key=self.api_key)
            self.logger.info("Claude API initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude API: {e}")
            raise

    def generate_text(self, prompt: str, max_tokens: int = 500, system: Optional[str] = None) -> str:
        """
        Generate text using Claude.

        Args:
            prompt: The prompt to generate text from
            max_tokens: Maximum number of tokens to generate
            system: Optional system message

        Returns:
            Generated text
        """
        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": self.temperature,
                "messages": messages
            }

            if system:
                kwargs["system"] = system

            response = self.client.messages.create(**kwargs)

            # Extract text from response
            if response.content and len(response.content) > 0:
                if hasattr(response.content[0], 'text'):
                    return response.content[0].text
                elif isinstance(response.content[0], dict) and 'text' in response.content[0]:
                    return response.content[0]['text']

            return str(response.content[0]) if response.content else ""
        except Exception as e:
            self.logger.error(f"Error generating text with Claude: {e}")
            raise

    def generate_response(self, message: str, user_id: str, context: Dict[str, Any]) -> str:
        """
        Generate a response to a user message with context.

        Args:
            message: User message
            user_id: User ID
            context: Conversation context

        Returns:
            Generated response
        """
        try:
            # Create system message with context
            system_message = self._create_system_message(context)

            # Create messages array
            messages = [{"role": "user", "content": message}]

            # Add conversation history if available
            if "message_history" in context:
                history_messages = self._format_history(context["message_history"])
                messages = history_messages + messages

            # Generate response
            response = self.client.messages.create(
                model=self.model,
                messages=messages,
                system=system_message,
                temperature=self.temperature,
                max_tokens=500
            )

            # Extract text from response
            if response.content and len(response.content) > 0:
                if hasattr(response.content[0], 'text'):
                    return response.content[0].text
                elif isinstance(response.content[0], dict) and 'text' in response.content[0]:
                    return response.content[0]['text']

            return str(response.content[0]) if response.content else ""
        except Exception as e:
            self.logger.error(f"Error generating response with Claude: {e}")
            return "I'm having trouble thinking right now. Could you try rephrasing or asking something else?"

    def _create_system_message(self, context: Dict[str, Any]) -> str:
        """
        Create a system message with context for Claude.

        Args:
            context: Conversation context

        Returns:
            System message
        """
        # Get user name if available
        user_name = context.get("user_name", "there")

        system_message = f"""You are FlowCoach, a friendly and helpful productivity assistant focused on GTD (Getting Things Done) methodology.

Current time: {context.get("current_time", "unknown")}
Current day: {context.get("current_day", "unknown")}
User name: {user_name}

Your personality:
- Friendly and supportive
- Focused on productivity and efficiency
- Knowledgeable about GTD methodology
- Concise but helpful

Keep responses brief and actionable. Focus on helping the user be more productive."""

        return system_message

    def _format_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Format conversation history for Claude.

        Args:
            history: Conversation history

        Returns:
            Formatted history
        """
        formatted_history = []

        for entry in history:
            role = entry.get("role", "user")
            if role in ["user", "assistant"]:
                formatted_history.append({
                    "role": role,
                    "content": entry.get("content", "")
                })

        return formatted_history

    def format_task_with_gtd(self, task_text: str) -> str:
        """
        Format a task according to GTD principles using Claude.

        Args:
            task_text: Original task text

        Returns:
            Formatted task text
        """
        system_prompt = """You are a GTD (Getting Things Done) task formatting assistant.
Your job is to reformat task descriptions to be clear, actionable, and follow GTD principles.
Return ONLY the reformatted task text without any additional explanation or commentary."""

        prompt = f"""Reformat this task description according to Getting Things Done (GTD) principles:

Original task: "{task_text}"

A good GTD task should:
1. Start with an action verb
2. Be specific and clear
3. Be achievable in one sitting
4. Include context if appropriate

Return only the reformatted task text without additional explanation."""

        return self.generate_text(prompt, max_tokens=100, system=system_prompt)

    def generate_subtasks(self, task_description: str, num_subtasks: int = 5) -> List[str]:
        """
        Generate subtasks for a complex task using Claude.

        Args:
            task_description: Complex task description
            num_subtasks: Number of subtasks to generate

        Returns:
            List of subtask descriptions
        """
        system_prompt = """You are a GTD task breakdown assistant.
Break down complex tasks into smaller, actionable subtasks.
Return only the list of subtasks, one per line, without numbering or additional explanation."""

        prompt = f"""Break down this complex task into {num_subtasks} smaller, actionable subtasks according to GTD principles:

Complex task: "{task_description}"

For each subtask:
1. Start with an action verb
2. Make it specific and clear
3. Ensure it's achievable in one sitting

Return only the list of subtasks, one per line, without numbering or additional explanation."""

        response = self.generate_text(prompt, max_tokens=500, system=system_prompt)
        subtasks = [line.strip() for line in response.strip().split("\n") if line.strip()]
        return subtasks
