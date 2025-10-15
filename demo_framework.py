"""
Demo of the BMAD-inspired FlowCoach Agent Framework.

This demonstrates:
- Loading agents from YAML definitions
- Agent registration and discovery
- Command-based interactions
- Context management
- Agent collaboration patterns
"""

import logging
import sys
from pathlib import Path

# Add framework to path
sys.path.append(str(Path(__file__).parent))

from framework import BaseAgent, AgentRegistry, ContextManager, WorkflowEngine
from agents.gtd_task_agent import GTDTaskAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockTodoistService:
    """Mock Todoist service for demo purposes."""
    
    def __init__(self):
        self.tasks = []
        self.task_id_counter = 1
    
    def add_task(self, content, project="Inbox", labels=None):
        """Add a task."""
        task = {
            "id": str(self.task_id_counter),
            "content": content,
            "project": project,
            "labels": labels or [],
            "completed": False
        }
        self.tasks.append(task)
        self.task_id_counter += 1
        logger.info(f"Created Todoist task: {content}")
        return task
    
    def get_tasks(self):
        """Get all tasks."""
        return self.tasks


def demo_agent_framework():
    """Demonstrate the agent framework capabilities."""
    print("🚀 FlowCoach Agent Framework Demo")
    print("=" * 50)
    
    # 1. Initialize core components
    print("\n📦 Initializing Framework Components...")
    
    # Mock services
    services = {
        "todoist_service": MockTodoistService()
    }
    
    # Create framework components
    context_manager = ContextManager()
    agent_registry = AgentRegistry(services)
    workflow_engine = WorkflowEngine(agent_registry, context_manager)
    
    print("✅ Framework initialized")
    
    # 2. Register agents
    print("\n🤖 Registering Agents...")
    
    # Load GTD Task Agent from YAML
    try:
        agent = GTDTaskAgent.from_yaml("agents/gtd_task_agent.yaml", services)
        agent_registry.register_agent_instance(agent)
        print(f"✅ Registered: {agent.name} ({agent.agent_id})")
    except Exception as e:
        print(f"❌ Failed to load GTD Task Agent: {e}")
        return
    
    # 3. Demonstrate agent capabilities
    print("\n🔍 Agent Capabilities:")
    capabilities = agent_registry.get_agent_capabilities("gtd-task-agent")
    if capabilities:
        print(f"  Name: {capabilities['name']}")
        print(f"  Description: {capabilities['description']}")
        print(f"  Commands: {', '.join(capabilities['commands'])}")
    
    # 4. Test agent activation
    print("\n⚡ Activating Agent...")
    activation_response = agent.activate()
    print(f"Agent Response:\n{activation_response['message']}")
    
    # 5. Test command handling
    print("\n💬 Testing Commands...")
    
    test_commands = [
        "*help",
        "*capture call dentist for appointment",
        "*format-gtd review quarterly budget spreadsheet", 
        "*project-check build new website for client",
        "email John about meeting tomorrow"  # Natural language
    ]
    
    user_id = "demo_user"
    
    for command in test_commands:
        print(f"\n🎯 Input: '{command}'")
        
        # Get user context
        context = context_manager.get_context(user_id)
        
        # Process message
        message = {"text": command, "user": user_id}
        response = agent.process_message(message, context)
        
        # Show response
        print(f"📤 Response: {response.get('message', response)}")
        
        # Update context if needed
        if "context_update" in response:
            context_manager.update_context(user_id, response["context_update"])
    
    # 6. Test agent discovery
    print("\n🔎 Testing Agent Discovery...")
    
    test_messages = [
        {"text": "create a task to buy groceries", "user": user_id},
        {"text": "help me plan my day", "user": user_id},
        {"text": "what's the weather like?", "user": user_id}
    ]
    
    for msg in test_messages:
        found_agent = agent_registry.find_agent_for_message(msg)
        agent_name = found_agent.name if found_agent else "None"
        print(f"  '{msg['text']}' → {agent_name}")
    
    # 7. Show created tasks
    print("\n📝 Created Tasks:")
    todoist_service = services["todoist_service"]
    for task in todoist_service.get_tasks():
        print(f"  [{task['id']}] {task['content']} (Project: {task['project']})")
    
    # 8. Context and workflow stats
    print("\n📊 Framework Statistics:")
    agent_stats = agent_registry.get_statistics()
    context_stats = context_manager.get_statistics()
    workflow_stats = workflow_engine.get_statistics()
    
    print(f"  Agents: {agent_stats['total_agents']}")
    print(f"  Commands: {agent_stats['total_commands']}")
    print(f"  Active Contexts: {context_stats['active_contexts']}")
    print(f"  Workflows: {workflow_stats['total_workflows']}")
    
    print("\n🎉 Demo Complete!")
    print("\nThe framework demonstrates:")
    print("• ✅ BMAD-inspired agent patterns")
    print("• ✅ YAML-based agent definitions")
    print("• ✅ Command routing and processing")
    print("• ✅ Context management")
    print("• ✅ Service integration")
    print("• ✅ Agent discovery and collaboration")


if __name__ == "__main__":
    demo_agent_framework()