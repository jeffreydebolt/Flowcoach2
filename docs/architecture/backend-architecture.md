# Backend Architecture

## Services Overview
- `app.py`: initializes Slack Bolt app, registers handlers, starts Socket Mode.  
- `services/` (Python): wrappers for OpenAI, Todoist, calendar (planned), workflow persistence.  
- `core/` and `framework/`: BMAD-inspired agent infrastructure to coordinate workflows.  
- `src/core/flowcoach.ts`: orchestrates parsing, session creation, Todoist operations for CLI.  
- TypeScript services provide Claude integration, session persistence, Todoist API client, thread state.

## Application Layer
- Python handlers map Slack events to BMAD agents, ensuring consistent workflows across surfaces.  
- CLI orchestrator enforces preview → accept pipeline with idempotency.

## Domain Layer
- Domain logic (task parsing, GTD tagging) resides in TypeScript `FlowCoach` class and Python `core/task_agent`.  
- Agents pattern enables plugging new flows without modifying handler core.

## Infrastructure Layer
- Services encapsulate external APIs with logging and error handling (`OpenAIService`, `TodoistService`, `ClaudeService`).  
- SQLite persistence via `SessionService`/`WorkflowPersistenceService`.
