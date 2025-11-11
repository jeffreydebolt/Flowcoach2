# FlowCoach

FlowCoach is a Slack bot that helps you manage your tasks and time using GTD (Getting Things Done) principles. It integrates with Todoist for task management and provides an intuitive interface for time estimation and task organization.

## Features

- Task creation with automatic GTD formatting
- Time estimation with [2min], [10min], [30+min] tags
- Integration with Todoist
- Smart task formatting using OpenAI
- Calendar integration for scheduling focus time (coming soon)

## Setup

1. Clone the repository

```bash
git clone https://github.com/yourusername/flowcoach.git
cd flowcoach
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:

```bash
# Required
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret
TODOIST_API_TOKEN=your-todoist-token

# Optional
OPENAI_API_KEY=your-openai-key
TZ=America/New_York

# FlowCoach v1 Feature Flags (default: false)
# Environment variables automatically map: FC_MORNING_MODAL_V1 → fc.morning_modal_v1
FC_INTERVIEW_MODAL_V1=true
FC_HOME_TAB_V1=true
FC_MORNING_MODAL_V1=false
FC_WRAP_MODAL_V1=false
FC_WEEKLY_MODAL_V1=false
FC_CHECKIN_V1=false
FC_INTENT_ROUTER_V1=false
```

4. Run the bot

```bash
python app.py
```

## Usage

In Slack, you can:

- Create tasks: "add a task to write documentation"
- Tasks will be formatted according to GTD principles
- Add time estimates using the buttons that appear
- Review tasks and get summaries of your workload

## Development

The project is structured as follows:

- `app.py`: Main application entry point
- `services/`: External service integrations (Todoist, Calendar, OpenAI)
- `handlers/`: Slack message and action handlers
- `core/`: Core business logic and agents
- `config/`: Configuration management
- `utils/`: Utility functions

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
