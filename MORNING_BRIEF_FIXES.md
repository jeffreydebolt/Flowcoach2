# Morning Brief Fixes

## Issues to Fix:

### 1. Task Selection Logic

**Problem**: Morning Brief shows mixed priorities, not just P1 tasks
**Current**: Shows P1 OR @flow_tomorrow OR overdue OR @flow_weekly tasks
**Fix**: Add option to show ONLY P1 tasks or configure task selection

### 2. Planning Comments

**Problem**: Adding "flow:planned_due priority=p2 time=15:00" comments to tasks
**Fix**: Remove comment creation or use labels/metadata instead

### 3. Missing P1 Tasks

**Problem**: Not all P1 tasks shown (only 4 of 5+)
**Fix**: Increase limit and improve P1 detection

## Implementation:

### Fix 1: Improve Task Selection

```python
# In planning.py - Add P1-only mode
def get_morning_brief_tasks(self, user_id: str, p1_only: bool = False) -> List[TaskCandidate]:
    """Get tasks for morning brief modal.

    Args:
        user_id: Slack user ID
        p1_only: If True, only return P1 tasks
    """
    if p1_only:
        # Only get P1 tasks
        tasks = self.todoist.get_tasks()
        p1_tasks = [t for t in tasks if t.get("priority") == 4]
        # Process and return P1 tasks
```

### Fix 2: Remove Planning Comments

```python
# In mark_task_as_planned - Remove lines 242-250
# Don't add comments, just add label
def mark_task_as_planned(self, task_id: str, priority_level: str, planned_time: str) -> bool:
    # Add @flow_top_today label
    success = self.todoist.add_task_label(task_id, "@flow_top_today")

    # Store planning data in task metadata instead of comments
    # Or use a different label like @planned_11am

    return success
```

### Fix 3: Show All P1 Tasks

```python
# In planning.py line 83
# Increase limit for P1 tasks
if p1_only:
    limited_candidates = candidates  # No limit for P1 only mode
else:
    limited_candidates = candidates[:10]
```

## Quick Fixes for Tomorrow:

1. **Disable comments temporarily**:
   - Comment out lines 242-250 in mark_task_as_planned
2. **Show more tasks**:
   - Change line 83 from `candidates[:10]` to `candidates[:20]`
3. **P1-only mode**:
   - Add filter to only show P1 tasks in morning brief

## Long-term Improvements:

1. **Configurable task selection**:
   - Let user choose what tasks appear in Morning Brief
   - Save preferences for task filtering
2. **Better planning storage**:
   - Use task metadata API instead of comments
   - Or create planning-specific labels like @planned_9am
3. **Smart task grouping**:
   - Group by project
   - Show time estimates
   - Better priority handling
