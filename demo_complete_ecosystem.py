#!/usr/bin/env python3
"""
Complete GTD Agent Ecosystem Demo

Demonstrates the full BMAD-inspired GTD agent ecosystem with both:
1. Project Breakdown Workflow (complex task → planning → task creation)
2. Weekly Review Workflow (system maintenance → insights → optimization)

This shows how all three agents (TaskAgent, PlanningAgent, ReviewAgent)
work together through structured workflows following BMAD patterns.
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

# Import workflows
from workflows.project_breakdown import register_project_breakdown_workflow
from workflows.weekly_review import register_weekly_review_workflow

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CompleteGTDEcosystemDemo:
    """Demonstrate the complete BMAD-inspired GTD agent ecosystem."""

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

        # Register workflows
        self.project_workflow = register_project_breakdown_workflow(
            self.workflow_engine, self.agent_registry, self.context_manager
        )

        self.review_workflow = register_weekly_review_workflow(
            self.workflow_engine, self.agent_registry, self.context_manager
        )

        # Demo user
        self.demo_user = "ecosystem_demo_user"

        logger.info("Complete GTD Ecosystem Demo initialized")

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

    def run_complete_demo(self):
        """Run the complete ecosystem demonstration."""
        print("🚀 " + "=" * 70)
        print("    BMAD-INSPIRED GTD AGENT ECOSYSTEM - COMPLETE DEMO")
        print("    Multi-Agent Workflows for Project Management & System Maintenance")
        print("=" * 74)
        print()

        print("This demo showcases two key workflows:")
        print("1. 📋 Project Breakdown Workflow - Transform complex projects into actionable tasks")
        print("2. 🔍 Weekly Review Workflow - Maintain GTD system integrity and insights")
        print()

        # Demo menu
        while True:
            print("\n" + "=" * 50)
            print("Choose a demo workflow:")
            print("1. 📋 Project Breakdown Workflow")
            print("2. 🔍 Weekly Review Workflow")
            print("3. 🎯 Complete Ecosystem (Both workflows)")
            print("4. ❓ Show Agent Capabilities")
            print("5. 🚪 Exit")
            print("=" * 50)

            choice = input("\nEnter your choice (1-5): ").strip()

            if choice == "1":
                self._demo_project_breakdown()
            elif choice == "2":
                self._demo_weekly_review()
            elif choice == "3":
                self._demo_complete_ecosystem()
            elif choice == "4":
                self._show_agent_capabilities()
            elif choice == "5":
                print("\n👋 Thanks for exploring the GTD Agent Ecosystem!")
                break
            else:
                print("❌ Invalid choice. Please try again.")

    def _demo_project_breakdown(self):
        """Demo project breakdown workflow."""
        print("\n📋 " + "=" * 60)
        print("    PROJECT BREAKDOWN WORKFLOW DEMO")
        print("=" * 64)

        project_request = input("\nEnter a complex project to break down: ").strip()
        if not project_request:
            project_request = "Launch a new mobile app with user authentication, push notifications, and social sharing features"

        print(f"\n🎯 **Project:** {project_request}")
        print("\n" + "-" * 60)

        # Start project breakdown
        response = self.project_workflow.start_project_breakdown(
            initial_request=project_request, user_id=self.demo_user, source_agent="demo"
        )

        print("\n🤖 **Workflow Response:**")
        print(response.get("message", "No message"))

        if response.get("response_type") == "planning_step_1":
            print("\n✅ Project breakdown workflow initiated successfully!")
            print("📋 PlanningAgent is ready to guide you through Natural Planning Model")

            # Simulate quick planning completion for demo
            self._simulate_quick_planning(project_request)

    def _demo_weekly_review(self):
        """Demo weekly review workflow."""
        print("\n🔍 " + "=" * 60)
        print("    WEEKLY REVIEW WORKFLOW DEMO")
        print("=" * 64)

        print("\nStarting GTD Weekly Review workflow...")

        # Start weekly review
        response = self.review_workflow.start_weekly_review(
            user_id=self.demo_user, review_type="full", scheduled=False
        )

        print("\n🤖 **Review Agent Response:**")
        print(response.get("message", "No message"))

        if response.get("response_type") == "weekly_review_step_1":
            print("\n✅ Weekly review workflow initiated successfully!")
            print("🔍 ReviewAgent is guiding you through David Allen's 8-step process")

            # Simulate quick review completion for demo
            self._simulate_quick_review()

    def _demo_complete_ecosystem(self):
        """Demo both workflows in sequence."""
        print("\n🎯 " + "=" * 60)
        print("    COMPLETE ECOSYSTEM DEMO")
        print("=" * 64)

        print("\n**Phase 1: Project Breakdown**")
        print("Creating a complex project to demonstrate workflow...")

        # Project breakdown
        complex_project = "Build a comprehensive task management app with AI features, team collaboration, and mobile sync"

        breakdown_response = self.project_workflow.start_project_breakdown(
            initial_request=complex_project, user_id=self.demo_user, source_agent="ecosystem_demo"
        )

        print(f"✅ Project breakdown initiated for: {complex_project}")

        # Simulate project completion
        mock_completion = {
            "response_type": "project_breakdown_complete",
            "tasks_created": 12,
            "next_actions": [
                {
                    "content": "Research competitor task management apps",
                    "context": "@computer",
                    "time_estimate": "30min",
                },
                {
                    "content": "Define core feature requirements",
                    "context": "@computer",
                    "time_estimate": "20min",
                },
                {
                    "content": "Sketch initial UI wireframes",
                    "context": "@computer",
                    "time_estimate": "45min",
                },
                {
                    "content": "Set up development environment",
                    "context": "@computer",
                    "time_estimate": "15min",
                },
            ],
        }

        self.project_workflow.handle_planning_completion(self.demo_user, mock_completion)
        print(f"✅ Created {mock_completion['tasks_created']} actionable tasks")

        print("\n**Phase 2: Weekly Review & System Maintenance**")
        print("Now running weekly review to maintain system health...")

        # Weekly review
        review_response = self.review_workflow.start_weekly_review(
            user_id=self.demo_user, review_type="quick", scheduled=True
        )

        print("✅ Weekly review initiated")

        # Simulate review completion
        print("✅ System reviewed - all inboxes processed, projects healthy")

        print("\n🎉 **Complete Ecosystem Demo Finished!**")
        print("\n**Summary:**")
        print("• Complex project broken down into 12 actionable tasks")
        print("• Natural Planning Model applied for clarity")
        print("• Weekly review maintained system integrity")
        print("• All three agents collaborated seamlessly")
        print("• BMAD patterns ensured structured workflows")

    def _show_agent_capabilities(self):
        """Show capabilities of all agents."""
        print("\n❓ " + "=" * 60)
        print("    AGENT CAPABILITIES")
        print("=" * 64)

        agents = ["gtd-task-agent", "gtd-planning-agent", "gtd-review-agent"]

        for agent_id in agents:
            agent = self.agent_registry.get_agent(agent_id)
            if agent:
                capabilities = agent.get_capabilities()
                print(f"\n🤖 **{capabilities['name']} ({capabilities['icon']})**")
                print(f"   {capabilities['description']}")
                print(f"   **Commands:** {', '.join(capabilities['commands'])}")
            else:
                print(f"\n❌ Agent {agent_id} not found")

        print("\n📊 **Framework Components:**")
        print(f"   • Agent Registry: {len(self.agent_registry.agents)} agents registered")
        print("   • Workflow Engine: 2 workflows available")
        print("   • Context Manager: Cross-agent state management")
        print("   • BMAD Patterns: Command routing, YAML config, structured workflows")

    def _simulate_quick_planning(self, project: str):
        """Simulate quick planning completion for demo."""
        print("\n🎭 **[Demo Simulation]** Completing Natural Planning Model...")
        print("   Step 1: Purpose & Principles ✅")
        print("   Step 2: Outcome Visioning ✅")
        print("   Step 3: Brainstorming ✅")
        print("   Step 4: Organization ✅")
        print("   Step 5: Next Actions ✅")

        # Mock completion
        mock_planning_result = {
            "response_type": "planning_complete",
            "next_actions": [
                {
                    "content": f"Research requirements for {project}",
                    "context": "@computer",
                    "time_estimate": "30min",
                },
                {
                    "content": "Create project roadmap",
                    "context": "@computer",
                    "time_estimate": "20min",
                },
                {
                    "content": "Set up initial development structure",
                    "context": "@computer",
                    "time_estimate": "15min",
                },
            ],
        }

        completion_response = self.project_workflow.handle_planning_completion(
            user_id=self.demo_user, planning_result=mock_planning_result
        )

        if completion_response.get("response_type") == "project_breakdown_complete":
            print(
                f"\n✅ **Project broken down into {len(mock_planning_result['next_actions'])} actionable tasks!**"
            )

    def _simulate_quick_review(self):
        """Simulate quick review completion for demo."""
        print("\n🎭 **[Demo Simulation]** Completing weekly review steps...")
        print("   Step 1: Collect loose papers ✅")
        print("   Step 2: Process inboxes to zero ✅")
        print("   Step 3: Review calendar ✅")
        print("   Step 4: Review active projects ✅")
        print("   Step 5: Review next actions ✅")
        print("   Step 6: Review waiting for ✅")
        print("   Step 7: Review someday/maybe ✅")
        print("   Step 8: Plan ahead ✅")

        # Simulate completion response
        print("\n✅ **Weekly review completed!**")
        print("   Duration: 25 minutes")
        print("   System health: Excellent")
        print("   Tasks processed: 15")
        print("   Next review: Friday at 4:00 PM")


# Mock services (reused from project breakdown demo)
class MockTodoistService:
    """Mock Todoist service for demo."""

    def create_task(self, content: str, **kwargs):
        return {"id": f"task_{hash(content) % 1000}", "content": content, "created": True}

    def get_projects(self):
        return [{"id": "project_1", "name": "Personal"}, {"id": "project_2", "name": "Work"}]

    def get_tasks(self, **kwargs):
        return [
            {"id": "task_1", "content": "Sample task 1", "project_id": "project_1"},
            {"id": "task_2", "content": "Sample task 2", "project_id": "project_2"},
        ]


class MockOpenAIService:
    """Mock OpenAI service for demo."""

    def generate_tasks(self, prompt: str):
        return ["Research task", "Planning task", "Implementation task"]


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
            "tasks_completed": 23,
            "tasks_created": 28,
            "completion_rate": 0.82,
            "most_productive_context": "@computer",
        }


if __name__ == "__main__":
    try:
        demo = CompleteGTDEcosystemDemo()
        demo.run_complete_demo()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user. Goodbye! 👋")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        print("Please check the logs for details.")
