# 📝 FlowCoach v2.1 Development Tasks

## 🔒 High Priority

### Ticket 1: Idempotent Todoist Push
- Add idempotency hash per task (sha1(userId+title+dueDate+parentId)).
- On re-accept or retry, skip duplicates.
- Add retry logic (3x exponential backoff) for Todoist 5xx or network errors.
- **Done when**: Re-accepting a session creates 0 new duplicates.

### Ticket 2: Prioritization Scoring v1
- Command: `what should I do now?`
- Compute fit based on current free window (calendar) + task duration bucket.
- Scoring: gap_fit (0/1), today_focus boost (+0.5), due_soon boost.
- Show top 3 tasks. Always confirm: "Start #1 now? yes/no/show more"
- **Done when**: With 20m gap, only 2m/10m tasks surface.

### Ticket 3: Date Assignment (Snooze)
- Commands:
  - `snooze <#|text> tomorrow` → set due: tomorrow 9:30a (default)
  - `do today <#|text>` → due: today
  - `undate <#|text>` → clear due
- Always confirm before commit.
- Idempotent (snoozing same task twice does nothing extra).
- **Done when**: User can snooze/reslot tasks with yes/no/pick time.

## ⚖️ Medium Priority

### Ticket 4: Daily Priorities (Focus List)
- Command: `priorities today` → capture 3 items (title or taskId).
- Store in DB table FocusToday.
- Tag with @today_focus if Todoist label mode is on (ask first).
- Midday check-in (once/day, 11a–2p): "1 done, 2 left. Reslot?"
- PM close: "✅ 5 done, ⏭ 2 moved. Push unfinished to tomorrow?"
- **Done when**: A user can set, view, and carry forward daily top 3.

### Ticket 5: Calendar Suggest
- Command: `suggest` → look at next free window today.
- Return tasks that fit (2m/10m if gap<30m, 30m+ if gap≥35m).
- Always ask: "Want me to hold that slot? yes/no"
- **Done when**: Suggest surfaces 2–3 tasks that match next available window.

### Ticket 6: Project Breakdown (Manual)
- Command: `breakdown <#|task>`
- Claude generates 3–6 subtasks with buckets.
- Preview → accept → parent+subtasks created in Todoist.
- Idempotent: same breakdown+accept = no duplicates.
- **Done when**: A project-sized task can be reliably decomposed via command.

### Ticket 7: Regression Test Suite
- Encode transcript scenarios as automated tests:
  - Calendar queries ("do I have time for 30m task?")
  - Task correction ("actually make that 10 mins")
  - Typo handling ("careate task…")
  - Status listing real Todoist tasks
- **Done when**: Suite passes on every commit.

## 🌱 Future (Icebox for Later)
- Chaos Parser v2 (multi-paragraph inputs)
- Energy-based prioritization (low/med/high)
- Deadline awareness
- Batch operations
- Calendar blocking (block 90m tomorrow for X)
- Weekly project reviews
- Email-to-task capture / draft replies