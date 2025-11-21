"""Natural language processing modules for FlowCoach."""

from .parser import ParsedTask, parse_task_input

__all__ = ["parse_task_input", "ParsedTask"]
