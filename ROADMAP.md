# 📌 FlowCoach v2.1 Roadmap (Updated)

## ✅ Where We Are

- Stable deterministic time parser (clean, no duplicates)
- Preview mode with accept/edit/discard flow
- Conversation memory + thread state (SQLite)
- High typo tolerance + smart clarification
- Natural GTD knowledge responses
- Calendar awareness (basic free/busy + time check)
- Status command showing real Todoist tasks
- Solid user experience: "chaos → clarity" loop working

## 🚧 High Priority (Next 2–4 Weeks)

### Idempotent Todoist Push
- Retry logic for failed API calls
- Prevent duplicates on re-accept or network hiccups

### Prioritization Scoring v1
- "What should I do now?" → ranks tasks that fit the current gap
- Read-only, consent-first suggestions

### Date Assignment (Snooze)
- Commands: `snooze <task> tomorrow`, `do today <task>`, `undate <task>`
- Always confirm before committing

## ⚖️ Medium Priority (1–2 Months)

### Daily Priorities
- AM: Ask for top 3 outcomes for today
- Tag tasks or keep in a "focus" note
- Midday check-in (optional, once/day): "1 done, 2 left. Want to reslot?"
- PM close: Carry unfinished forward with confirmation

### Calendar Suggest
- Command `suggest` → "Next free window is 1–1:30, want me to line up Quick Wins?"
- Always confirm, never auto-schedule

### Project Breakdown
- Triggered by `breakdown <task>`
- Generates subtasks → preview → accept

### Regression Test Suite
- Lock current behaviors (calendar queries, "actually make that 10 mins", typo handling, status)
- Prevent future regressions

## 🌱 Future Roadmap (Longer Term)

- **Advanced Chaos Parser v2**: handle more complex inputs (multi-paragraph dumps, mixed contexts)
- **Energy-Based Prioritization**: match tasks to "low/med/high" energy states
- **Deadline Awareness**: surface tasks due soon
- **Batch Operations**: bulk reschedule/edit
- **Calendar Blocking**: "Block 90m for budget review tomorrow" → create calendar event (consent-first)
- **Project Reviews**: weekly summary of stalled vs moving projects
- **Email Light Touch**: "Turn this email into a task" or draft short reply

## 🏆 Strategic Themes

- **Consent-first**: Always ask before changing Todoist or calendar
- **Clarity over control**: Focus on daily priorities, summaries, and nudges
- **Complement, don't duplicate**: Todoist stays execution, FlowCoach becomes the clarity/assistant layer