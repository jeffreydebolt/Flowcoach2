"""
Workflow Engine for orchestrating multi-agent workflows.

Inspired by BMAD's workflow patterns, this enables:
- Multi-step agent workflows
- Agent handoffs and collaboration
- Context preservation across workflow steps
- Conditional workflow logic
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import yaml
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class WorkflowStep:
    """Individual step in a workflow."""
    
    def __init__(self, step_config: Dict[str, Any]):
        self.id = step_config.get("id")
        self.name = step_config.get("name", self.id)
        self.agent_id = step_config.get("agent")
        self.action = step_config.get("action")
        self.condition = step_config.get("condition")
        self.next_steps = step_config.get("next", [])
        self.on_success = step_config.get("on_success")
        self.on_failure = step_config.get("on_failure")
        self.timeout = step_config.get("timeout", 300)  # 5 minute default
        self.retries = step_config.get("retries", 0)
        
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """Check if this step should execute based on conditions."""
        if not self.condition:
            return True
        
        # Simple condition evaluation (can be expanded)
        try:
            return eval(self.condition, {"context": context})
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{self.condition}': {e}")
            return True


class Workflow:
    """Represents a complete workflow definition."""
    
    def __init__(self, workflow_config: Dict[str, Any]):
        self.id = workflow_config.get("id")
        self.name = workflow_config.get("name", self.id)
        self.description = workflow_config.get("description", "")
        self.version = workflow_config.get("version", "1.0")
        self.entry_point = workflow_config.get("entry_point")
        self.timeout = workflow_config.get("timeout", 3600)  # 1 hour default
        
        # Parse steps
        self.steps = {}
        for step_config in workflow_config.get("steps", []):
            step = WorkflowStep(step_config)
            self.steps[step.id] = step
        
        # Workflow metadata
        self.created_at = datetime.now()
        self.updated_at = self.created_at
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'Workflow':
        """Load workflow from YAML file."""
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        return cls(config)


class WorkflowExecution:
    """Represents an active workflow execution."""
    
    def __init__(self, workflow: Workflow, initial_context: Dict[str, Any] = None):
        self.workflow = workflow
        self.execution_id = f"{workflow.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.status = WorkflowStatus.PENDING
        self.context = initial_context or {}
        
        # Execution tracking
        self.current_step = None
        self.completed_steps = []
        self.failed_steps = []
        self.step_results = {}
        
        # Timing
        self.started_at = None
        self.completed_at = None
        self.duration = None
        
        logger.info(f"Created workflow execution: {self.execution_id}")
    
    def add_result(self, step_id: str, result: Dict[str, Any]):
        """Add result from a completed step."""
        self.step_results[step_id] = result
        self.context.update(result.get("context_updates", {}))
    
    def get_step_result(self, step_id: str) -> Optional[Dict[str, Any]]:
        """Get result from a previous step."""
        return self.step_results.get(step_id)


class WorkflowEngine:
    """
    Engine for executing multi-agent workflows.
    
    Features:
    - Workflow definition and execution
    - Agent orchestration and handoffs
    - Context preservation across steps
    - Error handling and recovery
    - Conditional logic and branching
    """
    
    def __init__(self, agent_registry, context_manager):
        """
        Initialize workflow engine.
        
        Args:
            agent_registry: Agent registry for agent lookups
            context_manager: Context manager for state preservation
        """
        self.agent_registry = agent_registry
        self.context_manager = context_manager
        self.workflows: Dict[str, Workflow] = {}
        self.active_executions: Dict[str, WorkflowExecution] = {}
        
        logger.info("WorkflowEngine initialized")
    
    def register_workflow(self, workflow: Workflow):
        """
        Register a workflow definition.
        
        Args:
            workflow: Workflow to register
        """
        self.workflows[workflow.id] = workflow
        logger.info(f"Registered workflow: {workflow.id}")
    
    def load_workflow_from_yaml(self, yaml_path: str):
        """
        Load and register workflow from YAML file.
        
        Args:
            yaml_path: Path to workflow YAML file
        """
        workflow = Workflow.from_yaml(yaml_path)
        self.register_workflow(workflow)
    
    def start_workflow(self, workflow_id: str, user_id: str, 
                      initial_context: Dict[str, Any] = None) -> WorkflowExecution:
        """
        Start a workflow execution.
        
        Args:
            workflow_id: ID of workflow to execute
            user_id: User initiating the workflow
            initial_context: Initial context data
            
        Returns:
            WorkflowExecution instance
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        
        # Prepare context
        context = initial_context or {}
        context.update({
            "workflow_id": workflow_id,
            "user_id": user_id,
            "execution_id": None,  # Will be set after execution creation
            "started_at": datetime.now().isoformat()
        })
        
        # Create execution
        execution = WorkflowExecution(workflow, context)
        execution.context["execution_id"] = execution.execution_id
        
        # Register execution
        self.active_executions[execution.execution_id] = execution
        
        # Update user context
        self.context_manager.update_workflow_context(
            user_id, 
            execution.execution_id,
            {
                "workflow_id": workflow_id,
                "status": "started",
                "execution_id": execution.execution_id
            }
        )
        
        logger.info(f"Started workflow {workflow_id} for user {user_id}: {execution.execution_id}")
        
        # Begin execution
        self._execute_workflow(execution)
        
        return execution
    
    def _execute_workflow(self, execution: WorkflowExecution):
        """Execute a workflow."""
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.now()
        
        try:
            # Start with entry point
            entry_step_id = execution.workflow.entry_point
            if not entry_step_id or entry_step_id not in execution.workflow.steps:
                raise ValueError(f"Invalid entry point: {entry_step_id}")
            
            self._execute_step(execution, entry_step_id)
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.now()
    
    def _execute_step(self, execution: WorkflowExecution, step_id: str):
        """Execute a specific workflow step."""
        if step_id not in execution.workflow.steps:
            logger.error(f"Unknown step: {step_id}")
            return
        
        step = execution.workflow.steps[step_id]
        execution.current_step = step_id
        
        logger.info(f"Executing step {step_id} in workflow {execution.execution_id}")
        
        # Check step conditions
        if not step.should_execute(execution.context):
            logger.info(f"Skipping step {step_id} due to condition")
            self._proceed_to_next_step(execution, step)
            return
        
        # Get target agent
        agent = self.agent_registry.get_agent(step.agent_id)
        if not agent:
            logger.error(f"Agent not found: {step.agent_id}")
            execution.failed_steps.append(step_id)
            return
        
        try:
            # Execute step action
            result = self._execute_step_action(agent, step, execution.context)
            
            # Process result
            if result.get("response_type") == "agent_handoff":
                # Handle agent handoff
                self._handle_agent_handoff(execution, step, result)
            elif result.get("response_type") == "workflow_complete":
                # Workflow completion
                self._complete_workflow(execution, result)
            else:
                # Normal step completion
                self._complete_step(execution, step, result)
                
        except Exception as e:
            logger.error(f"Step {step_id} failed: {e}")
            execution.failed_steps.append(step_id)
            self._handle_step_failure(execution, step, str(e))
    
    def _execute_step_action(self, agent, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the action for a workflow step."""
        if step.action.startswith("*"):
            # Command execution
            command = step.action[1:]
            return agent.process_message({"text": f"*{command}"}, context)
        else:
            # Method execution
            if hasattr(agent, step.action):
                method = getattr(agent, step.action)
                return method(context)
            else:
                # Fallback to message processing
                return agent.process_message({"text": step.action}, context)
    
    def _complete_step(self, execution: WorkflowExecution, step: WorkflowStep, result: Dict[str, Any]):
        """Complete a workflow step."""
        execution.completed_steps.append(step.id)
        execution.add_result(step.id, result)
        
        logger.info(f"Completed step {step.id}")
        
        # Proceed to next steps
        self._proceed_to_next_step(execution, step)
    
    def _proceed_to_next_step(self, execution: WorkflowExecution, step: WorkflowStep):
        """Proceed to the next step(s) in the workflow."""
        if not step.next_steps:
            # No more steps - workflow complete
            self._complete_workflow(execution)
            return
        
        # Execute next steps
        for next_step_id in step.next_steps:
            self._execute_step(execution, next_step_id)
    
    def _handle_agent_handoff(self, execution: WorkflowExecution, step: WorkflowStep, result: Dict[str, Any]):
        """Handle agent handoff during workflow."""
        target_agent_id = result.get("target_agent")
        handoff_context = result.get("context", {})
        
        # Update execution context
        execution.context.update(handoff_context)
        execution.context["handoff_from"] = step.agent_id
        execution.context["handoff_to"] = target_agent_id
        
        logger.info(f"Agent handoff: {step.agent_id} → {target_agent_id}")
        
        # Continue with next steps
        self._proceed_to_next_step(execution, step)
    
    def _handle_step_failure(self, execution: WorkflowExecution, step: WorkflowStep, error: str):
        """Handle step failure."""
        if step.on_failure:
            # Execute failure handler
            self._execute_step(execution, step.on_failure)
        else:
            # Default failure handling
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.now()
            logger.error(f"Workflow failed at step {step.id}: {error}")
    
    def _complete_workflow(self, execution: WorkflowExecution, final_result: Dict[str, Any] = None):
        """Complete workflow execution."""
        execution.status = WorkflowStatus.COMPLETED
        execution.completed_at = datetime.now()
        execution.duration = (execution.completed_at - execution.started_at).total_seconds()
        
        # Update user context
        user_id = execution.context.get("user_id")
        if user_id:
            self.context_manager.complete_workflow(
                user_id,
                execution.execution_id,
                final_result or {"completed_steps": execution.completed_steps}
            )
        
        logger.info(f"Completed workflow {execution.workflow.id}: {execution.execution_id}")
    
    def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow execution."""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return None
        
        return {
            "execution_id": execution_id,
            "workflow_id": execution.workflow.id,
            "status": execution.status.value,
            "current_step": execution.current_step,
            "completed_steps": execution.completed_steps,
            "failed_steps": execution.failed_steps,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "duration": execution.duration
        }
    
    def pause_workflow(self, execution_id: str):
        """Pause a workflow execution."""
        execution = self.active_executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.PAUSED
            logger.info(f"Paused workflow: {execution_id}")
    
    def resume_workflow(self, execution_id: str):
        """Resume a paused workflow."""
        execution = self.active_executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.RUNNING
            logger.info(f"Resumed workflow: {execution_id}")
    
    def cancel_workflow(self, execution_id: str):
        """Cancel a workflow execution."""
        execution = self.active_executions.get(execution_id)
        if execution:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.now()
            logger.info(f"Cancelled workflow: {execution_id}")
    
    def cleanup_completed_workflows(self, max_age_hours: int = 24):
        """Clean up old completed workflow executions."""
        now = datetime.now()
        to_remove = []
        
        for execution_id, execution in self.active_executions.items():
            if execution.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
                if execution.completed_at:
                    age_hours = (now - execution.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        to_remove.append(execution_id)
        
        for execution_id in to_remove:
            del self.active_executions[execution_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old workflow executions")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get workflow engine statistics."""
        status_counts = {}
        for execution in self.active_executions.values():
            status = execution.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_workflows": len(self.workflows),
            "active_executions": len(self.active_executions),
            "status_distribution": status_counts
        }