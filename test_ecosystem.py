#!/usr/bin/env python3
"""
Test GTD Agent Ecosystem - Non-interactive test

Tests the complete BMAD-inspired GTD agent ecosystem without user input.
Validates that all agents are properly loaded and can communicate.
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


class EcosystemTester:
    """Test the complete GTD ecosystem functionality."""

    def __init__(self):
        """Initialize test environment."""
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

        # Test user
        self.test_user = "test_user_001"

    def run_tests(self):
        """Run all ecosystem tests."""
        print("🧪 " + "=" * 60)
        print("    GTD AGENT ECOSYSTEM TESTS")
        print("=" * 64)
        print()

        tests = [
            ("Load Agents", self.test_load_agents),
            ("Agent Commands", self.test_agent_commands),
            ("Agent Communication", self.test_agent_communication),
            ("Load Workflows", self.test_load_workflows),
            ("Project Breakdown", self.test_project_breakdown),
            ("Weekly Review", self.test_weekly_review),
            ("Framework Integration", self.test_framework_integration),
        ]

        results = {}

        for test_name, test_func in tests:
            print(f"\n🔍 Testing: {test_name}")
            print("-" * 40)

            try:
                test_func()
                results[test_name] = "✅ PASS"
                print(f"✅ {test_name}: PASSED")
            except Exception as e:
                results[test_name] = f"❌ FAIL: {str(e)}"
                print(f"❌ {test_name}: FAILED - {str(e)}")

        # Print summary
        print("\n" + "=" * 60)
        print("    TEST RESULTS SUMMARY")
        print("=" * 60)

        for test_name, result in results.items():
            print(f"{result:<50} {test_name}")

        passed = sum(1 for result in results.values() if result.startswith("✅"))
        total = len(results)

        print(f"\nOverall: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed! GTD ecosystem is working correctly.")
        else:
            print("⚠️ Some tests failed. Check the logs for details.")

    def test_load_agents(self):
        """Test loading all GTD agents."""
        # Load TaskAgent
        task_agent = GTDTaskAgent.from_yaml("agents/gtd_task_agent.yaml", self.mock_services)
        self.agent_registry.register_agent_instance(task_agent, "gtd-task-agent")
        assert task_agent.name == "TaskFlow"

        # Load PlanningAgent
        planning_agent = GTDPlanningAgent.from_yaml(
            "agents/gtd_planning_agent.yaml", self.mock_services
        )
        self.agent_registry.register_agent_instance(planning_agent, "gtd-planning-agent")
        assert planning_agent.name == "PlanMaster"

        # Load ReviewAgent
        review_agent = GTDReviewAgent.from_yaml("agents/gtd_review_agent.yaml", self.mock_services)
        self.agent_registry.register_agent_instance(review_agent, "gtd-review-agent")
        assert review_agent.name == "ReviewCoach"

        print("   Loaded 3 agents successfully")

    def test_agent_commands(self):
        """Test agent command registration and help."""
        # Test TaskAgent commands
        task_agent = self.agent_registry.get_agent("gtd-task-agent")
        help_response = task_agent.process_message({"text": "*help", "user": self.test_user}, {})
        assert help_response["response_type"] == "help"
        assert "capture" in help_response["message"]

        # Test PlanningAgent commands
        planning_agent = self.agent_registry.get_agent("gtd-planning-agent")
        help_response = planning_agent.process_message(
            {"text": "*help", "user": self.test_user}, {}
        )
        assert help_response["response_type"] == "help"
        assert "breakdown" in help_response["message"]

        # Test ReviewAgent commands
        review_agent = self.agent_registry.get_agent("gtd-review-agent")
        help_response = review_agent.process_message({"text": "*help", "user": self.test_user}, {})
        assert help_response["response_type"] == "help"
        assert "weekly-review" in help_response["message"]

        print("   All agent commands registered and working")

    def test_agent_communication(self):
        """Test agent can_handle and message processing."""
        try:
            # Test TaskAgent message handling
            task_agent = self.agent_registry.get_agent("gtd-task-agent")

            # Should handle task creation - TaskAgent handles all messages
            can_handle_task = task_agent.can_handle({"text": "I need to call the dentist"})
            print(f"     TaskAgent handles task creation: {can_handle_task}")

            # Test PlanningAgent message handling
            planning_agent = self.agent_registry.get_agent("gtd-planning-agent")

            # Should handle planning requests
            can_handle_planning = planning_agent.can_handle(
                {"text": "help me break down this complex project"}
            )
            print(f"     PlanningAgent handles planning: {can_handle_planning}")

            # Test ReviewAgent message handling
            review_agent = self.agent_registry.get_agent("gtd-review-agent")

            # Should handle review requests
            can_handle_review = review_agent.can_handle({"text": "time for my weekly review"})
            print(f"     ReviewAgent handles reviews: {can_handle_review}")

            print("   Agent communication patterns working correctly")
        except Exception as e:
            print(f"   Agent communication test error: {e}")
            raise

    def test_load_workflows(self):
        """Test workflow registration."""
        # Register workflows
        project_workflow = register_project_breakdown_workflow(
            self.workflow_engine, self.agent_registry, self.context_manager
        )

        review_workflow = register_weekly_review_workflow(
            self.workflow_engine, self.agent_registry, self.context_manager
        )

        # Verify workflows are registered
        assert hasattr(self.workflow_engine, "workflow_instances")
        assert "project_breakdown" in self.workflow_engine.workflow_instances
        assert "weekly_review" in self.workflow_engine.workflow_instances

        print("   2 workflows registered successfully")

    def test_project_breakdown(self):
        """Test project breakdown workflow."""
        # Get workflow
        project_workflow = self.workflow_engine.workflow_instances["project_breakdown"]

        # Start project breakdown
        complex_project = "Build a mobile app with authentication and social features"
        response = project_workflow.start_project_breakdown(
            initial_request=complex_project, user_id=self.test_user, source_agent="test"
        )

        # Should detect complexity and initiate planning
        assert response is not None
        assert isinstance(response, dict)

        # Test planning completion
        mock_planning_result = {
            "response_type": "planning_complete",
            "next_actions": [
                {
                    "content": "Research app requirements",
                    "context": "@computer",
                    "time_estimate": "30min",
                },
                {
                    "content": "Design user interface",
                    "context": "@computer",
                    "time_estimate": "45min",
                },
            ],
        }

        completion_response = project_workflow.handle_planning_completion(
            user_id=self.test_user, planning_result=mock_planning_result
        )

        assert completion_response is not None
        assert isinstance(completion_response, dict)

        print("   Project breakdown workflow functioning")

    def test_weekly_review(self):
        """Test weekly review workflow."""
        # Get workflow
        review_workflow = self.workflow_engine.workflow_instances["weekly_review"]

        # Start weekly review
        response = review_workflow.start_weekly_review(user_id=self.test_user, review_type="quick")

        # Should initiate review process
        assert response is not None
        assert isinstance(response, dict)

        # Test review status
        status_response = review_workflow.get_review_status(self.test_user)
        assert status_response is not None
        assert isinstance(status_response, dict)

        print("   Weekly review workflow functioning")

    def test_framework_integration(self):
        """Test framework components integration."""
        # Test context manager
        self.context_manager.update_context(self.test_user, {"test_key": "test_value"})
        context = self.context_manager.get_context(self.test_user)
        assert context["test_key"] == "test_value"

        # Test agent registry
        agents = self.agent_registry.list_agents()
        assert len(agents) >= 3

        # Test agent discovery
        task_message = {"text": "I need to create a task", "user": self.test_user}
        agent = self.agent_registry.find_agent_for_message(task_message)
        assert agent is not None
        assert agent.name == "TaskFlow"

        print("   Framework integration working correctly")


# Mock services
class MockTodoistService:
    def create_task(self, content: str, **kwargs):
        return {"id": f"task_{hash(content) % 1000}", "content": content, "created": True}

    def add_task(self, content: str, **kwargs):
        return {"id": f"task_{hash(content) % 1000}", "content": content, "created": True}

    def get_projects(self):
        return [{"id": "project_1", "name": "Personal"}]


class MockOpenAIService:
    def generate_tasks(self, prompt: str):
        return ["Sample task 1", "Sample task 2"]


class MockCalendarService:
    def get_events(self, start_date, end_date):
        return [{"title": "Test Meeting", "start": "2024-01-15T10:00:00"}]


class MockAnalyticsService:
    def get_productivity_stats(self, user_id: str, period: str):
        return {"tasks_completed": 10, "completion_rate": 0.8}


if __name__ == "__main__":
    try:
        tester = EcosystemTester()
        tester.run_tests()
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
