"""
FlowCoach Agent Framework - Python implementation inspired by BMAD-METHOD.

This framework provides BMAD-style agent patterns in Python, enabling:
- Declarative agent definitions via YAML
- Command-based agent interactions
- Workflow orchestration
- Agent collaboration and handoffs
- Context preservation across conversations
"""

from .agent_registry import AgentRegistry
from .base_agent import BaseAgent
from .context_manager import ContextManager
from .workflow_engine import WorkflowEngine

__version__ = "1.0.0"
__all__ = ["BaseAgent", "WorkflowEngine", "AgentRegistry", "ContextManager"]
