#!/usr/bin/env python3
"""
Interactive GTD Agent Demo

Run this to interact with the GTD agents directly and see BMAD patterns in action.
This demo lets you type commands and see agent responses in real-time.
"""

import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.gtd_planning_agent import GTDPlanningAgent
from agents.gtd_review_agent import GTDReviewAgent

# Import agents
from agents.gtd_task_agent import GTDTaskAgent
from framework.agent_registry import AgentRegistry
from framework.context_manager import ContextManager
from framework.workflow_engine import WorkflowEngine

# Setup logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise for demo


class InteractiveGTDDemo:
    """Interactive demo of the GTD agent ecosystem."""

    def __init__(self):
        """Initialize the demo environment."""
        # Initialize framework
        self.context_manager = ContextManager()
        self.agent_registry = AgentRegistry()
        self.workflow_engine = WorkflowEngine(self.agent_registry, self.context_manager)

        # Mock services
        self.mock_services = {
            "todoist_service": MockTodoistService(),
            "openai_service": MockOpenAIService(),
            "calendar_service": MockCalendarService(),
            "analytics_service": MockAnalyticsService(),
        }

        # Demo user
        self.user_id = "demo_user"
        self.context = {}

        # Load agents
        self._load_agents()

        print("✅ GTD Agent Ecosystem loaded successfully!")

    def _load_agents(self):
        """Load all GTD agents."""
        # Load TaskAgent
        task_agent = GTDTaskAgent.from_yaml("agents/gtd_task_agent.yaml", self.mock_services)
        self.agent_registry.register_agent_instance(task_agent, "gtd-task-agent")

        # Load PlanningAgent
        planning_agent = GTDPlanningAgent.from_yaml(
            "agents/gtd_planning_agent.yaml", self.mock_services
        )
        self.agent_registry.register_agent_instance(planning_agent, "gtd-planning-agent")

        # Load ReviewAgent
        review_agent = GTDReviewAgent.from_yaml("agents/gtd_review_agent.yaml", self.mock_services)
        self.agent_registry.register_agent_instance(review_agent, "gtd-review-agent")

    def run_interactive_demo(self):
        """Run the interactive demo."""
        self._print_welcome()

        while True:
            try:
                # Get user input
                user_input = input("\n🤖 Enter command (or 'quit' to exit): ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Thanks for trying the GTD Agent Ecosystem!")
                    break

                if not user_input:
                    continue

                # Process the input
                self._process_user_input(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 Demo interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    def _print_welcome(self):
        """Print welcome message and instructions."""
        print("\n" + "=" * 70)
        print("    🚀 GTD AGENT ECOSYSTEM - INTERACTIVE DEMO")
        print("    BMAD-Inspired Multi-Agent Productivity System")
        print("=" * 70)

        print("\n🤖 **Available Agents:**")
        print("   • TaskFlow (gtd-task-agent) - Individual task management")
        print("   • PlanMaster (gtd-planning-agent) - Project breakdown")
        print("   • ReviewCoach (gtd-review-agent) - System maintenance")

        print("\n📋 **Try These Commands:**")
        print("   • *help - Show agent commands")
        print("   • *capture Call dentist for appointment")
        print("   • *breakdown Launch a new website with e-commerce")
        print("   • *weekly-review")
        print("   • hello - Natural language (agent will be selected)")
        print("   • I need to plan a complex project")
        print("   • Time for my weekly review")

        print("\n💡 **BMAD Patterns in Action:**")
        print("   • Commands start with * (BMAD command syntax)")
        print("   • Natural language triggers agent selection")
        print("   • Context preserved across interactions")
        print("   • Agents collaborate through handoffs")

        print("\n" + "=" * 70)

    def _process_user_input(self, user_input: str):
        """Process user input and route to appropriate agent."""
        message = {"text": user_input, "user": self.user_id}

        print(f"\n📝 **Input:** {user_input}")
        print("-" * 50)

        # Check if it's a direct command (starts with *)
        if user_input.startswith("*"):
            # Direct command - try all agents to see who handles it
            response = self._try_command_with_agents(message)
        else:
            # Natural language - find appropriate agent
            agent = self.agent_registry.find_agent_for_message(message)
            if agent:
                print(f"🎯 **Selected Agent:** {agent.name} ({agent.icon})")
                response = agent.process_message(message, self.context)
            else:
                response = {
                    "message": "No agent could handle this message. Try using a command like *help"
                }

        # Display response
        self._display_response(response)

        # Update context if provided
        if isinstance(response, dict) and "context_update" in response:
            self.context.update(response["context_update"])

    def _try_command_with_agents(self, message: dict):
        """Try a command with each agent until one handles it."""
        agents = [
            ("TaskFlow", self.agent_registry.get_agent("gtd-task-agent")),
            ("PlanMaster", self.agent_registry.get_agent("gtd-planning-agent")),
            ("ReviewCoach", self.agent_registry.get_agent("gtd-review-agent")),
        ]

        for agent_name, agent in agents:
            if not agent:
                continue

            # Check if this agent has the command
            command = message["text"][1:].split()[0]  # Remove * and get command name
            if command in agent.commands:
                print(f"🎯 **Executing with:** {agent_name} ({agent.icon})")
                return agent.process_message(message, self.context)

        # No agent handled the command
        return {"message": f"❌ Unknown command: {message['text']}. Try *help with any agent."}

    def _display_response(self, response: dict):
        """Display agent response in a nice format."""
        if not isinstance(response, dict):
            print(f"🤖 **Response:** {response}")
            return

        # Show response type
        response_type = response.get("response_type", "unknown")
        print(f"📋 **Response Type:** {response_type}")

        # Show main message
        message = response.get("message", "No message provided")
        print("\n🤖 **Agent Response:**")
        print("   " + message.replace("\n", "\n   "))

        # Show additional info
        if "workflow" in response:
            workflow = response["workflow"]
            print(
                f"\n🔄 **Workflow:** {workflow.get('name', 'Unknown')} (Step {workflow.get('step', '?')})"
            )

        if "actions" in response:
            actions = response["actions"]
            print("\n⚡ **Available Actions:**")
            for action in actions:
                print(f"   • {action.get('label', action.get('value', 'Unknown'))}")

        if "handoff_to" in response:
            print(f"\n🤝 **Handoff to:** {response['handoff_to']}")

        if "next_actions" in response:
            actions = response["next_actions"]
            print(f"\n📋 **Generated Tasks:** {len(actions)} tasks")
            for i, action in enumerate(actions[:3], 1):  # Show first 3
                content = action.get("content", action.get("description", "Unknown"))
                context = action.get("context", "@unknown")
                estimate = action.get("time_estimate", action.get("estimate", "?"))
                print(f"   {i}. {content} ({estimate}, {context})")
            if len(actions) > 3:
                print(f"   ... and {len(actions) - 3} more tasks")


class MockTodoistService:
    """Mock Todoist service for demo."""

    def __init__(self):
        self.tasks = []
        self.task_counter = 1

    def add_task(self, content: str, **kwargs):
        task = {
            "id": self.task_counter,
            "content": content,
            "project_id": kwargs.get("project_id", "inbox"),
            "labels": kwargs.get("labels", []),
            "created": True,
        }
        self.tasks.append(task)
        self.task_counter += 1
        print(f"   ✅ Created task in Todoist: '{content}'")
        return task

    def create_task(self, content: str, **kwargs):
        return self.add_task(content, **kwargs)

    def get_projects(self):
        return [{"id": "inbox", "name": "Inbox"}, {"id": "work", "name": "Work"}]


class MockOpenAIService:
    """Mock OpenAI service for demo."""

    def generate_tasks(self, prompt: str):
        return ["Generated task 1", "Generated task 2", "Generated task 3"]


class MockCalendarService:
    """Mock calendar service for demo."""

    def get_events(self, start_date, end_date):
        return [
            {"title": "Team Meeting", "start": "2024-01-15T10:00:00"},
            {"title": "Project Review", "start": "2024-01-16T14:00:00"},
        ]


class MockAnalyticsService:
    """Mock analytics service for demo."""

    def get_productivity_stats(self, user_id: str, period: str):
        return {
            "tasks_completed": 15,
            "tasks_created": 20,
            "completion_rate": 0.75,
            "most_productive_context": "@computer",
        }


if __name__ == "__main__":
    try:
        demo = InteractiveGTDDemo()
        demo.run_interactive_demo()
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
