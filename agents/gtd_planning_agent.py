"""
GTD Planning Agent - BMAD-inspired implementation.

This agent follows BMAD's Natural Planning Model patterns for breaking down
complex projects into actionable GTD task hierarchies.
"""

import logging
from typing import Any

import yaml

from framework.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class GTDPlanningAgent(BaseAgent):
    """
    GTD Planning Agent implementing David Allen's Natural Planning Model.

    Following BMAD patterns for:
    - Command-driven interactions
    - Context preservation across planning steps
    - Agent collaboration and handoffs
    - Structured output formats
    """

    def __init__(self, config: dict[str, Any], services: dict[str, Any] = None):
        """Initialize GTD Planning Agent with BMAD patterns."""
        super().__init__(config, services)

        # Service dependencies with error handling
        self.todoist_service = self.get_service("todoist")
        self.openai_service = self.get_service("openai")
        self.workflow_persistence = self.get_service("workflow_persistence")

        # Track available services
        self.has_todoist = self.todoist_service is not None
        self.has_openai = self.openai_service is not None
        self.has_persistence = self.workflow_persistence is not None

        if not self.has_todoist:
            logger.warning(
                f"{self.name}: Todoist service not available - task creation will be limited"
            )
        if not self.has_openai:
            logger.warning(
                f"{self.name}: OpenAI service not available - AI features will be limited"
            )
        if not self.has_persistence:
            logger.warning(
                f"{self.name}: Workflow persistence not available - workflows won't survive restarts"
            )

        # Planning configuration
        self.planning_config = config.get("config", {}).get("natural_planning", {})
        self.context_mapping = config.get("config", {}).get("context_mapping", {})
        self.templates = config.get("config", {}).get("templates", {})

        # Load project templates
        self.project_templates = self._load_project_templates()

        # Natural Planning Model steps
        self.planning_steps = self.planning_config.get(
            "steps",
            [
                "purpose_and_principles",
                "outcome_visioning",
                "brainstorming",
                "organizing",
                "next_actions",
            ],
        )

        # Task granularity settings
        granularity = self.planning_config.get("task_granularity", {})
        self.min_minutes = granularity.get("min_minutes", 2)
        self.max_minutes = granularity.get("max_minutes", 30)
        self.default_estimate = granularity.get("default_estimate", "10min")

        logger.info(f"Initialized {self.name} with Natural Planning Model")

    def can_handle(self, message: dict[str, Any]) -> bool:
        """
        Determine if this agent can handle planning-related messages.

        BMAD pattern: Clear capability boundaries
        """
        text = message.get("text", "").strip().lower()

        if not text:
            return False

        # Check for project planning indicators
        planning_indicators = [
            "break down",
            "breakdown",
            "plan out",
            "help me organize",
            "where do i start",
            "steps for",
            "project plan",
            "how do i",
        ]

        for indicator in planning_indicators:
            if indicator in text:
                return True

        # Check for outcome clarification requests
        clarification_indicators = [
            "what does success look like",
            "help me clarify",
            "not sure what i want",
            "vague idea",
            "general goal",
        ]

        for indicator in clarification_indicators:
            if indicator in text:
                return True

        # Check for complexity indicators
        complexity_indicators = ["complex", "overwhelming", "big project", "lots of moving parts"]

        for indicator in complexity_indicators:
            if indicator in text:
                return True

        return False

    def _process_agent_message(
        self, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process planning message following BMAD patterns.

        BMAD pattern: Context-aware message processing
        """
        text = message.get("text", "").strip()
        user_id = message.get("user", "unknown")

        # Check current planning context
        planning_state = self.get_context("planning_state")
        current_project = self.get_context("current_project")

        # Handle multi-step planning workflows
        if planning_state == "awaiting_outcome_clarification":
            return self._handle_outcome_clarification(text, user_id)
        elif planning_state == "awaiting_brainstorm_input":
            return self._handle_brainstorm_input(text, user_id)
        elif planning_state == "awaiting_organization_approval":
            return self._handle_organization_approval(text, user_id)

        # Handle new planning requests
        if any(phrase in text.lower() for phrase in ["break down", "breakdown", "plan out"]):
            return self._initiate_project_breakdown(text, user_id)
        elif any(phrase in text.lower() for phrase in ["clarify", "what does success"]):
            return self._initiate_outcome_clarification(text, user_id)
        else:
            return self._general_planning_guidance(text, user_id)

    # BMAD-style command implementations

    def cmd_breakdown(
        self, args: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Break down project using Natural Planning Model.

        BMAD pattern: Structured command with clear inputs/outputs
        """
        user_id = message.get("user", "unknown")
        return self._initiate_project_breakdown(args, user_id)

    def cmd_clarify_outcome(
        self, args: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Clarify project outcome and success criteria."""
        user_id = message.get("user", "unknown")
        return self._initiate_outcome_clarification(args, user_id)

    def cmd_brainstorm(
        self, args: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Facilitate brainstorming session."""
        user_id = message.get("user", "unknown")
        return self._facilitate_brainstorm(args, user_id)

    def cmd_organize_tasks(
        self, args: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Organize brainstormed items into structure."""
        user_id = message.get("user", "unknown")
        return self._organize_brainstormed_items(user_id)

    def cmd_next_actions(
        self, args: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract immediate next actions."""
        user_id = message.get("user", "unknown")
        return self._extract_next_actions(args, user_id)

    def cmd_estimate_project(
        self, args: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Estimate project timeline and effort."""
        user_id = message.get("user", "unknown")
        return self._estimate_project_effort(args, user_id)

    # Natural Planning Model implementation (BMAD-inspired structured approach)

    def _initiate_project_breakdown(self, project_description: str, user_id: str) -> dict[str, Any]:
        """
        Start Natural Planning Model breakdown.

        BMAD pattern: Multi-step workflow initiation
        """
        logger.info(f"Starting project breakdown for: {project_description}")

        # Check for template suggestions
        suggested_template = self._suggest_template(project_description)
        if suggested_template:
            template = self.project_templates.get("templates", {}).get(suggested_template)
            if template:
                return {
                    "response_type": "template_suggestion",
                    "project": project_description,
                    "suggested_template": suggested_template,
                    "template_name": template["name"],
                    "message": f"🚀 **Quick Start Option**\n\nI noticed you're working on: **{project_description}**\n\nI have a template for **{template['name']}** that might save you time!\n\n*Template includes:*\n- Pre-organized task categories\n- Common project phases\n- Estimated timeline: {template.get('time_estimate', 'varies')}\n\nWould you like to:",
                    "actions": [
                        {"label": "🚀 Use Template", "value": f"use_template_{suggested_template}"},
                        {"label": "📋 Custom Planning", "value": "custom_breakdown"},
                        {
                            "label": "👀 Preview Template",
                            "value": f"preview_template_{suggested_template}",
                        },
                    ],
                    "context_update": {
                        "potential_project": project_description,
                        "suggested_template": suggested_template,
                    },
                }

        # Store project context
        workflow_id = f"project_breakdown_{hash(project_description) % 100000}"
        self.update_context(
            {
                "current_project": project_description,
                "planning_state": "purpose_and_principles",
                "planning_step": 1,
                "planning_data": {},
                "workflow_id": workflow_id,
            }
        )

        # Save workflow state if persistence available
        if self.has_persistence:
            self._save_workflow_state(user_id, workflow_id)

        # Step 1: Purpose and Principles
        return {
            "response_type": "planning_step_1",
            "project": project_description,
            "step": "Purpose & Principles",
            "message": f"🎯 **Project Planning: {project_description}**\n\n**Step 1: Purpose & Principles**\n\nLet's clarify why this project matters:\n\n1. **Why** is this project important?\n2. What **problem** does it solve?\n3. What are the key **principles** or constraints?\n\nPlease share your thoughts on the purpose behind this project.",
            "workflow": {
                "name": "natural_planning",
                "step": 1,
                "total_steps": 5,
                "next_step": "outcome_visioning",
            },
            "context_update": {
                "planning_state": "awaiting_purpose_input",
                "current_project": project_description,
            },
        }

    def _handle_purpose_input(self, purpose_text: str, user_id: str) -> dict[str, Any]:
        """Handle purpose and principles input (Step 1)."""
        project = self.get_context("current_project")
        planning_data = self.get_context("planning_data", {})

        # Store purpose
        planning_data["purpose"] = purpose_text

        # Move to Step 2: Outcome Visioning
        self.update_context(
            {
                "planning_state": "awaiting_outcome_input",
                "planning_step": 2,
                "planning_data": planning_data,
            }
        )

        # Save workflow state
        if self.has_persistence:
            self._save_workflow_state(user_id)

        return {
            "response_type": "planning_step_2",
            "step": "Outcome Visioning",
            "message": "✅ **Purpose captured!**\n\n**Step 2: Outcome Visioning**\n\nNow let's envision success:\n\n1. When this project is **complete**, what will be different?\n2. How will you **know** it's done?\n3. What does \"**wild success**\" look like?\n\nPaint the picture of the successful outcome:",
            "workflow": {"step": 2, "total_steps": 5, "previous_data": {"purpose": purpose_text}},
        }

    def _handle_outcome_clarification(self, outcome_text: str, user_id: str) -> dict[str, Any]:
        """Handle outcome visioning input (Step 2)."""
        planning_data = self.get_context("planning_data", {})
        planning_data["outcome"] = outcome_text

        # Move to Step 3: Brainstorming
        self.update_context(
            {
                "planning_state": "awaiting_brainstorm_input",
                "planning_step": 3,
                "planning_data": planning_data,
            }
        )

        return {
            "response_type": "planning_step_3",
            "step": "Brainstorming",
            "message": "🎯 **Outcome defined!**\n\n**Step 3: Brainstorming**\n\nNow let's capture **everything** that might be involved:\n\n- All possible tasks and activities\n- Required resources and tools\n- People who need to be involved\n- Potential obstacles or challenges\n- Any dependencies or prerequisites\n\n*Don't filter yet - just brain dump everything!*\n\nWhat comes to mind?",
            "workflow": {"step": 3, "total_steps": 5},
        }

    def _handle_brainstorm_input(self, brainstorm_text: str, user_id: str) -> dict[str, Any]:
        """Handle brainstorming input (Step 3)."""
        planning_data = self.get_context("planning_data", {})

        # Parse brainstormed items
        brainstorm_items = self._parse_brainstorm_items(brainstorm_text)
        planning_data["brainstorm_items"] = brainstorm_items

        # Organize items automatically
        organized_structure = self._auto_organize_items(brainstorm_items)
        planning_data["organized_structure"] = organized_structure

        # Move to Step 4: Organization
        self.update_context(
            {
                "planning_state": "awaiting_organization_approval",
                "planning_step": 4,
                "planning_data": planning_data,
            }
        )

        # Present organized structure
        structure_display = self._format_organized_structure(organized_structure)

        return {
            "response_type": "planning_step_4",
            "step": "Organization",
            "message": f"🧠 **Brainstormed {len(brainstorm_items)} items!**\n\n**Step 4: Organization**\n\nHere's how I've organized your brainstormed items:\n\n{structure_display}\n\nDoes this structure make sense? Would you like to:\n\n1. ✅ **Approve** this organization\n2. ✏️ **Modify** the structure\n3. 🔄 **Reorganize** differently",
            "actions": [
                {"label": "✅ Approve", "value": "approve_organization"},
                {"label": "✏️ Modify", "value": "modify_structure"},
                {"label": "🔄 Reorganize", "value": "reorganize"},
            ],
            "workflow": {"step": 4, "total_steps": 5, "organized_items": len(brainstorm_items)},
        }

    def _handle_organization_approval(self, response: str, user_id: str) -> dict[str, Any]:
        """Handle organization approval (Step 4)."""
        planning_data = self.get_context("planning_data", {})

        if response.lower() in ["approve", "approve_organization", "yes", "looks good"]:
            # Move to Step 5: Next Actions
            return self._extract_next_actions_final_step(user_id)
        elif response.lower() in ["modify", "modify_structure", "change"]:
            return self._request_structure_modifications(user_id)
        else:
            return self._request_reorganization(user_id)

    def _extract_next_actions_final_step(self, user_id: str) -> dict[str, Any]:
        """Final step: Extract immediate next actions."""
        planning_data = self.get_context("planning_data", {})
        organized_structure = planning_data.get("organized_structure", {})

        # Extract immediate next actions
        next_actions = self._identify_immediate_actions(organized_structure)

        # Format for GTD Task Agent
        formatted_actions = []
        for action in next_actions:
            formatted_action = {
                "content": action["description"],
                "context": action.get("context", "@next"),
                "time_estimate": action.get("estimate", self.default_estimate),
                "project": self.get_context("current_project", "Project"),
            }
            formatted_actions.append(formatted_action)

        # Update context with completion
        self.update_context(
            {
                "planning_state": "completed",
                "planning_step": 5,
                "next_actions": formatted_actions,
                "project_structure": organized_structure,
            }
        )

        # Clean up workflow state since planning is complete
        if self.has_persistence:
            workflow_id = self.get_context("workflow_id")
            if workflow_id:
                self.workflow_persistence.delete_workflow_state(user_id, workflow_id)

        # Format display
        actions_display = "\n".join(
            [
                f"• **{action['content']}** ({action['time_estimate']}, {action['context']})"
                for action in formatted_actions
            ]
        )

        return {
            "response_type": "planning_complete",
            "step": "Next Actions",
            "project": self.get_context("current_project"),
            "next_actions": formatted_actions,
            "message": f"🎉 **Planning Complete!**\n\n**Step 5: Next Actions**\n\nHere are your immediate next actions:\n\n{actions_display}\n\nWould you like me to:\n\n1. 📝 **Create these tasks** in Todoist\n2. 🤝 **Hand off** to TaskFlow for individual task creation\n3. 📋 **Show full project** structure",
            "actions": [
                {"label": "📝 Create tasks", "value": "create_all_tasks"},
                {"label": "🤝 Hand to TaskFlow", "value": "handoff_to_taskflow"},
                {"label": "📋 Show structure", "value": "show_full_structure"},
            ],
            "handoff_ready": True,
            "target_agent": "gtd-task-agent",
        }

    # Helper methods following BMAD patterns

    def _parse_brainstorm_items(self, text: str) -> list[str]:
        """Parse brainstormed text into individual items."""
        # Split by common delimiters
        items = []

        # Try different splitting methods
        if "\n" in text:
            items = [line.strip() for line in text.split("\n") if line.strip()]
        elif "," in text:
            items = [item.strip() for item in text.split(",") if item.strip()]
        elif "." in text and len(text.split(".")) > 2:
            items = [item.strip() for item in text.split(".") if item.strip()]
        else:
            # Single item or paragraph - try to extract key phrases
            items = [text.strip()]

        # Clean up items
        cleaned_items = []
        for item in items:
            # Remove bullet points, numbers, etc.
            item = item.lstrip("-•*123456789. ")
            if len(item) > 3:  # Skip very short items
                cleaned_items.append(item)

        return cleaned_items

    def _auto_organize_items(self, items: list[str]) -> dict[str, Any]:
        """Organize brainstormed items into logical structure."""
        # Simple categorization logic (can be enhanced with AI)
        categories = {
            "Planning & Research": [],
            "Development & Creation": [],
            "Communication & Coordination": [],
            "Testing & Quality": [],
            "Launch & Deployment": [],
            "Other": [],
        }

        # Categorize items based on keywords
        for item in items:
            item_lower = item.lower()

            if any(
                word in item_lower
                for word in ["research", "plan", "analyze", "study", "investigate"]
            ):
                categories["Planning & Research"].append(item)
            elif any(
                word in item_lower
                for word in ["build", "create", "develop", "design", "write", "code"]
            ):
                categories["Development & Creation"].append(item)
            elif any(
                word in item_lower
                for word in ["email", "call", "meeting", "discuss", "coordinate", "contact"]
            ):
                categories["Communication & Coordination"].append(item)
            elif any(
                word in item_lower
                for word in ["test", "review", "check", "validate", "verify", "quality"]
            ):
                categories["Testing & Quality"].append(item)
            elif any(
                word in item_lower for word in ["launch", "deploy", "release", "publish", "go live"]
            ):
                categories["Launch & Deployment"].append(item)
            else:
                categories["Other"].append(item)

        # Remove empty categories
        return {cat: items for cat, items in categories.items() if items}

    def _format_organized_structure(self, structure: dict[str, list]) -> str:
        """Format organized structure for display."""
        formatted = []

        for category, items in structure.items():
            formatted.append(f"**{category}:**")
            for item in items:
                formatted.append(f"  • {item}")
            formatted.append("")  # Empty line between categories

        return "\n".join(formatted)

    def _identify_immediate_actions(self, structure: dict[str, list]) -> list[dict[str, Any]]:
        """Identify immediate next actions from organized structure."""
        next_actions = []

        # Take first item from each category as potential next action
        priority_order = [
            "Planning & Research",
            "Communication & Coordination",
            "Development & Creation",
            "Testing & Quality",
            "Launch & Deployment",
            "Other",
        ]

        for category in priority_order:
            if category in structure and structure[category]:
                first_item = structure[category][0]

                # Determine context based on category
                context = self._determine_context(category, first_item)
                estimate = self._estimate_task_time(first_item)

                next_actions.append(
                    {
                        "description": first_item,
                        "context": context,
                        "estimate": estimate,
                        "category": category,
                    }
                )

                # Limit to 5 immediate actions
                if len(next_actions) >= 5:
                    break

        return next_actions

    def _determine_context(self, category: str, task: str) -> str:
        """Determine GTD context for a task."""
        task_lower = task.lower()

        # Context mapping from config
        for task_type, context in self.context_mapping.items():
            if task_type in task_lower:
                return context

        # Category-based context
        category_contexts = {
            "Planning & Research": "@computer",
            "Development & Creation": "@computer",
            "Communication & Coordination": "@phone",
            "Testing & Quality": "@computer",
            "Launch & Deployment": "@computer",
            "Other": "@anywhere",
        }

        return category_contexts.get(category, "@next")

    def _estimate_task_time(self, task: str) -> str:
        """Estimate time for a task."""
        task_lower = task.lower()

        # Simple heuristics
        if any(word in task_lower for word in ["quick", "check", "call", "email"]):
            return "2min"
        elif any(word in task_lower for word in ["research", "analyze", "review", "plan"]):
            return "30+min"
        else:
            return self.default_estimate

    # Persistence helper methods

    def _save_workflow_state(self, user_id: str, workflow_id: str = None):
        """Save current workflow state to persistence."""
        if not self.has_persistence:
            return

        workflow_id = workflow_id or self.get_context("workflow_id")
        if not workflow_id:
            return

        state_data = {
            "current_project": self.get_context("current_project"),
            "planning_state": self.get_context("planning_state"),
            "planning_step": self.get_context("planning_step"),
            "planning_data": self.get_context("planning_data", {}),
            "context": self.context_data,
        }

        self.workflow_persistence.save_workflow_state(
            user_id, workflow_id, self.agent_id, state_data
        )

    def _load_workflow_state(self, user_id: str, workflow_id: str) -> bool:
        """Load workflow state from persistence."""
        if not self.has_persistence:
            return False

        saved_state = self.workflow_persistence.load_workflow_state(user_id, workflow_id)
        if saved_state and saved_state.get("agent_id") == self.agent_id:
            state_data = saved_state.get("state_data", {})

            # Restore context
            self.context_data = state_data.get("context", {})

            logger.info(f"Restored workflow state for user {user_id}, workflow {workflow_id}")
            return True

        return False

    def cmd_resume(
        self, args: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Resume a previous planning session."""
        user_id = message.get("user", "unknown")

        if not self.has_persistence:
            return {
                "response_type": "error",
                "message": "Workflow persistence is not available. Cannot resume workflows.",
            }

        # Get active workflows for user
        active_workflows = self.workflow_persistence.get_active_workflows(user_id)

        if not active_workflows:
            return {
                "response_type": "no_active_workflows",
                "message": "No active planning sessions found. Start a new one with *breakdown [project]",
            }

        # If only one workflow, resume it
        if len(active_workflows) == 1:
            workflow = active_workflows[0]
            if self._load_workflow_state(user_id, workflow["workflow_id"]):
                # Continue from current state
                planning_state = self.get_context("planning_state")
                project = self.get_context("current_project")

                return {
                    "response_type": "workflow_resumed",
                    "message": f"Resumed planning for: **{project}**\n\nCurrent state: {planning_state}\n\nPlease continue where you left off.",
                    "workflow_id": workflow["workflow_id"],
                    "planning_state": planning_state,
                }

        # Multiple workflows - show list
        workflow_list = "\n".join(
            [f"• {w['workflow_id']} (updated: {w['updated_at']})" for w in active_workflows[:5]]
        )

        return {
            "response_type": "multiple_workflows",
            "message": f"Found {len(active_workflows)} active planning sessions:\n\n{workflow_list}\n\nSpecify which one to resume.",
            "workflows": active_workflows,
        }

    def _load_project_templates(self) -> dict[str, Any]:
        """Load project templates from YAML file."""
        try:
            import os

            templates_path = "templates/project_templates.yaml"

            if os.path.exists(templates_path):
                with open(templates_path) as f:
                    template_data = yaml.safe_load(f)
                logger.info(f"Loaded {len(template_data.get('templates', {}))} project templates")
                return template_data
            else:
                logger.warning("Project templates file not found - templates unavailable")
                return {"templates": {}, "template_keywords": {}}

        except Exception as e:
            logger.error(f"Error loading project templates: {e}")
            return {"templates": {}, "template_keywords": {}}

    def _suggest_template(self, project_description: str) -> str | None:
        """Suggest a template based on project description."""
        description_lower = project_description.lower()

        template_keywords = self.project_templates.get("template_keywords", {})

        for template_id, keywords in template_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return template_id

        return None

    def cmd_template(
        self, args: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Use a project template for quick setup."""
        user_id = message.get("user", "unknown")

        if not args:
            # Show available templates
            templates = self.project_templates.get("templates", {})
            if not templates:
                return {
                    "response_type": "no_templates",
                    "message": "No project templates are currently available.",
                }

            template_list = "\n".join(
                [
                    f"• **{template_id}**: {template_data['name']} - {template_data['description']}"
                    for template_id, template_data in templates.items()
                ]
            )

            return {
                "response_type": "template_list",
                "message": f"📋 **Available Project Templates:**\n\n{template_list}\n\nUse: *template [template_id] [your project name]",
            }

        # Parse template request
        parts = args.split(" ", 1)
        template_id = parts[0]
        project_name = (
            parts[1] if len(parts) > 1 else f"New {template_id.replace('_', ' ').title()}"
        )

        template = self.project_templates.get("templates", {}).get(template_id)
        if not template:
            return {
                "response_type": "template_not_found",
                "message": f"Template '{template_id}' not found. Use *template to see available templates.",
            }

        # Apply template to create project structure
        return self._apply_template(template, project_name, user_id)

    def _apply_template(
        self, template: dict[str, Any], project_name: str, user_id: str
    ) -> dict[str, Any]:
        """Apply a template to create a structured project."""
        workflow_id = f"template_{hash(project_name) % 100000}"

        # Set up context with template data
        planning_data = {
            "purpose": template.get("purpose", ""),
            "outcome": template.get("vision", ""),
            "brainstorm_items": [],
            "organized_structure": template.get("categories", {}),
        }

        # Flatten categories into brainstorm items for consistency
        for category, items in template.get("categories", {}).items():
            planning_data["brainstorm_items"].extend(items)

        self.update_context(
            {
                "current_project": project_name,
                "planning_state": "template_applied",
                "planning_step": 4,  # Skip to organization step
                "planning_data": planning_data,
                "workflow_id": workflow_id,
                "template_used": template["name"],
            }
        )

        # Save workflow state
        if self.has_persistence:
            self._save_workflow_state(user_id, workflow_id)

        # Format the template structure for display
        structure_display = self._format_organized_structure(template.get("categories", {}))

        return {
            "response_type": "template_applied",
            "template_name": template["name"],
            "project": project_name,
            "message": f"📋 **Applied Template: {template['name']}**\n\nProject: **{project_name}**\n\n**Pre-organized Structure:**\n\n{structure_display}\n\nTime Estimate: {template.get('time_estimate', 'varies')}\n\nReady to extract next actions or would you like to modify this structure?",
            "actions": [
                {"label": "✅ Extract Next Actions", "value": "extract_actions"},
                {"label": "✏️ Modify Structure", "value": "modify_structure"},
                {"label": "🔄 Start Custom Planning", "value": "custom_planning"},
            ],
            "context_update": {
                "template_structure": template.get("categories", {}),
                "ready_for_actions": True,
            },
        }
