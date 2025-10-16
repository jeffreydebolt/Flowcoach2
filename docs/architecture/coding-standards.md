# Coding Standards

## Critical Fullstack Rules
- **Deterministic Time Parsing First:** Always run structured parser before LLM calls to keep duration buckets reliable.
- **Idempotent Todoist Writes:** Derive `title_hash` consistently; never create Todoist tasks without duplicate check.
- **Centralized Config Access:** Use `config.get_config()` (Python) or environment accessors (TS) rather than `process.env` scattering.
- **Workflow State TTL:** Ensure workflow states set `expires_at`; cleanup jobs must run daily.

## Naming Conventions
| Element             | Frontend (CLI/Slack) | Backend (Python/TS) | Example              |
|---------------------|----------------------|---------------------|----------------------|
| Components          | PascalCase           | -                   | `TaskPreview.tsx`    |
| Hooks/Helpers       | camelCase with `use` | -                   | `useTodoistClient.ts`|
| API Routes          | -                    | kebab-case          | `/api/user-profile`  |
| Database Tables     | -                    | snake_case          | `created_tasks`      |
