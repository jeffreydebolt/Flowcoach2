# FlowCoach Refactoring Documentation

## Overview

This document provides a detailed explanation of the refactoring performed on the FlowCoach Slack bot. The refactoring focused on implementing an agentic architecture, improving code organization, enhancing error handling, and streamlining integrations.

## Original Issues

The original codebase had several issues:

1. **Code Structure Issues**:
   - Redundancy between code in the root directory and the `flowcoach_new` subdirectory
   - Presence of experimental or obsolete files
   - Large service files handling multiple responsibilities
   - Inconsistent imports and structural organization

2. **Integration Problems**:
   - Inconsistent use of Todoist libraries
   - Google Calendar authentication not suitable for a multi-user Slack bot
   - OpenAI models and prompts hardcoded

3. **State Management**:
   - Inconsistent conversation state handling
   - Unreliable multi-turn interactions

4. **Error Handling**:
   - Too many broad exception catches hiding specific issues
   - Generic error messages

## Refactoring Approach

The refactoring followed a complete rewrite approach, creating a new, clean project structure with:

1. **Agentic Architecture**: Specialized agents for different domains (task, calendar, communication)
2. **Modular Design**: Clear separation of concerns with dedicated modules
3. **Centralized Configuration**: All settings in one place
4. **Improved Error Handling**: More specific exception handling
5. **Enhanced State Management**: Consistent conversation state handling

## Key Components

### Configuration System

The configuration system centralizes all settings in the `config` module, making it easy to customize the bot's behavior through environment variables.

### Agentic Architecture

The bot uses an agentic architecture with three main agents:

1. **Task Agent**: Handles task creation, formatting, and management
2. **Calendar Agent**: Manages calendar integration and scheduling
3. **Communication Agent**: Handles user interactions and messaging

Each agent has a specific domain of responsibility and can process messages independently.

### Service Integrations

The service integrations have been improved:

1. **Todoist Service**: Uses the official Todoist API Python SDK
2. **Calendar Service**: Improved OAuth flow and focus block calculation
3. **OpenAI Service**: Configurable models and prompts

### Handlers

The handlers have been reorganized:

1. **Message Handlers**: Process incoming messages and route them to the appropriate agent
2. **Action Handlers**: Handle interactive components like buttons
3. **Event Handlers**: Handle Slack events like app mentions and team joins

## Implementation Details

### Directory Structure

```
flowcoach_refactored/
├── app.py                  # Main entry point
├── config/                 # Configuration module
├── core/                   # Core agents
│   ├── base_agent.py       # Base agent class
│   ├── task_agent.py       # Task management agent
│   ├── calendar_agent.py   # Calendar integration agent
│   └── communication_agent.py # User interaction agent
├── handlers/               # Slack event handlers
│   ├── message_handlers.py # Message handling
│   ├── action_handlers.py  # Interactive component handling
│   └── event_handlers.py   # Slack event handling
├── services/               # External service integrations
│   ├── todoist_service.py  # Todoist API integration
│   ├── calendar_service.py # Google Calendar integration
│   └── openai_service.py   # OpenAI API integration
├── models/                 # Data models (for future use)
├── utils/                  # Utility functions (for future use)
├── tests/                  # Test scripts
└── scripts/                # Utility scripts
```

### Workflow

1. User sends a message to the bot
2. Message handler receives the message
3. Message is routed to the appropriate agent based on content
4. Agent processes the message and returns a response
5. Response is formatted and sent back to the user

## Future Enhancements

The refactored codebase is designed to be easily extensible. Future enhancements could include:

1. **Email Integration**: Connecting to email services for digests
2. **Advanced Delegation**: More sophisticated delegation suggestions
3. **Project Management**: Enhanced project tracking and management
4. **Analytics**: Insights into productivity patterns
5. **Multi-User Support**: Better handling of multiple users

## Migration Guide

To migrate from the old codebase to the new one:

1. Copy your `.env` file with API keys
2. Run the Google Calendar authentication script
3. Update any custom configurations in the `.env` file
4. Start the bot with `python app.py`

## Testing

The refactored codebase includes test scripts for all major components:

1. `test_basic.py`: Tests basic functionality
2. `test_todoist.py`: Tests Todoist integration
3. `test_calendar.py`: Tests Google Calendar integration
4. `test_openai.py`: Tests OpenAI integration

Run these tests to verify that everything is working correctly.
