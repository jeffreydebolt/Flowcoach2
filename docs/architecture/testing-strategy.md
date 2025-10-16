# Testing Strategy

## Testing Pyramid
```
Frontend Unit   Backend Unit
      ^              ^
      |        Integration (Slack command flows, CLI accept flow)
      |                ^
      +-------- E2E (CLI organize ➜ Todoist mock, Slack smoke tests)
```

## Test Organization
- Python: `tests/` directory with pytest.  
- TypeScript: `test-parser.ts`, `test-calendar.ts`; expand with vitest/jest suites.  
- E2E: mock Slack events + local CLI acceptance using fixture Todoist responses.

## Test Examples

Frontend Tests (CLI formatting)  
```typescript
import { formatPreview } from '../src/core/formatting';
// Assert durations and emojis render correctly for quick wins and projects.
```

Backend Tests (Python handler)  
```python
def test_handle_organize_message(mock_slack_client, todoist_stub):
    # Validate session creation and Todoist enqueue logic.
```

E2E Test (CLI organize flow)  
```typescript
it('organizes tasks and persists session', async () => {
  const response = await flowcoach.organize('email Sam - 10 min', 'test_user');
  expect(response.type).toBe('preview');
  const session = await sessionService.getLastPendingSession('test_user');
  expect(session).not.toBeNull();
});
```
