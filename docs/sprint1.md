# FlowCoach Sprint 1: Core Rhythm Implementation

## Overview

Sprint 1 implements the core daily and weekly rhythm features for FlowCoach, including:

- Morning Brief (8:30 AM) with top 3 prioritized tasks
- Evening Wrap (6:00 PM) with progress recap and actions
- Weekly Outcomes prompting (Monday 9:00 AM)
- Adaptive scoring for deep work tasks
- Error handling and resilience

## What Was Built

### Job Infrastructure

- **Morning Brief Job**: Sends daily task priorities at 8:30 AM local time
- **Evening Wrap Job**: Reviews progress and offers actions at 6:00 PM
- **Weekly Outcomes Job**: Prompts for weekly goals on Monday mornings
- **Deep Work Scoring**: Automatic detection and scoring of complex tasks

### Core Components

- **Task Sorting Engine**: Prioritizes by weekly outcomes > @rev_driver > task scores > due dates
- **Slack Message Builder**: Rich interactive messages with buttons for actions
- **Todoist Client**: Robust API wrapper with retry logic and error handling
- **Database Layer**: SQLite schema for outcomes, scores, and event tracking

### Interactive Features

- Morning brief task actions: Done, Move to Today, Snooze
- Evening wrap actions: Move to Tomorrow, Pause Project, Archive
- Weekly outcomes capture and display via `/flow week` command
- Deep work task scoring with impact/urgency/energy metrics

## How to Run Jobs

### Prerequisites

Set environment variables in `.env`:

```bash
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
TODOIST_API_TOKEN=your-todoist-api-token
FC_ACTIVE_USERS=U123456789,U987654321  # Comma-separated Slack user IDs
FC_DEFAULT_TIMEZONE=America/Denver      # Optional, defaults to Mountain Time
FC_DB_PATH=./flowcoach.db              # Optional, defaults to ./flowcoach.db
```

### Running Individual Jobs

#### Morning Brief

```bash
cd /path/to/flowcoach_refactored
python -m apps.server.jobs.morning_brief
```

#### Evening Wrap

```bash
python -m apps.server.jobs.evening_wrap
```

#### Weekly Outcomes

```bash
python -m apps.server.jobs.weekly_outcomes
```

#### Deep Work Scoring

```bash
python -m apps.server.jobs.score_tasks
```

### Production Scheduling

For production deployment, schedule jobs with cron or equivalent:

```bash
# Morning brief at 8:30 AM
30 8 * * * /usr/bin/python -m apps.server.jobs.morning_brief

# Evening wrap at 6:00 PM
0 18 * * * /usr/bin/python -m apps.server.jobs.evening_wrap

# Weekly outcomes on Monday at 9:00 AM
0 9 * * 1 /usr/bin/python -m apps.server.jobs.weekly_outcomes

# Deep work scoring every 2 hours during work days
0 9,11,13,15,17 * * 1-5 /usr/bin/python -m apps.server.jobs.score_tasks
```

## How to Run Tests

### Unit Tests

```bash
# All unit tests
python -m pytest apps/server/tests/unit/

# Specific test modules
python -m pytest apps/server/tests/unit/test_sorting.py
python -m pytest apps/server/tests/unit/test_scoring.py
python -m pytest apps/server/tests/unit/test_messages.py
```

### Integration Tests

```bash
# All integration tests
python -m pytest apps/server/tests/integration/

# Specific integration test
python -m pytest apps/server/tests/integration/test_morning_brief_flow.py
```

### Coverage

```bash
# Run tests with coverage
python -m pytest --cov=apps.server --cov-report=html

# Open coverage report
open htmlcov/index.html
```

## Configuration

### Slack Setup

1. Create Slack app at https://api.slack.com/apps
2. Add Bot Token Scopes: `chat:write`, `users:read`, `im:history`
3. Enable Socket Mode (for real-time features)
4. Install app to workspace and copy bot token

### Todoist Setup

1. Go to Todoist Settings > Integrations > API token
2. Copy token to `TODOIST_API_TOKEN` environment variable
3. Note your default project ID for `FC_DEFAULT_PROJECT` (optional)

### Testing Configuration

For local testing without hitting live APIs:

```bash
# Set mock mode (if implemented)
FC_TEST_MODE=true

# Use test user IDs
FC_ACTIVE_USERS=U000000000  # Your test Slack user ID
```

## Slack Commands

### Interactive Commands

- **`/flow week`**: View and update weekly outcomes
- **Morning brief buttons**: Done, Move to Today, Snooze
- **Evening wrap buttons**: Move to Tomorrow, Pause Project, Archive

### Weekly Outcomes

Reply to Monday morning prompt with:

```
1. Ship feature X to production
2. Improve page load times by 20%
3. Complete Q1 planning sessions
```

Or bullet points:

```
• Launch new dashboard
• Fix critical bugs
• Team retrospective
```

### Deep Work Scoring

When prompted for task scoring, reply with:

```
4/3/am
```

Format: `Impact/Urgency/Energy` where:

- Impact: 1-5 (low to high business impact)
- Urgency: 1-5 (low to high time pressure)
- Energy: 'am' or 'pm' (when you do your best work)

## Database

### View Current Data

```bash
# Connect to database
sqlite3 flowcoach.db

# View weekly outcomes
SELECT * FROM weekly_outcomes ORDER BY created_at DESC LIMIT 5;

# View task scores
SELECT * FROM task_scores ORDER BY total_score DESC LIMIT 10;

# View recent events
SELECT * FROM events WHERE severity = 'error' ORDER BY timestamp DESC LIMIT 10;
```

### Reset Data

```bash
# Clear all data (WARNING: destructive)
rm flowcoach.db

# Clear specific table
sqlite3 flowcoach.db "DELETE FROM weekly_outcomes WHERE user_id = 'U123456';"
```

## Troubleshooting

### Common Issues

1. **"No active users configured"**

   - Set `FC_ACTIVE_USERS` environment variable with Slack user IDs

2. **"SLACK_BOT_TOKEN not found"**

   - Ensure Slack bot token is in `.env` file
   - Check token has required permissions

3. **"TODOIST_API_TOKEN not found"**

   - Get API token from Todoist settings
   - Add to `.env` file

4. **Morning brief not sent**

   - Check user timezone in Slack profile
   - Verify job runs within 5-minute window of 8:30 AM local time
   - Check logs for errors

5. **Database errors**
   - Ensure write permissions for SQLite file
   - Check disk space
   - View error logs in events table

### Debugging

Enable debug logging:

```bash
LOG_LEVEL=debug python -m apps.server.jobs.morning_brief
```

View logs:

```bash
# Application logs
tail -f flowcoach.log

# Database event logs
sqlite3 flowcoach.db "SELECT * FROM events ORDER BY timestamp DESC LIMIT 20;"
```

## Architecture Notes

### Error Handling

- All external API calls use retry decorators with exponential backoff
- Fallback messages sent when primary functionality fails
- All errors logged to both file and database events table

### Database

- Uses SQLite for simplicity in Sprint 1
- Designed for easy migration to PostgreSQL in future sprints
- Singleton DAL (Data Access Layer) pattern for consistent access

### Slack Integration

- Interactive button actions update Todoist in real-time
- Timezone-aware scheduling based on user's Slack profile
- Graceful degradation when Slack API is unreachable

### Todoist Integration

- Thin wrapper with automatic retries and error handling
- Automatic label creation for scoring system
- Idempotent operations to prevent duplicate data
