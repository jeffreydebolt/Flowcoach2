# Integration Architecture

## External Integrations
| Integration | Purpose | Protocol | Auth | Rate Limits / Considerations |
|-------------|---------|----------|------|------------------------------|
| Slack (Bolt + Web API) | Receive messages/actions, send responses | WebSockets (Socket Mode) + HTTPS | OAuth tokens (`SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`) | Socket Mode requires stable outbound connection; respect events-per-second quotas |
| Todoist API | Create/update tasks | HTTPS REST | Personal API token | Use idempotent hashes to avoid duplicates; apply exponential backoff |
| OpenAI Chat Completions | Format GTD tasks | HTTPS REST | API key | Temperature kept low (0.7); guardrails for failures |
| Anthropic Claude | Advanced parsing & breakdown | HTTPS REST | API key | Batch requests sequentially; log prompt/response metadata for debugging |
| Calendar Providers (planned) | Focus block scheduling | HTTPS REST | OAuth tokens stored per user | Pipeline not yet active; design for token refresh storage |

## Async & Background Workloads
Current system executes synchronously within request lifecycle. Planned enhancements:
- **EventBridge scheduled Lambda** to retry failed Todoist pushes.
- **SQS queue** for heavy breakdown requests to avoid Slack timeout (future).

## API Gateway & Routing
- Slack events handled via Socket Mode; no inbound HTTP required.
- CLI commands execute locally; future remote CLI/API should expose Express/FastAPI with authenticated endpoints.
