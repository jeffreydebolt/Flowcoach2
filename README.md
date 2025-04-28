# FlowCoach - GTD Assistant for Slack

FlowCoach is a Slack bot that helps you manage your tasks using GTD (Getting Things Done) principles, schedule focus time, and prioritize your work.

## Features

- **Task Management**: Create tasks with natural language, automatically formatted according to GTD principles
- **Time Estimation**: Tag tasks by how long they'll take (2min, 10min, 30+min)
- **Task Breakdown**: Break complex tasks into smaller, actionable subtasks
- **Calendar Integration**: Find focus blocks in your calendar and schedule time for tasks
- **Agentic Architecture**: Specialized agents handle different aspects of productivity

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/flowcoach.git
   cd flowcoach
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_APP_TOKEN=xapp-your-token
   TODOIST_API_TOKEN=your-todoist-token
   OPENAI_API_KEY=your-openai-key
   ```

4. Set up Google Calendar authentication:
   ```
   python scripts/authenticate_calendar.py
   ```

5. Run the bot:
   ```
   python app.py
   ```

## Usage

Once the bot is running and added to your Slack workspace, you can interact with it in the following ways:

### Task Management

- Create a task: `Add a task to write documentation`
- Review tasks: `Show my tasks`
- Break down a task: `Break down the website redesign task`

### Calendar Management

- View your schedule: `What's my calendar today?`
- Find focus time: `When do I have focus time today?`
- Schedule a task: `Schedule time for the documentation task`

### General Help

- Get help: `help` or `What can you do?`

## Architecture

FlowCoach uses an agentic architecture with specialized agents for different domains:

- **Task Agent**: Handles task creation, formatting, and management
- **Calendar Agent**: Manages calendar integration and scheduling
- **Communication Agent**: Handles user interactions and messaging

These agents work together to provide a seamless productivity experience.

## Services

FlowCoach integrates with the following services:

- **Todoist**: For task management
- **Google Calendar**: For calendar integration and scheduling
- **OpenAI**: For natural language processing and task formatting

## Configuration

Configuration is centralized in the `config` module. You can customize the following settings in your `.env` file:

- `WORK_START_HOUR`: Start of your workday (default: 9)
- `WORK_END_HOUR`: End of your workday (default: 17)
- `MIN_FOCUS_BLOCK_MINUTES`: Minimum duration for focus blocks (default: 30)
- `DEFAULT_GTD_PROJECT`: Default Todoist project for tasks (default: Inbox)
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-4)

## Testing

Run the tests to verify the functionality:

```
python -m tests.test_basic
python -m tests.test_todoist
python -m tests.test_calendar
python -m tests.test_openai
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
