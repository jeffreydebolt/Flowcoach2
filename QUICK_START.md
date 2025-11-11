# FlowCoach Quick Start Guide

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- Todoist account and API token
- Claude API key (for TypeScript CLI)
- Slack workspace (optional, for bot)

### Initial Setup

```bash
# Install dependencies
pip install -r requirements.txt
npm install

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys
```

## 🎯 Using FlowCoach CLI

### Basic Commands

```bash
# Organize tasks with time estimates
npm run dev -- organize "1) email Sarah - 5 min 2) review proposal - 30 min 3) plan Q1 roadmap"

# Preview shows parsed tasks - then accept to create in Todoist
npm run dev -- accept

# Break down complex projects
npm run dev -- breakdown "#1"

# Resume last session
npm run dev -- resume

# Discard current session
npm run dev -- discard
```

### Examples

```bash
# Quick tasks
npm run dev -- organize "call mom, buy milk - 2 min, fix login bug - 30+"

# Project planning
npm run dev -- organize "plan website redesign, create mockups, get team feedback"

# Daily planning
npm run dev -- organize "1. morning standup 2. code review PR #123 - 20 min 3. implement user auth"
```

## 🤖 Using Slack Bot

### Setup

1. Create Slack app at api.slack.com
2. Add Bot Token Scopes: `chat:write`, `im:history`, `app_mentions:read`
3. Enable Socket Mode
4. Install app to workspace
5. Add tokens to .env

### Running the Bot

```bash
python app.py
```

### Slack Commands

- DM the bot: `organize: email client, prep meeting, review docs`
- Mention in channel: `@flowcoach breakdown project update presentation`
- Use buttons to accept/modify tasks

## 📊 Time Buckets

Tasks are automatically categorized:

- **2 min** (@t_2min): Quick wins (≤5 min)
- **10 min** (@t_10min): Focused work (6-15 min)
- **30+ min** (@t_30plus): Deep work (>15 min)

## 🔧 Development Commands

### Code Quality

```bash
# Format Python code
black .

# Format TypeScript
npm run format

# Run linters
flake8
npm run lint

# Run all checks
./scripts/lint.sh
```

### Testing

```bash
# Python tests
pytest

# TypeScript tests
npm test

# Test specific features
python tests/test_calendar.py
npm run dev -- test
```

## 🗄️ Database

### View Sessions

```bash
sqlite3 flowcoach.db "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5;"
```

### Reset Database

```bash
rm flowcoach.db
# Database recreates automatically on next run
```

## 🔑 Environment Variables

### Required

- `CLAUDE_API_KEY` - For advanced parsing
- `TODOIST_API_TOKEN` - For task creation

### Optional

- `SLACK_BOT_TOKEN` - For Slack bot
- `SLACK_APP_TOKEN` - For Socket Mode
- `GOOGLE_CALENDAR_CREDENTIALS` - For calendar integration

### Configuration

- `FC_DEFAULT_PROJECT` - Default Todoist project ID
- `FC_LABEL_MODE` - "labels" or "prefix" for time estimates
- `LOG_LEVEL` - "debug", "info", "warning", "error"

## 🆘 Troubleshooting

### Common Issues

1. **"No API key found"**

   - Check .env file exists and has keys
   - Ensure no spaces around = in .env

2. **"Cannot connect to Todoist"**

   - Verify API token is correct
   - Check internet connection
   - Try regenerating token

3. **"Session not found"**

   - Run `npm run dev -- resume` to check
   - May need to start fresh with organize

4. **Pre-commit hook failures**
   - Run `black .` for Python
   - Run `npm run format` for TypeScript
   - Then retry commit

## 📚 Further Reading

- [Architecture Documentation](docs/architecture/index.md)
- [Development Workflow](docs/architecture/developer-workflow.md)
- [API Integration Guide](docs/architecture/integration-architecture.md)
