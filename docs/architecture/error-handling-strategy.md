# Error Handling Strategy

## Error Flow
```mermaid
sequenceDiagram
    participant Client as Slack/CLI
    participant Runtime as Python/Node Runtime
    participant Logger as Logging Layer
    participant Notifier as Alerting (PagerDuty/SNS)

    Client->>Runtime: Request
    Runtime->>Runtime: Try/Except or Promise.catch
    alt Recoverable
        Runtime->>Client: User-friendly error message
        Runtime->>Logger: warn level log with context
    else Critical
        Runtime->>Notifier: Send alert
        Runtime->>Client: Generic failure response
        Runtime->>Logger: error level log + stack trace
    end
```

## Error Response Format
```typescript
interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    timestamp: string;
    requestId: string;
  };
}
```

## Frontend Error Handling
```typescript
export function handleCliError(err: unknown) {
  const requestId = crypto.randomUUID();
  console.error(`[${requestId}]`, err);
  return `❌ Sorry, something went wrong (ref: ${requestId}). Try again or contact support.`;
}
```

## Backend Error Handling
```python
def safe_todoist_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except TodoistError as err:
        logger.warning("Todoist API failure", extra={"error": str(err)})
        raise FlowCoachServiceError("todoist_error", str(err)) from err
```
