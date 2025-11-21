"""
Project Breakdown Workflow - BMAD-inspired multi-agent collaboration.

Demonstrates how GTD agents work together to transform complex projects into
actionable tasks through David Allen's Natural Planning Model.

Workflow: Complex Task → Planning → Breakdown → Task Creation → Review
"""

import logging
from datetime import datetime
from typing import Any

from framework.agent_registry import AgentRegistry
from framework.context_manager import ContextManager
from framework.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)


class ProjectBreakdownWorkflow:
    """
    Multi-agent workflow for breaking down complex projects.

    Following BMAD patterns for:
    - Agent collaboration and handoffs
    - Context preservation across steps
    - Structured workflow progression
    - Error handling and recovery
    """

    def __init__(
        self,
        workflow_engine: WorkflowEngine,
        agent_registry: AgentRegistry,
        context_manager: ContextManager,
    ):
        """Initialize workflow with required components."""
        self.workflow_engine = workflow_engine
        self.agent_registry = agent_registry
        self.context_manager = context_manager

        # Workflow configuration
        self.workflow_id = "project_breakdown"
        self.steps = [
            "detect_complexity",
            "initiate_planning",
            "natural_planning_process",
            "extract_tasks",
            "create_individual_tasks",
            "schedule_review",
        ]

        logger.info("Initialized Project Breakdown Workflow")

    def start_project_breakdown(
        self, initial_request: str, user_id: str, source_agent: str = "user"
    ) -> dict[str, Any]:
        """
        Start project breakdown workflow.

        Args:
            initial_request: Complex project or task description
            user_id: User identifier
            source_agent: Agent that triggered the workflow

        Returns:
            Workflow initiation response
        """
        logger.info(f"Starting project breakdown for: {initial_request}")

        # Initialize workflow context
        workflow_context = {
            "initial_request": initial_request,
            "source_agent": source_agent,
            "complexity_detected": True,
            "planning_complete": False,
            "tasks_created": False,
            "review_scheduled": False,
            "created_at": datetime.now().isoformat(),
        }

        # Create a simple execution context for this workflow
        from types import SimpleNamespace

        execution = SimpleNamespace()
        execution.workflow_id = self.workflow_id
        execution.user_id = user_id
        execution.context = workflow_context
        execution.status = "active"

        # Begin with complexity detection
        return self._execute_complexity_detection(execution, initial_request)

    def _execute_complexity_detection(self, execution, initial_request: str) -> dict[str, Any]:
        """Step 1: Detect if request needs project breakdown."""
        logger.info("Executing complexity detection")

        # Simple heuristics for complexity detection
        complexity_indicators = [
            len(initial_request.split()) > 10,  # Long description
            any(
                word in initial_request.lower()
                for word in [
                    "website",
                    "project",
                    "launch",
                    "organize",
                    "implement",
                    "develop",
                    "create",
                    "design",
                    "plan",
                    "strategy",
                ]
            ),
            any(
                word in initial_request.lower()
                for word in ["complex", "multiple", "several", "various", "different"]
            ),
        ]

        is_complex = sum(complexity_indicators) >= 2

        if not is_complex:
            # Not complex enough - hand back to task agent
            return {
                "response_type": "simple_task_detected",
                "message": "This looks like a simple task. Let me help you create it directly.",
                "workflow_status": "redirected",
                "handoff_to": "gtd-task-agent",
                "context": {"simple_task": initial_request},
            }

        # Complex enough - proceed to planning
        execution.context["complexity_score"] = sum(complexity_indicators)
        execution.context["complexity_reasons"] = [
            reason
            for reason, detected in zip(
                [
                    "Long description (>10 words)",
                    "Contains project keywords",
                    "Contains complexity indicators",
                ],
                complexity_indicators,
            )
            if detected
        ]

        return self._initiate_planning_phase(execution, initial_request)

    def _initiate_planning_phase(self, execution, initial_request: str) -> dict[str, Any]:
        """Step 2: Hand off to GTD Planning Agent."""
        logger.info("Initiating planning phase")

        # Get planning agent
        planning_agent = self.agent_registry.get_agent("gtd-planning-agent")
        if not planning_agent:
            return {
                "response_type": "workflow_error",
                "message": "Planning agent not available. Creating simple task instead.",
                "fallback": True,
            }

        # Prepare handoff context
        handoff_context = self.context_manager.prepare_handoff_context(
            user_id=execution.user_id,
            source_agent="workflow_engine",
            target_agent="gtd-planning-agent",
            handoff_data={
                "workflow_id": execution.workflow_id,
                "project_request": initial_request,
                "complexity_detected": True,
                "step": "initiate_planning",
            },
        )

        # Execute planning agent breakdown command
        planning_message = {
            "text": f"*breakdown {initial_request}",
            "user": execution.user_id,
            "workflow_context": handoff_context,
        }

        planning_response = planning_agent.process_message(planning_message, handoff_context)

        # Update execution context
        execution.context.update(
            {
                "planning_initiated": True,
                "planning_agent_response": planning_response,
                "current_step": "natural_planning_process",
            }
        )

        # Add workflow metadata to response
        planning_response["workflow"] = {
            "id": execution.workflow_id,
            "step": "planning_initiated",
            "next_step": "Continue with planning agent until completion",
        }

        return planning_response

    def handle_planning_completion(
        self, user_id: str, planning_result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Handle completion of planning phase.

        Called when GTD Planning Agent completes the Natural Planning Model process.
        """
        logger.info("Handling planning completion")

        # For demo purposes, create a mock execution context
        # In a full implementation, this would retrieve from workflow engine
        from types import SimpleNamespace

        execution = SimpleNamespace()
        execution.workflow_id = self.workflow_id
        execution.user_id = user_id
        execution.context = {"planning_complete": True, "initial_request": "Demo project"}

        # Extract tasks from planning result
        next_actions = planning_result.get("next_actions", [])
        project_structure = planning_result.get("project_structure", {})

        if not next_actions:
            return {
                "response_type": "planning_incomplete",
                "message": "Planning completed but no next actions were identified. Please review the planning output.",
            }

        # Update execution context
        execution.context.update(
            {
                "planning_complete": True,
                "next_actions": next_actions,
                "project_structure": project_structure,
                "current_step": "create_individual_tasks",
            }
        )

        # Proceed to task creation
        return self._execute_task_creation(execution, next_actions)

    def _execute_task_creation(
        self, execution, next_actions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Step 3: Create individual tasks from planning output."""
        logger.info(f"Creating {len(next_actions)} tasks from planning")

        # Get task agent
        task_agent = self.agent_registry.get_agent("gtd-task-agent")
        if not task_agent:
            return {
                "response_type": "workflow_error",
                "message": "Task agent not available. Please create tasks manually.",
                "tasks_to_create": next_actions,
            }

        # Create tasks one by one
        created_tasks = []
        task_creation_responses = []

        for i, action in enumerate(next_actions, 1):
            # Format task for creation
            task_content = action.get("content", action.get("description", ""))
            context = action.get("context", "@next")
            estimate = action.get("time_estimate", "10min")
            project = action.get("project", execution.context.get("initial_request", "Project"))

            # Create task via task agent
            task_message = {
                "text": f"*capture {task_content}",
                "user": execution.user_id,
                "workflow_context": {
                    "context": context,
                    "estimate": estimate,
                    "project": project,
                    "workflow_id": execution.workflow_id,
                    "task_sequence": i,
                },
            }

            task_response = task_agent.process_message(task_message, execution.context)
            task_creation_responses.append(task_response)

            # Track created task
            if task_response.get("response_type") == "task_created":
                created_tasks.append(
                    {
                        "content": task_content,
                        "context": context,
                        "estimate": estimate,
                        "status": "created",
                    }
                )

        # Update execution context
        execution.context.update(
            {
                "tasks_created": True,
                "created_tasks": created_tasks,
                "task_creation_responses": task_creation_responses,
                "current_step": "schedule_review",
            }
        )

        # Prepare completion response
        tasks_summary = "\n".join(
            [
                f"• **{task['content']}** ({task['estimate']}, {task['context']})"
                for task in created_tasks
            ]
        )

        completion_response = {
            "response_type": "project_breakdown_complete",
            "workflow_id": execution.workflow_id,
            "project": execution.context.get("initial_request"),
            "tasks_created": len(created_tasks),
            "created_tasks": created_tasks,
            "message": f"🎉 **Project Breakdown Complete!**\n\n**Project:** {execution.context.get('initial_request')}\n\n**Created {len(created_tasks)} tasks:**\n\n{tasks_summary}\n\nYour project has been broken down using GTD Natural Planning Model and all tasks are now in your system!\n\nWould you like me to:\n1. 📊 **Schedule a project review** with ReviewCoach\n2. 🎯 **Show project structure** details\n3. ✅ **Mark workflow complete**",
            "actions": [
                {"label": "📊 Schedule Review", "value": "schedule_project_review"},
                {"label": "🎯 Show Structure", "value": "show_project_structure"},
                {"label": "✅ Complete", "value": "complete_workflow"},
            ],
            "workflow": {
                "id": execution.workflow_id,
                "step": "tasks_created",
                "completion_rate": 0.9,
            },
        }

        return completion_response

    def handle_workflow_action(self, user_id: str, action: str) -> dict[str, Any]:
        """Handle post-completion workflow actions."""
        # For demo purposes, create mock execution
        from types import SimpleNamespace

        execution = SimpleNamespace()
        execution.workflow_id = self.workflow_id
        execution.user_id = user_id
        execution.context = {
            "initial_request": "Demo project",
            "created_tasks": [],
            "project_structure": {},
        }

        if action == "schedule_project_review":
            return self._schedule_project_review(execution)
        elif action == "show_project_structure":
            return self._show_project_structure(execution)
        elif action == "complete_workflow":
            return self._complete_workflow(execution)
        else:
            return {"response_type": "error", "message": f"Unknown action: {action}"}

    def _schedule_project_review(self, execution) -> dict[str, Any]:
        """Schedule project review with GTD Review Agent."""
        logger.info("Scheduling project review")

        # Get review agent
        review_agent = self.agent_registry.get_agent("gtd-review-agent")
        if not review_agent:
            return {
                "response_type": "review_unavailable",
                "message": "Review agent not available. Consider manually scheduling a project check-in.",
            }

        # Schedule review
        review_message = {
            "text": f"*project-health {execution.context.get('initial_request')}",
            "user": execution.user_id,
            "workflow_context": {
                "project_breakdown_workflow": execution.workflow_id,
                "created_tasks": execution.context.get("created_tasks", []),
            },
        }

        review_response = review_agent.process_message(review_message, execution.context)

        # Update execution
        execution.context.update({"review_scheduled": True, "review_response": review_response})

        return {
            "response_type": "review_scheduled",
            "message": "📊 **Project review scheduled!** ReviewCoach will help you monitor the health and progress of your new project.",
            "review_details": review_response,
            "workflow_status": "review_scheduled",
        }

    def _show_project_structure(self, execution) -> dict[str, Any]:
        """Show complete project structure."""
        project_structure = execution.context.get("project_structure", {})
        created_tasks = execution.context.get("created_tasks", [])

        # Format structure display
        structure_display = "**Project Breakdown Structure:**\n\n"

        for category, items in project_structure.items():
            structure_display += f"**{category}:**\n"
            for item in items:
                # Check if this item became a task
                task_status = "💭 Planned"
                for task in created_tasks:
                    if item.lower() in task["content"].lower():
                        task_status = f"✅ Created ({task['context']}, {task['estimate']})"
                        break

                structure_display += f"  • {item} - {task_status}\n"
            structure_display += "\n"

        return {
            "response_type": "project_structure_display",
            "project": execution.context.get("initial_request"),
            "message": structure_display,
            "workflow_status": "structure_shown",
        }

    def _complete_workflow(self, execution) -> dict[str, Any]:
        """Complete and cleanup workflow."""
        logger.info(f"Completing workflow {execution.workflow_id}")

        # Calculate final stats
        created_tasks = execution.context.get("created_tasks", [])
        complexity_score = execution.context.get("complexity_score", 0)

        # Mark workflow as complete
        execution.status = "completed"
        execution.completed_at = datetime.now().isoformat()

        return {
            "response_type": "workflow_complete",
            "workflow_id": execution.workflow_id,
            "project": execution.context.get("initial_request"),
            "summary": {
                "tasks_created": len(created_tasks),
                "complexity_score": complexity_score,
                "planning_method": "Natural Planning Model",
                "review_scheduled": execution.context.get("review_scheduled", False),
            },
            "message": f"🎯 **Project Breakdown Workflow Complete!**\n\nYour complex project has been successfully transformed into {len(created_tasks)} actionable GTD tasks using David Allen's Natural Planning Model.\n\n**Next Steps:**\n• Execute your next actions in order\n• Use weekly reviews to maintain momentum\n• Break down tasks further if needed\n\nHappy productivity! 🚀",
            "workflow_status": "completed",
        }


# Workflow registration helper
def register_project_breakdown_workflow(
    workflow_engine: WorkflowEngine, agent_registry: AgentRegistry, context_manager: ContextManager
):
    """Register the project breakdown workflow with the engine."""
    workflow_instance = ProjectBreakdownWorkflow(workflow_engine, agent_registry, context_manager)

    # For now, store workflow instance directly in a simple registry
    # In a full implementation, this would create a proper Workflow object
    if not hasattr(workflow_engine, "workflow_instances"):
        workflow_engine.workflow_instances = {}

    workflow_engine.workflow_instances["project_breakdown"] = workflow_instance

    logger.info("Project Breakdown Workflow registered")
    return workflow_instance
