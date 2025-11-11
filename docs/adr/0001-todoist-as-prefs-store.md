# ADR-001: Use Todoist as Preferences Store

**Status:** Accepted
**Date:** 2025-11-10
**Deciders:** FlowCoach Team

## Context

FlowCoach v1 (BMAD implementation) needs to store user preferences including:

- Timezone and work schedule
- Energy windows for optimal task scheduling
- Quiet hours for notification control
- Daily rhythm preferences (morning brief, evening wrap times)

We need to decide between:

1. Adding database tables for preferences
2. Using Todoist metadata (labels/comments/project notes)
3. External storage service

## Decision

We will use **Todoist project notes** as the primary preferences store.

Specifically:

- Create a "FlowCoach" project in each user's Todoist
- Store preferences as JSON in a pinned task description
- Use task content "FlowCoach Preferences (Do not delete)" for identification
- Set high priority to keep it visible at the top

## Rationale

**Advantages of Todoist storage:**

- **No database changes** - preserves existing SQLite-based system
- **User-owned data** - preferences live in user's Todoist, not our systems
- **Automatic sync** - Todoist handles backup, sync, availability
- **Transparent** - users can see their preferences if needed
- **BMAD compliance** - uses existing Todoist integration
- **Incremental rollout** - can be feature-flagged independently

**Why not database storage:**

- Requires schema changes and migrations
- Another system to backup/maintain
- Data ownership questions
- More complex for multi-tenant scenarios

**Why not external service:**

- Additional dependency and failure mode
- More API calls and latency
- Cost and vendor lock-in

**Why project notes vs. labels/comments:**

- JSON blob needs more space than label names allow
- Comments are append-only, notes are editable
- Project notes provide clear ownership boundary

## Implementation Details

### Storage Format

```json
{
  "user_id": "U123456",
  "version": "1.0",
  "preferences": {
    "timezone": "America/New_York",
    "work_days": "mon,tue,wed,thu,fri",
    "morning_window_start": "08:00",
    "morning_window_end": "10:00",
    "wrap_window_start": "17:00",
    "wrap_window_end": "19:00",
    "quiet_hours_start": "19:00",
    "quiet_hours_end": "08:00",
    "energy_windows": [
      {
        "name": "deep",
        "start_time": "09:00",
        "end_time": "11:00",
        "max_session_minutes": 90
      }
    ],
    "checkin_time_today": "14:30"
  }
}
```

### Error Handling

- If FlowCoach project doesn't exist, create it automatically
- If preferences task doesn't exist, create it
- If JSON is invalid, fall back to defaults and log error
- Retry logic for Todoist API rate limits

### Migration Path

- No migration needed - new feature behind flag
- Users get defaults until they complete interview
- Interview saves preferences to Todoist on completion

## Consequences

**Positive:**

- Rapid implementation without database changes
- User data ownership and transparency
- Natural backup/sync via Todoist
- Easy rollback if issues arise

**Negative:**

- Dependency on Todoist API for preferences
- Potential confusion if users delete the task
- JSON blob is less queryable than database
- Size limits (though should be ample for preferences)

**Risks & Mitigations:**

- **Risk:** User deletes preferences task
  - **Mitigation:** Clear naming, high priority, recreate if missing
- **Risk:** Todoist API issues affect preferences
  - **Mitigation:** Cache preferences locally, graceful degradation
- **Risk:** JSON becomes large over time
  - **Mitigation:** Version field allows format evolution

## Alternatives Considered

1. **SQLite preferences table**

   - Pros: Queryable, fast, no external dependency
   - Cons: Schema changes, backup complexity, not BMAD-compliant

2. **Task labels for simple preferences**

   - Pros: Native Todoist metadata
   - Cons: Limited to simple key-value pairs, no complex objects

3. **Environment variables**
   - Pros: Simple for power users
   - Cons: No GUI, not per-user, not suitable for SaaS

## Review

This decision will be reviewed after Phase 1 (Morning Brief Modal) implementation based on:

- Todoist API reliability for preferences access
- User experience with interview and setup flow
- Performance characteristics under real usage
- Any user feedback about the FlowCoach project approach
