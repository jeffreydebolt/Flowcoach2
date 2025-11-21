"""
Agent Registry for managing and discovering agents.

Inspired by BMAD's agent ecosystem, this provides:
- Agent registration and discovery
- Agent capability querying
- Dynamic agent loading
- Agent health monitoring
"""

import importlib
import logging
from pathlib import Path
from typing import Any

import yaml

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for managing agents in the FlowCoach framework.

    Features:
    - Agent registration and discovery
    - Capability-based agent selection
    - Dynamic agent loading from YAML definitions
    - Agent health monitoring
    - Service dependency injection
    """

    def __init__(self, services: dict[str, Any] = None):
        """
        Initialize agent registry.

        Args:
            services: Dictionary of services to inject into agents
        """
        self.services = services or {}
        self.agents: dict[str, BaseAgent] = {}
        self.agent_classes: dict[str, type[BaseAgent]] = {}
        self.agent_configs: dict[str, dict[str, Any]] = {}

        logger.info("AgentRegistry initialized")

    def register_agent_class(self, agent_class: type[BaseAgent], agent_id: str = None):
        """
        Register an agent class.

        Args:
            agent_class: Agent class to register
            agent_id: Optional agent ID (defaults to class name)
        """
        agent_id = agent_id or agent_class.__name__.lower().replace("agent", "")
        self.agent_classes[agent_id] = agent_class
        logger.debug(f"Registered agent class: {agent_id}")

    def register_agent_instance(self, agent: BaseAgent, agent_id: str = None):
        """
        Register an agent instance.

        Args:
            agent: Agent instance to register
            agent_id: Optional agent ID (defaults to agent's ID)
        """
        agent_id = agent_id or agent.agent_id
        self.agents[agent_id] = agent
        logger.info(f"Registered agent instance: {agent_id}")

    def load_agent_from_yaml(
        self, yaml_path: str, agent_class: type[BaseAgent] = None
    ) -> BaseAgent:
        """
        Load agent from YAML definition.

        Args:
            yaml_path: Path to YAML definition file
            agent_class: Optional specific agent class to use

        Returns:
            Loaded agent instance
        """
        yaml_path = Path(yaml_path)

        # Load YAML configuration
        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        agent_config = config.get("agent", {})
        agent_id = agent_config.get("id", yaml_path.stem)

        # Determine agent class
        if agent_class:
            agent_cls = agent_class
        elif agent_id in self.agent_classes:
            agent_cls = self.agent_classes[agent_id]
        else:
            # Try to import agent class dynamically
            class_name = agent_config.get("class")
            if class_name:
                agent_cls = self._import_agent_class(class_name)
            else:
                raise ValueError(f"No agent class specified for {agent_id}")

        # Create agent instance
        agent = agent_cls.from_yaml(str(yaml_path), self.services)

        # Register the agent
        self.register_agent_instance(agent, agent_id)
        self.agent_configs[agent_id] = config

        logger.info(f"Loaded agent from YAML: {agent_id}")
        return agent

    def load_agents_from_directory(self, directory: str, agent_class: type[BaseAgent] = None):
        """
        Load all agents from a directory of YAML files.

        Args:
            directory: Directory containing agent YAML files
            agent_class: Optional default agent class for all agents
        """
        directory = Path(directory)

        for yaml_file in directory.glob("*.yaml"):
            try:
                self.load_agent_from_yaml(str(yaml_file), agent_class)
            except Exception as e:
                logger.error(f"Failed to load agent from {yaml_file}: {e}")

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        """
        Get agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)

    def get_agents_by_capability(self, capability: str) -> list[BaseAgent]:
        """
        Get agents that have a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of agents with the capability
        """
        capable_agents = []

        for agent in self.agents.values():
            if capability in agent.commands:
                capable_agents.append(agent)

        return capable_agents

    def find_agent_for_message(self, message: dict[str, Any]) -> BaseAgent | None:
        """
        Find the best agent to handle a message.

        Args:
            message: Message to be handled

        Returns:
            Best agent for the message or None
        """
        # Try each agent's can_handle method
        for agent in self.agents.values():
            try:
                if agent.can_handle(message):
                    return agent
            except Exception as e:
                logger.error(f"Error checking if {agent.agent_id} can handle message: {e}")

        return None

    def route_message(
        self, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Route a message to the appropriate agent and get response.

        Args:
            message: Message to route
            context: Message context

        Returns:
            Agent response or None if no agent can handle it
        """
        text = message.get("text", "").strip()

        # Handle command routing for *command syntax
        if text.startswith("*"):
            command_text = text[1:]  # Remove the *
            command_parts = command_text.split(" ", 1)
            command_name = command_parts[0]
            command_args = command_parts[1] if len(command_parts) > 1 else ""

            # Try each agent to see if it has this command
            for agent_id, agent in self.agents.items():
                if hasattr(agent, "commands") and command_name in agent.commands:
                    try:
                        logger.info(f"Routing command '{command_name}' to agent '{agent_id}'")
                        return agent.process_message(message, context)
                    except Exception as e:
                        logger.error(
                            f"Error executing command '{command_name}' on agent '{agent_id}': {e}"
                        )
                        return {
                            "response_type": "command_error",
                            "message": f"Error executing {command_name}: {str(e)}",
                        }

            # No agent found for this command
            return {
                "response_type": "unknown_command",
                "message": f"Unknown command: {command_name}. Try 'help' to see available commands.",
            }

        # Handle non-command messages
        agent = self.find_agent_for_message(message)
        if agent:
            try:
                return agent.process_message(message, context)
            except Exception as e:
                logger.error(f"Error processing message with agent '{agent.agent_id}': {e}")
                return {
                    "response_type": "processing_error",
                    "message": f"Error processing your message: {str(e)}",
                }

        return None

    def get_agent_capabilities(self, agent_id: str) -> dict[str, Any] | None:
        """
        Get capabilities of a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent capabilities or None if not found
        """
        agent = self.get_agent(agent_id)
        return agent.get_capabilities() if agent else None

    def list_agents(self) -> list[dict[str, Any]]:
        """
        List all registered agents with their basic info.

        Returns:
            List of agent information dictionaries
        """
        agent_list = []

        for agent_id, agent in self.agents.items():
            agent_list.append(
                {
                    "id": agent_id,
                    "name": agent.name,
                    "title": agent.title,
                    "description": agent.description,
                    "icon": agent.icon,
                    "commands": list(agent.commands.keys()),
                    "status": "active",  # Could be extended with health checks
                }
            )

        return sorted(agent_list, key=lambda x: x["name"])

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check on all agents.

        Returns:
            Health check results
        """
        results = {
            "total_agents": len(self.agents),
            "healthy_agents": 0,
            "unhealthy_agents": 0,
            "agent_status": {},
        }

        for agent_id, agent in self.agents.items():
            try:
                # Basic health check - try to get capabilities
                capabilities = agent.get_capabilities()
                status = "healthy" if capabilities else "unhealthy"
                results["agent_status"][agent_id] = status

                if status == "healthy":
                    results["healthy_agents"] += 1
                else:
                    results["unhealthy_agents"] += 1

            except Exception as e:
                results["agent_status"][agent_id] = f"error: {str(e)}"
                results["unhealthy_agents"] += 1

        return results

    def update_services(self, services: dict[str, Any]):
        """
        Update services for all registered agents.

        Args:
            services: Updated services dictionary
        """
        self.services.update(services)

        # Update services for all agents
        for agent in self.agents.values():
            agent.services.update(services)

        logger.info("Updated services for all agents")

    def remove_agent(self, agent_id: str):
        """
        Remove an agent from the registry.

        Args:
            agent_id: Agent identifier
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Removed agent: {agent_id}")

        if agent_id in self.agent_configs:
            del self.agent_configs[agent_id]

    def _import_agent_class(self, class_path: str) -> type[BaseAgent]:
        """
        Dynamically import an agent class.

        Args:
            class_path: Full class path (e.g., "agents.gtd_task_agent.GTDTaskAgent")

        Returns:
            Agent class
        """
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ValueError, ImportError, AttributeError) as e:
            raise ImportError(f"Could not import agent class {class_path}: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Registry statistics
        """
        total_commands = sum(len(agent.commands) for agent in self.agents.values())

        return {
            "total_agents": len(self.agents),
            "total_agent_classes": len(self.agent_classes),
            "total_commands": total_commands,
            "services_available": list(self.services.keys()),
        }
