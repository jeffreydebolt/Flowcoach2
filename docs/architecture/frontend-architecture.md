# Frontend Architecture

## Client Overview
- **Slack UI:** Interactive message responses, buttons, and dialogues handled via Slack Bolt actions. No custom web UI.  
- **CLI:** Node-based CLI for power users/testing; outputs Markdown/text in terminal.  
- **Future UI Considerations:** Potential Next.js dashboard for reporting.

## Frontend Components
| Component               | Description | Stack |
|-------------------------|-------------|-------|
| Slack Message Renderer  | Formats replies (core/templates) | Python Jinja-lite patterns |
| CLI Output Formatter    | Converts parsed tasks to human-readable preview | TypeScript string formatting |

## State Management & Data Fetching
- Slack frontend relies on backend state; no client storage.  
- CLI fetches from local SQLite via services; ephemeral per run.  
- Introduce GraphQL/REST once dashboard exists.

## Routing & Navigation
- Slack: Command keywords (`organize`, `accept`, `breakdown`) and interactive buttons drive flows.  
- CLI: Command-line arguments route to methods inside `FlowCoach`.

## Accessibility & UX
- Slack messages follow GTD tagging `[2min]` style; ensure alt text for attachments.  
- CLI uses concise text, highlight states with Unicode icons (✅, ⚠️).  
- Document keyboard-focused improvements for future web UI.
