# Environment Bootstrap Guide

FlowCoach provides flexible environment variable loading to ensure tokens and configuration are available in both development and production environments.

## Two Approaches

### Option 1: Wrapper Script (Recommended for Development)

The `./dev.sh` wrapper script automatically loads `.env` files before running commands:

```bash
# Run health server with environment loaded
./dev.sh python -m apps.server.health

# Run Slack bot with environment loaded
./dev.sh python app.py

# Run database migrations with environment loaded
./dev.sh python scripts/migrate.py

# Run any Python command with environment loaded
./dev.sh python -c "import os; print('Token loaded:', bool(os.getenv('SLACK_BOT_TOKEN')))"
```

**How it works:**

- Loads `.env` if present (ignores comments and blank lines)
- Exports all variables to environment
- Executes the provided command with full environment

### Option 2: Automatic Loading via python-dotenv

FlowCoach can automatically load `.env` files when modules are imported:

```bash
# Install python-dotenv (optional)
pip install python-dotenv

# Set local development mode (default)
export FC_ENV=local

# Or force auto-loading in any environment
export FC_AUTO_LOAD_ENV=1

# Now run commands directly - .env will auto-load
python -m apps.server.health
python app.py
python scripts/migrate.py
```

**How it works:**

- Enabled by default when `FC_ENV=local` (default)
- Can be forced with `FC_AUTO_LOAD_ENV=1`
- Automatically finds `.env` in repository root
- Preserves existing environment variables (override=False)

## Health Status Meanings

The health endpoint at `/health` reports service status:

### Service States

- `"ok"`: Token/credential is properly configured
- `"not_configured"`: Token/credential is missing or empty

### Overall Status Logic

- `"ok"`: Database healthy + all services (slack, todoist, claude) configured
- `"degraded"`: Database healthy + any service not configured, OR 3-10 critical errors in 24h
- `"error"`: Database unhealthy OR >10 critical errors in 24h

### Example Responses

**All Green (with .env loaded):**

```json
{
  "status": "ok",
  "database_status": "ok",
  "services_status": {
    "database": "ok",
    "slack": "ok",
    "todoist": "ok",
    "claude": "ok"
  }
}
```

**Degraded (without .env):**

```json
{
  "status": "degraded",
  "database_status": "ok",
  "services_status": {
    "database": "ok",
    "slack": "not_configured",
    "todoist": "not_configured",
    "claude": "not_configured"
  }
}
```

## Environment Variables

Required tokens for full "ok" status:

- `SLACK_BOT_TOKEN` - Slack bot token for daily briefs and interactions
- `TODOIST_API_TOKEN` - Todoist API token for task management
- `CLAUDE_API_KEY` - Claude API key for AI-powered task parsing

Environment control:

- `FC_ENV` - Set to `local` (default) or `production`
- `FC_AUTO_LOAD_ENV` - Set to `1` to force auto-loading in any environment
- `FC_DB_DRIVER` - Database driver: `sqlite` (default), `postgres`, `supabase`

## Examples

### Development Workflow with Wrapper

```bash
# Start health server
./dev.sh python -m apps.server.health
curl http://localhost:8080/health  # Should show all services "ok"

# Run migrations
./dev.sh python scripts/migrate.py

# Start Slack bot
./dev.sh python app.py
```

### Development Workflow with Auto-loading

```bash
# Install optional dependency
pip install python-dotenv

# Verify auto-loading works
python -c "import apps.server.health; print('Auto-loading enabled')"

# Run commands directly
python -m apps.server.health
python app.py
```

### Production Deployment

```bash
# Disable auto-loading in production
export FC_ENV=production

# Set tokens via environment (not .env file)
export SLACK_BOT_TOKEN=xoxb-production-token
export TODOIST_API_TOKEN=production-token
export CLAUDE_API_KEY=production-key

# Run services
python -m apps.server.health
python app.py
```

## Guardrails

- **Token values are never logged** - Only presence/absence is reported
- **Local-only by default** - Auto-loading only works when `FC_ENV=local` or `FC_AUTO_LOAD_ENV=1`
- **No .env modification** - Bootstrap only reads, never writes configuration
- **Graceful fallback** - Missing python-dotenv or .env files don't cause errors
- **Override protection** - Existing environment variables take precedence over .env values

## Troubleshooting

**Health endpoint shows "degraded" despite .env existing:**

- Verify `.env` is in repository root
- Check tokens aren't empty or whitespace-only
- Try wrapper script: `./dev.sh python -m apps.server.health`

**Auto-loading not working:**

- Install python-dotenv: `pip install python-dotenv`
- Verify `FC_ENV=local` or set `FC_AUTO_LOAD_ENV=1`
- Check `.env` exists in repository root

**Services still "not_configured":**

- Verify exact variable names: `SLACK_BOT_TOKEN`, `TODOIST_API_TOKEN`, `CLAUDE_API_KEY`
- Check for trailing whitespace in token values
- Use wrapper script to ensure loading: `./dev.sh python -m apps.server.health`
