# Scaling & Reliability

## Scaling Strategy
- Horizontal scaling via ECS task count; Python and Node runtimes scale independently.  
- Use CloudWatch metrics (CPU, memory, request latency) to trigger autoscaling policies.  
- For Slack, ensure single Socket Mode connection per workspace; scale via sharding across workspaces if needed.

## Performance Considerations
- Offload heavy parsing to Claude only when deterministic parser insufficient.  
- Cache Todoist projects/labels in memory to reduce API calls.  
- SQLite replaced with Postgres to avoid locking under concurrency.

## Reliability Patterns
- Idempotent task creation (hash-based).  
- Graceful shutdown via signal handlers in Python.  
- Dead-letter queue planned for failed background jobs.  
- Health checks hitting `/healthz` endpoints (add to runtimes).
