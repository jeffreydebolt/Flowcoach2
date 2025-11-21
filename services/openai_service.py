"""
OpenAI service for FlowCoach.

This module provides a service for interacting with the OpenAI API.
"""

import logging
from typing import Any

from openai import OpenAI


class OpenAIService:
    """Service for interacting with OpenAI API."""

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the OpenAI service.

        Args:
            config: OpenAI configuration
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = config["api_key"]
        self.model = config["model"]
        self.temperature = config["temperature"]

        # Initialize API client
        try:
            self.client = OpenAI(api_key=self.api_key)
            self.logger.info("OpenAI API initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI API: {e}")
            raise

    def generate_text(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Generate text using OpenAI.

        Args:
            prompt: The prompt to generate text from
            max_tokens: Maximum number of tokens to generate

        Returns:
            Generated text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=max_tokens,
            )

            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error generating text with OpenAI: {e}")
            raise

    def generate_response(self, message: str, user_id: str, context: dict[str, Any]) -> str:
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
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": message},
            ]

            # Add conversation history if available
            if "message_history" in context:
                history_messages = self._format_history(context["message_history"])
                # Insert history before the current user message
                messages = messages[:1] + history_messages + messages[1:]

            # Generate response
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=self.temperature, max_tokens=500
            )

            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error generating response with OpenAI: {e}")
            return "I'm having trouble thinking right now. Could you try rephrasing or asking something else?"

    def _create_system_message(self, context: dict[str, Any]) -> str:
        """
        Create a system message with context for OpenAI.

        Args:
            context: Conversation context

        Returns:
            System message
        """
        # Get user name if available
        user_name = context.get("user_name", "there")

        system_message = f"""
        You are FlowCoach, a friendly and helpful productivity assistant focused on GTD (Getting Things Done) methodology.
        
        Current time: {context.get("current_time", "unknown")}
        Current day: {context.get("current_day", "unknown")}
        User name: {user_name}
        
        Your personality:
        - Friendly and supportive
        - Focused on productivity and efficiency
        - Knowledgeable about GTD methodology
        - Concise but helpful
        
        Keep responses brief and actionable. Focus on helping the user be more productive.
        """

        return system_message

    def _format_history(self, history: list[dict[str, Any]]) -> list[dict[str, str]]:
        """
        Format conversation history for OpenAI.

        Args:
            history: Conversation history

        Returns:
            Formatted history
        """
        formatted_history = []

        for entry in history:
            if entry.get("role") in ["user", "assistant", "system"]:
                formatted_history.append({"role": entry["role"], "content": entry["content"]})

        return formatted_history

    def format_task_with_gtd(self, task_text: str) -> str:
        """
        Format a task according to GTD principles.

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

        return self.generate_text(prompt, max_tokens=100)

    def generate_subtasks(self, task_description: str, num_subtasks: int = 5) -> list[str]:
        """
        Generate subtasks for a complex task.

        Args:
            task_description: Complex task description
            num_subtasks: Number of subtasks to generate

        Returns:
            List of subtask descriptions
        """
        prompt = f"""
        Break down this complex task into {num_subtasks} smaller, actionable subtasks according to GTD principles:
        
        Complex task: "{task_description}"
        
        For each subtask:
        1. Start with an action verb
        2. Make it specific and clear
        3. Ensure it's achievable in one sitting
        
        Return only the list of subtasks, one per line, without numbering or additional explanation.
        """

        response = self.generate_text(prompt, max_tokens=500)
        subtasks = [line.strip() for line in response.strip().split("\n") if line.strip()]
        return subtasks

    def suggest_delegation(self, task_description: str) -> dict[str, Any]:
        """
        Suggest whether a task should be delegated.

        Args:
            task_description: Task description

        Returns:
            Dictionary with delegation suggestion
        """
        prompt = f"""
        Analyze this task and determine if it should be delegated:
        
        Task: "{task_description}"
        
        Consider:
        1. Is this task something only the user can do?
        2. Does it require the user's specific expertise?
        3. Is it a high-value use of the user's time?
        
        Respond in JSON format with these fields:
        - should_delegate: true/false
        - reason: brief explanation
        - delegation_suggestion: who or what role might handle this (if should_delegate is true)
        """

        response = self.generate_text(prompt, max_tokens=300)

        # In a real implementation, parse the JSON response
        # For now, return a simple dictionary
        return {
            "should_delegate": "delegate" in response.lower(),
            "reason": response,
            "delegation_suggestion": response,
        }
