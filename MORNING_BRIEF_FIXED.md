# Morning Brief Fixes Applied ✅

## What I Fixed While You Were Sleeping:

### 1. ✅ Removed Planning Comments

**Before**: Added "flow:planned_due priority=p3 time=11:00" comments to every task
**After**: Only adds @flow_top_today label, no more comment spam

### 2. ✅ Increased Task Limit

**Before**: Limited to 10 tasks max
**After**: Shows up to 20 tasks

### 3. ✅ Added P1 Focus Mode

**Before**: Mixed priorities (P1, P2, P3, overdue) all jumbled together
**After**: P1 focus mode ensures ALL P1 tasks are shown first, then fills remaining slots

### 4. ✅ Better Debug Logging

**Before**: Couldn't tell why P1 tasks were missing
**After**: Logs all P1 tasks found in Todoist to help debug

## How It Works Now:

1. **Fetches all tasks** from Todoist
2. **Identifies ALL P1 tasks** (logs count for debugging)
3. **P1 Focus Mode**:
   - Shows ALL P1 tasks first
   - Fills remaining slots (up to 20 total) with other important tasks
4. **No more comment spam** - just adds @flow_top_today label

## Next Steps:

### To Test:

1. Restart the bot: `pkill -f "Python app.py" && python3 app.py`
2. Open Morning Brief
3. Check logs for "MBDebug: Found X total P1 tasks"
4. Verify all P1 tasks appear in the modal

### Future Improvements:

1. **Task grouping by project** - organize tasks better
2. **Configurable selection** - let user choose what tasks to see
3. **Better planning storage** - use metadata instead of comments
4. **Time estimate display** - show [10min] tags in modal

## The Result:

- ✅ No more comment clutter on your tasks
- ✅ All P1 tasks should now appear
- ✅ Better organization with P1s first
- ✅ Can handle up to 20 tasks in the modal

Ready for testing when you wake up! 🌅
