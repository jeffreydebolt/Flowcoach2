"""
Communication agent for FlowCoach.

This module defines the CommunicationAgent class that handles user interactions and messaging.
"""

from typing import Any

from core.base_agent import BaseAgent


class CommunicationAgent(BaseAgent):
    """
    Agent responsible for managing user interactions and communication.

    This agent handles:
    - General conversation and greetings
    - Help requests
    - User feedback
    - Routing messages to other agents based on intent
    """

    def __init__(self, config: dict[str, Any], services: dict[str, Any]):
        """
        Initialize the communication agent.

        Args:
            config: Configuration dictionary
            services: Dictionary of service instances
        """
        super().__init__(config, services)
        self.openai_service = services.get("openai")

        # Communication-related keywords
        self.greeting_keywords = ["hi", "hello", "hey", "yo", "greetings"]
        self.help_keywords = ["help", "guide", "instructions", "what can you do"]
        self.feedback_keywords = ["feedback", "suggestion", "issue", "bug"]

    def process_message(
        self, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Process a communication-related message.

        Args:
            message: The message to process
            context: Additional context for processing

        Returns:
            Optional response data or None if no response
        """
        text = message.get("text", "").strip().lower()
        user_id = message.get("user")

        # Handle greetings
        if any(keyword in text for keyword in self.greeting_keywords) and len(text.split()) <= 3:
            return self._handle_greeting(user_id)

        # Handle help requests
        if any(keyword in text for keyword in self.help_keywords):
            return self._handle_help_request()

        # Handle feedback
        if any(keyword in text for keyword in self.feedback_keywords):
            return self._handle_feedback(text)

        # If no specific communication intent, try general conversation with OpenAI
        if self.openai_service:
            return self._handle_general_conversation(text, user_id, context)

        # Fallback if no other agent handles it and OpenAI is not available
        return {
            "response_type": "fallback",
            "message": 'I understand you sent a message, but I wasn\'t sure how to handle it. Try asking for "help".',
        }

    def get_capabilities(self) -> dict[str, Any]:
        """
        Get the capabilities of this agent.

        Returns:
            Dictionary describing agent capabilities
        """
        return {
            "name": "Communication Agent",
            "description": "Manages user interactions and messaging",
            "commands": [
                {
                    "name": "greeting",
                    "description": "Respond to user greetings",
                    "examples": ["Hi", "Hello there"],
                },
                {
                    "name": "help",
                    "description": "Provide help and usage instructions",
                    "examples": ["Help", "What can you do?"],
                },
                {
                    "name": "feedback",
                    "description": "Handle user feedback or bug reports",
                    "examples": ["I have some feedback", "I found a bug"],
                },
            ],
        }

    def can_handle(self, message: dict[str, Any]) -> bool:
        """
        Determine if this agent can handle the given message.

        This agent acts as a fallback and general conversationalist, so it can handle
        messages not explicitly handled by other agents.

        Args:
            message: The message to check

        Returns:
            True (as it's a general handler)
        """
        # This agent can potentially handle any message not claimed by more specific agents.
        # The decision to handle is made within process_message.
        return True

    def _handle_greeting(self, user_id: str) -> dict[str, Any]:
        """
        Handle user greetings.

        Args:
            user_id: The user ID

        Returns:
            Response data
        """
        # Personalize greeting if user info is available (future enhancement)
        return {
            "response_type": "greeting",
            "message": "Hi there! I'm FlowCoach, your productivity assistant. How can I help you today? 😊",
        }

    def _handle_help_request(self) -> dict[str, Any]:
        """
        Handle help requests.

        Returns:
            Response data
        """
        # Generate help message based on capabilities of all agents (future enhancement)
        help_text = (
            "I can help you manage your tasks using GTD principles! Here are a few things you can ask me:\n"
            '- *Create tasks:* "Add a task to finish the report"\n'
            '- *Review tasks:* "Show my tasks"\n'
            '- *Calendar summary:* "What\'s my schedule today?"\n'
            '- *Find focus time:* "When can I focus today?"\n'
            "Just send me a message in plain language!"
        )
        return {"response_type": "help", "message": help_text}

    def _handle_feedback(self, text: str) -> dict[str, Any]:
        """
        Handle user feedback.

        Args:
            text: The feedback message

        Returns:
            Response data
        """
        self.logger.info(f"Received feedback: {text}")
        # In a real application, this would log feedback to a database or tracking system
        return {
            "response_type": "feedback_received",
            "message": "Thank you for your feedback! I've recorded it.",
        }

    def _handle_general_conversation(
        self, text: str, user_id: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Handle general conversation using OpenAI.

        Args:
            text: The user's message
            user_id: The user ID
            context: Conversation context

        Returns:
            Response data or None if OpenAI fails
        """
        try:
            # Prepare context for OpenAI
            # simplified_context = ... (build context as needed)

            # Generate response
            response_text = self.openai_service.generate_response(text, user_id, context)

            return {"response_type": "general_conversation", "message": response_text}
        except Exception as e:
            self.logger.error(f"Error during general conversation with OpenAI: {e}")
            return {
                "response_type": "error",
                "message": "I'm having a bit of trouble thinking right now. Could you try rephrasing?",
            }
