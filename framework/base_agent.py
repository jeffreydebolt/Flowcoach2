"""
Base Agent class inspired by BMAD-METHOD patterns.

Provides the foundational architecture for declarative, command-driven agents
with YAML-based configuration and workflow integration.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the FlowCoach framework.

    Inspired by BMAD's agent architecture, this provides:
    - YAML-based agent definitions
    - Command registration and routing
    - Context management
    - Agent collaboration patterns
    - Dependency injection
    """

    def __init__(self, config: dict[str, Any], services: dict[str, Any] = None):
        """
        Initialize agent with configuration and services.

        Args:
            config: Agent configuration dictionary
            services: Dictionary of available services (Todoist, Slack, etc.)
        """
        self.config = config or {}
        self.services = services or {}
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        # Core agent properties from config
        self.agent_id = self.config.get("id", self.__class__.__name__.lower())
        self.name = self.config.get("name", self.__class__.__name__)
        self.title = self.config.get("title", "Agent")
        self.description = self.config.get("description", "")
        self.icon = self.config.get("icon", "🤖")

        # Command registry
        self.commands: dict[str, Callable] = {}
        self.command_metadata: dict[str, dict[str, Any]] = {}

        # Dependencies and context
        self.dependencies = self.config.get("dependencies", {})
        self.context_data = {}
        self.conversation_state = {}

        # Initialize agent
        self._register_commands()
        self.logger.info(f"Initialized {self.name} ({self.agent_id})")

    @classmethod
    def from_yaml(cls, yaml_path: str, services: dict[str, Any] = None) -> "BaseAgent":
        """
        Create agent instance from YAML definition file.

        Args:
            yaml_path: Path to agent YAML definition
            services: Dictionary of available services

        Returns:
            Configured agent instance
        """
        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        # Extract agent configuration
        agent_config = config.get("agent", {})
        agent_config.update(
            {
                "commands": config.get("commands", []),
                "dependencies": config.get("dependencies", {}),
                "persona": config.get("persona", {}),
                "workflows": config.get("workflows", []),
            }
        )

        return cls(agent_config, services)

    def _register_commands(self):
        """Register commands from agent configuration."""
        commands_config = self.config.get("commands", [])

        for cmd_config in commands_config:
            if isinstance(cmd_config, str):
                # Simple command name
                cmd_name = cmd_config
                cmd_meta = {"description": f"Execute {cmd_name}"}
            elif isinstance(cmd_config, dict):
                # Command with metadata
                cmd_name = cmd_config.get("name")
                cmd_meta = {
                    "description": cmd_config.get("description", f"Execute {cmd_name}"),
                    "examples": cmd_config.get("examples", []),
                    "parameters": cmd_config.get("parameters", []),
                }
            else:
                continue

            if not cmd_name:
                continue

            # Try to find corresponding method
            method_name = f"cmd_{cmd_name.replace('-', '_')}"
            if hasattr(self, method_name):
                self.commands[cmd_name] = getattr(self, method_name)
                self.command_metadata[cmd_name] = cmd_meta
                self.logger.debug(f"Registered command: {cmd_name}")

    def activate(self, initial_message: str = None) -> dict[str, Any]:
        """
        Activate the agent (BMAD-inspired activation pattern).

        Args:
            initial_message: Optional initial message to process

        Returns:
            Activation response with greeting and available commands
        """
        self.logger.info(f"Activating {self.name}")

        # Construct greeting
        greeting = f"Hello! I'm {self.name} ({self.icon}), your {self.title}."
        if self.description:
            greeting += f" {self.description}"

        # Show available commands
        commands_list = []
        for cmd_name, cmd_meta in self.command_metadata.items():
            desc = cmd_meta.get("description", "")
            commands_list.append(f"*{cmd_name}*: {desc}")

        if commands_list:
            greeting += "\n\nAvailable commands:\n" + "\n".join(commands_list)

        response = {
            "response_type": "agent_activated",
            "agent_id": self.agent_id,
            "message": greeting,
            "commands": list(self.commands.keys()),
        }

        # Process initial message if provided
        if initial_message:
            return self.process_message({"text": initial_message}, {})

        return response

    def process_message(self, message: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """
        Process an incoming message (main entry point).

        Args:
            message: Message data (text, user, etc.)
            context: Conversation context

        Returns:
            Response data
        """
        text = message.get("text", "").strip()
        user_id = message.get("user")

        self.logger.info(f"Processing message: '{text}' from user: {user_id}")

        # Update context
        self.context_data.update(context)

        # Check for command invocation (starts with *)
        if text.startswith("*"):
            return self._handle_command(text[1:], message, context)

        # Check if agent can handle this message
        if self.can_handle(message):
            return self._process_agent_message(message, context)

        # Default response
        return {
            "response_type": "unhandled",
            "message": f"I don't understand '{text}'. Try *help for available commands.",
        }

    def _handle_command(
        self, command_text: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle explicit command invocation."""
        parts = command_text.split(" ", 1)
        cmd_name = parts[0]
        cmd_args = parts[1] if len(parts) > 1 else ""

        if cmd_name == "help":
            return self._handle_help()

        if cmd_name in self.commands:
            try:
                return self.commands[cmd_name](cmd_args, message, context)
            except Exception as e:
                self.logger.error(f"Error executing command {cmd_name}: {e}")
                return {
                    "response_type": "command_error",
                    "message": f"Error executing {cmd_name}: {str(e)}",
                }

        return {
            "response_type": "unknown_command",
            "message": f"Unknown command: {cmd_name}. Try *help for available commands.",
        }

    def _handle_help(self) -> dict[str, Any]:
        """Handle help command."""
        if not self.commands:
            return {"response_type": "help", "message": f"{self.name} has no commands available."}

        help_text = f"**{self.name} Commands:**\n"
        for cmd_name, cmd_meta in self.command_metadata.items():
            desc = cmd_meta.get("description", "No description")
            examples = cmd_meta.get("examples", [])
            help_text += f"\n*{cmd_name}*: {desc}"
            if examples:
                help_text += f"\n  Examples: {', '.join(examples)}"

        return {"response_type": "help", "message": help_text}

    def handoff_to(
        self, target_agent_id: str, context: dict[str, Any], message: str = None
    ) -> dict[str, Any]:
        """
        Hand off conversation to another agent (BMAD-inspired collaboration).

        Args:
            target_agent_id: ID of target agent
            context: Context to pass to target agent
            message: Optional message for target agent

        Returns:
            Handoff response
        """
        self.logger.info(f"Handing off to {target_agent_id}")

        return {
            "response_type": "agent_handoff",
            "source_agent": self.agent_id,
            "target_agent": target_agent_id,
            "context": context,
            "message": message or f"Handed off from {self.name}",
            "handoff_message": f"Transferring you to {target_agent_id}...",
        }

    def get_capabilities(self) -> dict[str, Any]:
        """
        Get agent capabilities (BMAD-inspired introspection).

        Returns:
            Dictionary describing agent capabilities
        """
        return {
            "id": self.agent_id,
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "commands": list(self.commands.keys()),
            "dependencies": list(self.dependencies.keys()),
            "can_handle": self.__class__.can_handle.__doc__ or "No description",
        }

    # Abstract methods that subclasses must implement

    @abstractmethod
    def can_handle(self, message: dict[str, Any]) -> bool:
        """
        Determine if this agent can handle the given message.

        Args:
            message: The message to check

        Returns:
            True if this agent can handle the message, False otherwise
        """
        pass

    @abstractmethod
    def _process_agent_message(
        self, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process a message that this agent can handle.

        Args:
            message: The message to process
            context: Conversation context

        Returns:
            Response data
        """
        pass

    # Utility methods for common patterns

    def get_service(self, service_name: str):
        """Get a service dependency."""
        service = self.services.get(service_name)
        if not service:
            self.logger.warning(f"Service {service_name} not available")
        return service

    def update_context(self, updates: dict[str, Any]):
        """Update conversation context."""
        self.context_data.update(updates)

    def get_context(self, key: str, default=None):
        """Get value from conversation context."""
        return self.context_data.get(key, default)
