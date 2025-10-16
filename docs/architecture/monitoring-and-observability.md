# Monitoring and Observability

## Monitoring Stack
- **Frontend Monitoring:** Slack interaction metrics via custom CloudWatch dashboards; CLI usage tracked via structured logs.
- **Backend Monitoring:** CloudWatch metrics (CPU, memory, invocation counts), ECS Container Insights.
- **Error Tracking:** Sentry (recommended) for Python & Node runtimes with shared project.
- **Performance Monitoring:** AWS X-Ray for tracing Todoist/OpenAI latency; Loki/Grafana optional for log exploration.

## Key Metrics
**Frontend Metrics:**
- Core Web Vitals: N/A (no web front). Track Slack command latency instead.
- JavaScript errors: CLI stderr incidents.
- API response times: CLI command duration histogram.
- User interactions: Slack command counts, CLI invocations per user.

**Backend Metrics:**
- Request rate: Slack events processed/min.
- Error rate: Todoist/OpenAI failure ratio.
- Response time: Slack handler execution time, CLI organize duration.
- Database query performance: Session insert latency, pending session queries.
