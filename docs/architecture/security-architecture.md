# Security Architecture

## Identity & Access
- Slack tokens stored encrypted; minimal scopes (commands, chat:write, app_mentions).  
- Todoist API tokens per environment; rotate quarterly.  
- CLI usage requires local `.env`; consider session-based auth if shipping remote CLI.

## Secrets Management
- Local: `.env`, never committed.  
- Cloud: AWS Secrets Manager with IAM roles limiting access to respective ECS tasks.  
- Rotate keys automatically via AWS rotation or manual runbooks.

## Data Protection
- Enforce TLS 1.2+ for outbound API calls (default).  
- Database encryption at rest (Aurora).  
- Logging scrubs task text when flagged as sensitive (future improvement).

## Threat Modeling & Mitigation
- **Risk:** Slack Socket Mode disconnect ➜ Mitigation: health checks, auto-reconnect, CloudWatch alarm.  
- **Risk:** Todoist API rate limiting ➜ Mitigation: exponential backoff, queued retries.  
- **Risk:** Prompt injection ➜ Mitigation: sanitize untrusted text, limit LLM instructions, run content filters.  
- **Risk:** API key leakage ➜ Mitigation: strict IAM, secret rotation, environment variable scanning in CI.
