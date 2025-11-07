# Database Schema

## Overview

FlowCoach uses SQLite for local development and testing, with plans to migrate to PostgreSQL for production deployment. All database operations in Sprint 1.5+ include retry logic to handle transient connection issues.

## Reliability Features (Sprint 1.5)

- **Automatic Retry**: All database operations retry up to 3 times on transient errors
- **Exponential Backoff**: Retry delays increase progressively (0.1s → 0.2s → 0.4s)
- **Error Logging**: Failed operations logged to `events` table for monitoring
- **Health Monitoring**: Database connectivity checked via `/health` endpoint

## Tables

### weekly_outcomes

Stores user's weekly goals/outcomes for prioritization.

```sql
CREATE TABLE weekly_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,           -- Slack user ID
    week_start DATE NOT NULL,        -- Monday of the week (YYYY-MM-DD)
    outcomes TEXT NOT NULL,          -- JSON array of 3 outcome strings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, week_start)
);
```

### task_scores

Stores impact/urgency/energy scores for deep work tasks.

```sql
CREATE TABLE task_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,   -- Todoist task ID
    impact INTEGER NOT NULL,        -- 1-5 scale
    urgency INTEGER NOT NULL,       -- 1-5 scale
    energy TEXT NOT NULL,           -- 'am' or 'pm'
    total_score INTEGER NOT NULL,   -- Calculated total (impact + urgency + energy_bonus)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### morning_brief_tasks

Tracks which tasks were surfaced in morning briefs for evening comparison.

```sql
CREATE TABLE morning_brief_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,          -- Slack user ID
    task_id TEXT NOT NULL,          -- Todoist task ID
    task_content TEXT NOT NULL,     -- Task content at time of surfacing
    surfaced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'surfaced'  -- 'surfaced', 'completed', 'snoozed', 'moved'
);
```

### events

General event/audit log for monitoring and debugging. Enhanced in Sprint 1.5 for better error tracking.

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    severity TEXT NOT NULL,         -- 'info', 'warning', 'error', 'critical'
    action TEXT NOT NULL,           -- Event type (e.g., 'morning_brief_sent', 'db_retry_exhausted')
    payload TEXT,                   -- JSON data related to event
    user_id TEXT                    -- Optional Slack user ID
);
```

**Sprint 1.5 Event Types**:

- `db_retry_exhausted`: Database operation failed after all retries
- `config_validation_failed`: Startup configuration validation errors
- `health_check_error`: Health endpoint errors
- `token_validation_failed`: API token authentication failures

## Indexes

Recommended indexes for performance:

```sql
CREATE INDEX idx_weekly_outcomes_user_week ON weekly_outcomes(user_id, week_start);
CREATE INDEX idx_task_scores_task_id ON task_scores(task_id);
CREATE INDEX idx_morning_brief_user_date ON morning_brief_tasks(user_id, surfaced_at);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_action ON events(action);
```

## Data Examples

### Weekly Outcomes

```json
{
  "user_id": "U123456789",
  "week_start": "2024-03-04",
  "outcomes": [
    "Ship v2.1 to production",
    "Improve page load speed by 20%",
    "Complete team 1:1 sessions"
  ]
}
```

### Task Score

```json
{
  "task_id": "7896543210",
  "impact": 4,
  "urgency": 3,
  "energy": "am",
  "total_score": 8
}
```

### Event Log Entry

```json
{
  "severity": "info",
  "action": "morning_brief_sent",
  "payload": {
    "user_id": "U123456789",
    "task_count": 3,
    "task_ids": ["7896543210", "7896543211", "7896543212"]
  },
  "user_id": "U123456789"
}
```
