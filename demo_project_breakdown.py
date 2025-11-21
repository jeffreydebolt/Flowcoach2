#!/usr/bin/env python3
"""
Demo: Project Breakdown Workflow

Demonstrates the complete BMAD-inspired GTD agent ecosystem working together
to transform a complex project into actionable tasks through Natural Planning Model.

Flow: TaskAgent detects complexity → PlanningAgent breaks down → TaskAgent creates tasks → ReviewAgent monitors
"""

import logging
import os
import sys
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.gtd_planning_agent import GTDPlanningAgent
from agents.gtd_review_agent import GTDReviewAgent

# Import agents
from agents.gtd_task_agent import GTDTaskAgent
from framework.agent_registry import AgentRegistry
from framework.context_manager import ContextManager
from framework.workflow_engine import WorkflowEngine
from workflows.project_breakdown import (
    register_project_breakdown_workflow,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ProjectBreakdownDemo:
    """Demonstrate the complete project breakdown workflow."""

    def __init__(self):
        """Initialize demo with all components."""
        # Initialize framework components
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

        # Load agents
        self._load_agents()

        # Register workflow
        self.project_workflow = register_project_breakdown_workflow(
            self.workflow_engine, self.agent_registry, self.context_manager
        )

        # Demo user
        self.demo_user = "demo_user_001"

        logger.info("Project Breakdown Demo initialized")

    def _load_agents(self):
        """Load all GTD agents."""
        try:
            # Load TaskAgent from YAML
            task_agent = GTDTaskAgent.from_yaml("agents/gtd_task_agent.yaml", self.mock_services)
            self.agent_registry.register_agent_instance(task_agent, "gtd-task-agent")

            # Load PlanningAgent from YAML
            planning_agent = GTDPlanningAgent.from_yaml(
                "agents/gtd_planning_agent.yaml", self.mock_services
            )
            self.agent_registry.register_agent_instance(planning_agent, "gtd-planning-agent")

            # Load ReviewAgent from YAML
            review_agent = GTDReviewAgent.from_yaml(
                "agents/gtd_review_agent.yaml", self.mock_services
            )
            self.agent_registry.register_agent_instance(review_agent, "gtd-review-agent")

            logger.info("All GTD agents loaded successfully")

        except Exception as e:
            logger.error(f"Error loading agents: {e}")
            raise

    def run_demo(self):
        """Run the complete project breakdown demo."""
        print("🚀 " + "=" * 60)
        print("    BMAD-INSPIRED GTD AGENT ECOSYSTEM DEMO")
        print("    Project Breakdown Workflow")
        print("=" * 64)
        print()

        # Demo scenarios
        scenarios = [
            {
                "name": "Complex Website Project",
                "request": "I need to launch a new company website with e-commerce functionality, blog, customer portal, and mobile app integration",
                "expected_complexity": "High",
            },
            {
                "name": "Home Office Organization",
                "request": "Organize my home office space including decluttering, setting up productivity systems, and creating a comfortable work environment",
                "expected_complexity": "Medium",
            },
            {
                "name": "Simple Task",
                "request": "Call dentist to schedule appointment",
                "expected_complexity": "Low (should bypass workflow)",
            },
        ]

        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'='*20} SCENARIO {i}: {scenario['name']} {'='*20}")
            print(f"Request: \"{scenario['request']}\"")
            print(f"Expected Complexity: {scenario['expected_complexity']}")
            print("\n" + "-" * 60)

            self._run_scenario(scenario)

            print("\n" + "=" * 80)
            input("\nPress Enter to continue to next scenario...")

        print("\n🎉 Demo completed! All GTD agents working together successfully.")

    def _run_scenario(self, scenario: dict[str, Any]):
        """Run a single demo scenario."""
        request = scenario["request"]

        # Step 1: TaskAgent receives initial request
        print("\n📝 STEP 1: TaskAgent receives complex request")
        task_agent = self.agent_registry.get_agent("gtd-task-agent")

        initial_message = {"text": request, "user": self.demo_user}

        task_response = task_agent.process_message(initial_message, {})
        print(f"TaskAgent Response: {task_response.get('message', 'No message')}")

        # Check if complexity was detected
        if "complex" in task_response.get("message", "").lower() or task_response.get("handoff_to"):
            print("\n🧠 STEP 2: Complexity detected - Starting Project Breakdown Workflow")

            # Start project breakdown workflow
            workflow_response = self.project_workflow.start_project_breakdown(
                initial_request=request, user_id=self.demo_user, source_agent="gtd-task-agent"
            )

            print(f"Workflow Response: {workflow_response.get('message', 'No message')}")

            # If workflow initiated planning, simulate the planning process
            if workflow_response.get("response_type") == "planning_step_1":
                print("\n📋 STEP 3: PlanningAgent - Natural Planning Model Process")
                self._simulate_planning_process(workflow_response)
        else:
            print("\n✅ Simple task detected - handled directly by TaskAgent")

    def _simulate_planning_process(self, initial_planning_response: dict[str, Any]):
        """Simulate the Natural Planning Model process."""
        planning_agent = self.agent_registry.get_agent("gtd-planning-agent")

        # Simulate user responses through the 5-step planning process
        planning_steps = [
            {
                "step": 1,
                "user_input": "This website is important for expanding our business reach and providing better customer experience. Key principles: user-friendly design, fast performance, secure transactions.",
                "description": "Purpose & Principles",
            },
            {
                "step": 2,
                "user_input": "Success looks like: a modern, responsive website that loads in under 3 seconds, processes payments securely, attracts 50% more customers, and showcases our products effectively.",
                "description": "Outcome Visioning",
            },
            {
                "step": 3,
                "user_input": "Research competitors, choose hosting platform, design mockups, write content, set up e-commerce, integrate payment processing, create blog section, build customer portal, mobile optimization, security setup, testing, launch, marketing",
                "description": "Brainstorming",
            },
        ]

        current_context = {}

        for step in planning_steps:
            print(f"\n   Step {step['step']}: {step['description']}")
            print(f"   User Input: \"{step['user_input']}\"")

            # Send user response to planning agent
            step_message = {"text": step["user_input"], "user": self.demo_user}

            response = planning_agent.process_message(step_message, current_context)
            print(f"   Agent Response: {response.get('step', 'Unknown')} - Next action ready")

            # Update context for next step
            current_context.update(response.get("context_update", {}))

        # Simulate organization approval (Step 4)
        print("\n   Step 4: Organization")
        approval_message = {"text": "approve", "user": self.demo_user}

        final_response = planning_agent.process_message(approval_message, current_context)

        if final_response.get("response_type") == "planning_complete":
            print(
                f"   ✅ Planning Complete! {len(final_response.get('next_actions', []))} next actions identified"
            )

            # Step 4: Handle planning completion through workflow
            print("\n🔄 STEP 4: Workflow handles planning completion")
            completion_response = self.project_workflow.handle_planning_completion(
                user_id=self.demo_user, planning_result=final_response
            )

            if completion_response.get("response_type") == "project_breakdown_complete":
                print(
                    f"✅ {completion_response.get('tasks_created', 0)} tasks created successfully!"
                )

                # Step 5: Optional review scheduling
                print("\n📊 STEP 5: Schedule project review with ReviewAgent")
                review_response = self.project_workflow.handle_workflow_action(
                    user_id=self.demo_user, action="schedule_project_review"
                )

                if review_response.get("response_type") == "review_scheduled":
                    print("✅ Project review scheduled with ReviewCoach")

                # Complete workflow
                completion = self.project_workflow.handle_workflow_action(
                    user_id=self.demo_user, action="complete_workflow"
                )

                if completion.get("response_type") == "workflow_complete":
                    print("🎯 Workflow completed successfully!")


# Mock services for demo
class MockTodoistService:
    """Mock Todoist service for demo."""

    def create_task(self, content: str, **kwargs):
        return {"id": "mock_task_123", "content": content, "created": True}

    def get_projects(self):
        return [{"id": "project_1", "name": "Personal"}, {"id": "project_2", "name": "Work"}]


class MockOpenAIService:
    """Mock OpenAI service for demo."""

    def generate_tasks(self, prompt: str):
        return ["Research task 1", "Planning task 2", "Implementation task 3"]


class MockCalendarService:
    """Mock calendar service for demo."""

    def get_events(self, start_date, end_date):
        return [{"title": "Demo Meeting", "start": "2024-01-15T10:00:00"}]


class MockAnalyticsService:
    """Mock analytics service for demo."""

    def get_productivity_stats(self, user_id: str, period: str):
        return {"tasks_completed": 15, "completion_rate": 0.8}


if __name__ == "__main__":
    try:
        demo = ProjectBreakdownDemo()
        demo.run_demo()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user. Goodbye! 👋")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        print("Please check the logs for details.")
