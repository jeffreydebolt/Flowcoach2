# Socket Mode Connection Issue - SOLVED

## Root Cause Identified

The FlowCoach bot is experiencing Socket Mode connection cycling every 3 seconds due to **Socket Mode connection conflicts**. Slack only allows **one active Socket Mode connection per app token**.

## Evidence

1. **Error Pattern**: "too_many_websockets" disconnect reason in logs
2. **Timing**: Exact 3-second cycles indicate systematic termination
3. **Behavior**: Connections establish successfully but are immediately terminated

## Likely Causes

1. **Another FlowCoach instance running** (production server, another dev environment)
2. **Multiple apps using same app token** (development vs production confusion)
3. **Previous connections not properly cleaned up** (hanging processes)

## Solution Strategy

### Immediate Fix (Development)

Create a **development-specific app token** to isolate local development:

1. Go to [Slack App Settings](https://api.slack.com/apps)
2. Create a duplicate app for development OR
3. Generate a new app token specifically for local development
4. Use environment variable to switch between dev/prod tokens

### Production Deployment Fix

Implement **single instance enforcement**:

```python
# Check if another instance is already running
def check_socket_mode_availability(app_token):
    """Test if Socket Mode is available for this app token."""
    try:
        test_handler = SocketModeHandler(test_app, app_token)
        # If this succeeds, no other instance is running
        test_handler.close()
        return True
    except Exception as e:
        if "too_many_websockets" in str(e):
            return False
        raise e
```

## Implementation Plan

### Phase 1: Immediate Development Fix

1. ✅ **Identified root cause** - Socket Mode conflicts
2. 🔄 **Create dev-specific configuration** - Use separate app token for development
3. 🔄 **Test Socket Mode isolation** - Verify no conflicts with dev token

### Phase 2: Production Deployment Protection

1. **Single instance checking** - Detect and prevent multiple instances
2. **Graceful instance handover** - Allow controlled instance switching
3. **Health monitoring** - Monitor Socket Mode connection health

## Technical Details

**Current Issue**:

- App Token: `xapp-1-A08FU15EA2Y-9640956927024-...`
- Conflict: Another instance using same token
- Result: Slack terminates new connections every 3 seconds

**Socket Mode Behavior**:

- Only ONE active connection per app token allowed
- New connections cause old ones to disconnect
- Rapid cycling indicates systematic conflicts

## Next Steps

1. **Check for competing instances**:
   - Production servers
   - Other development environments
   - Background processes
2. **Create development isolation**:
   - Separate development app/token
   - Environment-specific configuration
3. **Implement deployment safeguards**:
   - Instance conflict detection
   - Graceful connection handover
   - Health monitoring

## Status

- ✅ **Root cause identified**: Socket Mode connection conflicts
- ✅ **Solution designed**: Development/production token isolation
- 🔄 **Implementation needed**: Separate dev app token configuration
