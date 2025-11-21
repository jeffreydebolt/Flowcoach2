"""
Weekly Review Workflow - BMAD-inspired GTD system maintenance.

Implements David Allen's Weekly Review process as a structured workflow
that maintains GTD system integrity and provides productivity insights.

Flow: ReviewAgent → TaskAgent (cleanup) → PlanningAgent (project health) → ReviewAgent (completion)
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from framework.agent_registry import AgentRegistry
from framework.context_manager import ContextManager
from framework.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)


class WeeklyReviewWorkflow:
    """
    Multi-agent workflow for GTD Weekly Review process.

    Following BMAD patterns for:
    - Systematic review progression
    - Agent collaboration for cleanup and health checks
    - Context preservation across review steps
    - Analytics and insights generation
    """

    def __init__(
        self,
        workflow_engine: WorkflowEngine,
        agent_registry: AgentRegistry,
        context_manager: ContextManager,
    ):
        """Initialize weekly review workflow."""
        self.workflow_engine = workflow_engine
        self.agent_registry = agent_registry
        self.context_manager = context_manager

        # Workflow configuration
        self.workflow_id = "weekly_review"
        self.review_steps = [
            "initiate_review",
            "collect_loose_items",
            "process_inboxes",
            "review_calendar",
            "review_projects",
            "review_next_actions",
            "review_waiting_for",
            "review_someday_maybe",
            "generate_insights",
            "plan_ahead",
            "complete_review",
        ]

        logger.info("Initialized Weekly Review Workflow")

    def start_weekly_review(
        self, user_id: str, review_type: str = "full", scheduled: bool = False
    ) -> dict[str, Any]:
        """
        Start weekly review workflow.

        Args:
            user_id: User identifier
            review_type: Type of review (full, quick, custom)
            scheduled: Whether this is a scheduled review

        Returns:
            Review initiation response
        """
        logger.info(f"Starting weekly review for user: {user_id}, type: {review_type}")

        # Initialize workflow context
        workflow_context = {
            "review_type": review_type,
            "scheduled": scheduled,
            "started_at": datetime.now().isoformat(),
            "steps_completed": [],
            "current_step": "initiate_review",
            "insights_data": {},
            "cleanup_tasks": [],
            "project_health_issues": [],
            "next_week_focus": [],
        }

        # Create simple execution context for demo
        from types import SimpleNamespace

        execution = SimpleNamespace()
        execution.workflow_id = self.workflow_id
        execution.user_id = user_id
        execution.context = workflow_context
        execution.status = "active"

        # Begin with review initiation
        return self._initiate_review(execution, review_type)

    def _initiate_review(self, execution, review_type: str) -> dict[str, Any]:
        """Step 1: Initiate review with ReviewAgent."""
        logger.info("Initiating weekly review")

        # Get review agent
        review_agent = self.agent_registry.get_agent("gtd-review-agent")
        if not review_agent:
            return {
                "response_type": "workflow_error",
                "message": "Review agent not available. Please try again later.",
            }

        # Start review with agent
        review_message = {
            "text": f"*weekly-review {review_type}",
            "user": execution.user_id,
            "workflow_context": {"workflow_id": execution.workflow_id, "automated_workflow": True},
        }

        review_response = review_agent.process_message(review_message, execution.context)

        # Update execution context
        execution.context.update(
            {
                "review_initiated": True,
                "review_agent_active": True,
                "current_step": "collect_loose_items",
            }
        )

        # Add workflow metadata
        review_response["workflow"] = {
            "id": execution.workflow_id,
            "type": "weekly_review",
            "step": "initiated",
            "automation_level": "guided",
        }

        return review_response

    def continue_review_step(self, user_id: str, user_response: str) -> dict[str, Any]:
        """
        Continue to next review step based on user response.

        Called when user completes a review step and provides input.
        """
        # For demo purposes, create mock execution
        from types import SimpleNamespace

        execution = SimpleNamespace()
        execution.workflow_id = self.workflow_id
        execution.user_id = user_id
        execution.context = {"current_step": "collect_loose_items", "steps_completed": []}

        current_step = execution.context.get("current_step")
        logger.info(f"Continuing review step: {current_step}")

        # Route to appropriate step handler
        step_handlers = {
            "collect_loose_items": self._handle_collect_completion,
            "process_inboxes": self._handle_inbox_processing,
            "review_calendar": self._handle_calendar_review,
            "review_projects": self._handle_project_review,
            "review_next_actions": self._handle_next_actions_review,
            "review_waiting_for": self._handle_waiting_for_review,
            "review_someday_maybe": self._handle_someday_maybe_review,
            "plan_ahead": self._handle_planning_completion,
        }

        handler = step_handlers.get(current_step)
        if handler:
            return handler(execution, user_response)
        else:
            # Default: continue with review agent
            return self._continue_with_review_agent(execution, user_response)

    def _handle_inbox_processing(self, execution, user_response: str) -> dict[str, Any]:
        """Handle inbox processing step with TaskAgent assistance."""
        if "help" in user_response.lower() or "stuck" in user_response.lower():
            # User needs help - engage TaskAgent for inbox processing
            return self._engage_task_agent_for_cleanup(execution, "inbox_processing")

        # Mark step complete and continue
        execution.context["steps_completed"].append("process_inboxes")
        execution.context["current_step"] = "review_calendar"

        return self._continue_with_review_agent(execution, user_response)

    def _handle_project_review(self, execution, user_response: str) -> dict[str, Any]:
        """Handle project review step with PlanningAgent assistance."""
        if any(word in user_response.lower() for word in ["stuck", "stalled", "help", "unclear"]):
            # Projects need attention - engage PlanningAgent
            return self._engage_planning_agent_for_health_check(execution, user_response)

        # Mark step complete
        execution.context["steps_completed"].append("review_projects")
        execution.context["current_step"] = "review_next_actions"

        return self._continue_with_review_agent(execution, user_response)

    def _engage_task_agent_for_cleanup(self, execution, cleanup_type: str) -> dict[str, Any]:
        """Engage TaskAgent for cleanup assistance."""
        logger.info(f"Engaging TaskAgent for {cleanup_type}")

        task_agent = self.agent_registry.get_agent("gtd-task-agent")
        if not task_agent:
            return {
                "response_type": "agent_unavailable",
                "message": "TaskAgent not available for cleanup assistance. Please continue manually.",
            }

        # Determine cleanup command based on type
        cleanup_commands = {
            "inbox_processing": "*format-gtd inbox items",
            "stale_cleanup": "*cleanup stale tasks",
            "context_organization": "*organize by context",
        }

        cleanup_message = {
            "text": cleanup_commands.get(cleanup_type, "*help"),
            "user": execution.user_id,
            "workflow_context": {
                "workflow_id": execution.workflow_id,
                "review_step": cleanup_type,
                "return_to_review": True,
            },
        }

        cleanup_response = task_agent.process_message(cleanup_message, execution.context)

        # Update execution context
        execution.context["cleanup_tasks"].append(
            {"type": cleanup_type, "status": "in_progress", "response": cleanup_response}
        )

        cleanup_response["workflow"] = {
            "id": execution.workflow_id,
            "step": "cleanup_assistance",
            "return_action": "continue_review",
        }

        return cleanup_response

    def _engage_planning_agent_for_health_check(
        self, execution, project_concerns: str
    ) -> dict[str, Any]:
        """Engage PlanningAgent for project health check."""
        logger.info("Engaging PlanningAgent for project health check")

        planning_agent = self.agent_registry.get_agent("gtd-planning-agent")
        if not planning_agent:
            return {
                "response_type": "agent_unavailable",
                "message": "PlanningAgent not available. Please review projects manually.",
            }

        health_check_message = {
            "text": f"*project-health analysis needed: {project_concerns}",
            "user": execution.user_id,
            "workflow_context": {
                "workflow_id": execution.workflow_id,
                "review_context": True,
                "concerns": project_concerns,
            },
        }

        health_response = planning_agent.process_message(health_check_message, execution.context)

        # Update execution context
        execution.context["project_health_issues"].append(
            {
                "concerns": project_concerns,
                "analysis": health_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        health_response["workflow"] = {
            "id": execution.workflow_id,
            "step": "project_health_check",
            "return_action": "continue_review",
        }

        return health_response

    def _continue_with_review_agent(self, execution, user_response: str) -> dict[str, Any]:
        """Continue with ReviewAgent for next step."""
        review_agent = self.agent_registry.get_agent("gtd-review-agent")
        if not review_agent:
            return {"response_type": "error", "message": "Review agent not available"}

        continue_message = {
            "text": user_response,
            "user": execution.user_id,
            "workflow_context": execution.context,
        }

        return review_agent.process_message(continue_message, execution.context)

    def _handle_collect_completion(self, execution, user_response: str) -> dict[str, Any]:
        """Handle completion of loose items collection."""
        execution.context["steps_completed"].append("collect_loose_items")
        execution.context["current_step"] = "process_inboxes"
        return self._continue_with_review_agent(execution, user_response)

    def _handle_calendar_review(self, execution, user_response: str) -> dict[str, Any]:
        """Handle calendar review completion."""
        execution.context["steps_completed"].append("review_calendar")
        execution.context["current_step"] = "review_projects"
        return self._continue_with_review_agent(execution, user_response)

    def _handle_next_actions_review(self, execution, user_response: str) -> dict[str, Any]:
        """Handle next actions review completion."""
        execution.context["steps_completed"].append("review_next_actions")
        execution.context["current_step"] = "review_waiting_for"
        return self._continue_with_review_agent(execution, user_response)

    def _handle_waiting_for_review(self, execution, user_response: str) -> dict[str, Any]:
        """Handle waiting for review completion."""
        execution.context["steps_completed"].append("review_waiting_for")
        execution.context["current_step"] = "review_someday_maybe"
        return self._continue_with_review_agent(execution, user_response)

    def _handle_someday_maybe_review(self, execution, user_response: str) -> dict[str, Any]:
        """Handle someday/maybe review completion."""
        execution.context["steps_completed"].append("review_someday_maybe")
        execution.context["current_step"] = "plan_ahead"
        return self._continue_with_review_agent(execution, user_response)

    def _handle_planning_completion(self, execution, user_response: str) -> dict[str, Any]:
        """Handle planning ahead completion."""
        execution.context["steps_completed"].append("plan_ahead")
        execution.context["current_step"] = "complete_review"

        # Generate comprehensive insights before completion
        return self._generate_review_insights(execution)

    def _generate_review_insights(self, execution) -> dict[str, Any]:
        """Generate comprehensive review insights."""
        logger.info("Generating weekly review insights")

        review_agent = self.agent_registry.get_agent("gtd-review-agent")
        if not review_agent:
            return self._complete_review_workflow(execution)

        # Generate insights based on review data
        insights_message = {
            "text": "*insights weekly",
            "user": execution.user_id,
            "workflow_context": {"review_data": execution.context, "generate_summary": True},
        }

        insights_response = review_agent.process_message(insights_message, execution.context)

        # Store insights
        execution.context["insights_data"] = insights_response

        # Complete the review
        return self._complete_review_workflow(execution, insights_response)

    def _complete_review_workflow(
        self, execution, insights_response: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Complete the weekly review workflow."""
        logger.info(f"Completing weekly review workflow {execution.workflow_id}")

        # Calculate review statistics
        completed_at = datetime.now()
        started_at = datetime.fromisoformat(
            execution.context.get("started_at", completed_at.isoformat())
        )
        duration = (completed_at - started_at).total_seconds() / 60  # minutes

        steps_completed = len(execution.context.get("steps_completed", []))
        total_steps = len(self.review_steps) - 2  # Exclude initiate and complete
        completion_rate = (steps_completed / total_steps) * 100

        # Compile review summary
        review_summary = {
            "duration_minutes": round(duration, 1),
            "steps_completed": steps_completed,
            "completion_rate": completion_rate,
            "cleanup_tasks": len(execution.context.get("cleanup_tasks", [])),
            "project_health_checks": len(execution.context.get("project_health_issues", [])),
            "review_type": execution.context.get("review_type", "full"),
        }

        # Mark workflow as complete
        execution.status = "completed"
        execution.completed_at = completed_at.isoformat()
        execution.context["review_summary"] = review_summary

        # Schedule next review reminder
        next_review_date = completed_at + timedelta(days=7)

        # Format completion message
        insights_text = ""
        if insights_response:
            insights_text = f"\n\n**Key Insights:**\n{insights_response.get('message', 'Review completed successfully.')}"

        completion_message = f"""🎉 **Weekly Review Complete!**

**Duration:** {review_summary['duration_minutes']} minutes
**Steps Completed:** {steps_completed}/{total_steps} ({completion_rate:.0f}%)
**Cleanup Tasks:** {review_summary['cleanup_tasks']} assisted
**Project Health Checks:** {review_summary['project_health_checks']} performed

Your GTD system is now refreshed and ready for the week ahead!{insights_text}

**Next Review:** {next_review_date.strftime('%A, %B %d at 4:00 PM')}

🚀 **You're ready to tackle the week with a clear, trusted system!**"""

        return {
            "response_type": "weekly_review_complete",
            "workflow_id": execution.workflow_id,
            "review_summary": review_summary,
            "insights": insights_response,
            "next_review_date": next_review_date.isoformat(),
            "message": completion_message,
            "celebration": True,
            "workflow_status": "completed",
        }

    def get_review_status(self, user_id: str) -> dict[str, Any]:
        """Get current review status for user."""
        # For demo purposes, return mock status
        from types import SimpleNamespace

        execution = SimpleNamespace()
        execution.workflow_id = self.workflow_id
        execution.context = {
            "current_step": "review_projects",
            "steps_completed": ["collect_loose_items", "process_inboxes", "review_calendar"],
            "started_at": datetime.now().isoformat(),
            "review_type": "full",
        }

        current_step = execution.context.get("current_step", "unknown")
        steps_completed = len(execution.context.get("steps_completed", []))
        total_steps = len(self.review_steps) - 2

        return {
            "response_type": "review_status",
            "workflow_id": execution.workflow_id,
            "current_step": current_step,
            "progress": f"{steps_completed}/{total_steps}",
            "completion_rate": (steps_completed / total_steps) * 100,
            "started_at": execution.context.get("started_at"),
            "review_type": execution.context.get("review_type", "full"),
            "message": f"**Review Progress:** {steps_completed}/{total_steps} steps completed\n**Current Step:** {current_step.replace('_', ' ').title()}\n\nReady to continue your weekly review?",
        }


# Workflow registration helper
def register_weekly_review_workflow(
    workflow_engine: WorkflowEngine, agent_registry: AgentRegistry, context_manager: ContextManager
):
    """Register the weekly review workflow with the engine."""
    workflow_instance = WeeklyReviewWorkflow(workflow_engine, agent_registry, context_manager)

    # For now, store workflow instance directly in a simple registry
    # In a full implementation, this would create a proper Workflow object
    if not hasattr(workflow_engine, "workflow_instances"):
        workflow_engine.workflow_instances = {}

    workflow_engine.workflow_instances["weekly_review"] = workflow_instance

    logger.info("Weekly Review Workflow registered")
    return workflow_instance
