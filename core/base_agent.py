"""
Base agent class for FlowCoach.

This module defines the BaseAgent class that all specialized agents will inherit from.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAgent(ABC):
    """
    Base class for all FlowCoach agents.
    
    Agents are responsible for handling specific domains of functionality
    such as task management, calendar integration, or communication.
    """
    
    def __init__(self, config: Dict[str, Any], services: Dict[str, Any]):
        """
        Initialize the base agent.
        
        Args:
            config: Configuration dictionary
            services: Dictionary of service instances
        """
        self.config = config
        self.services = services
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.info(f"Initializing {self.__class__.__name__}")
    
    @abstractmethod
    def process_message(self, message: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a message directed to this agent.
        
        Args:
            message: The message to process
            context: Additional context for processing
            
        Returns:
            Optional response data or None if no response
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this agent.
        
        Returns:
            Dictionary describing agent capabilities
        """
        pass
    
    def can_handle(self, message: Dict[str, Any]) -> bool:
        """
        Determine if this agent can handle the given message.
        
        Args:
            message: The message to check
            
        Returns:
            True if this agent can handle the message, False otherwise
        """
        # Default implementation to be overridden by subclasses
        return False
