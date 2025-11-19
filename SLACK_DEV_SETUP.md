# Development Slack App Setup Guide

## Problem

You cannot run FlowCoach locally for development because Slack only allows **one active Socket Mode connection per app token**. Your production instance is already using the main app token.

## Solution

Create a **separate Slack app** specifically for development that connects to the same workspace.

## Step-by-Step Instructions

### 1. Create Development Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Choose **"From an app manifest"**
4. Select your workspace: **Bread** (T08782ZB401)
5. Copy and paste the manifest below:

```yaml
display_information:
  name: FlowCoach Dev
  description: FlowCoach Development Bot
  background_color: '#2c3e50'
features:
  app_home:
    home_tab_enabled: true
    messages_tab_enabled: true
    messages_tab_read_only_enabled: false
  bot_user:
    display_name: FlowCoach Dev
    always_online: true
  slash_commands:
    - command: /flowcoach-dev
      description: FlowCoach development commands
      usage_hint: '[command]'
oauth_config:
  scopes:
    bot:
      - app_mentions:read
      - assistant:write
      - channels:history
      - channels:write.topic
      - chat:write
      - commands
      - groups:write
      - im:history
      - im:read
      - im:write
      - links:write
      - mpim:history
      - users:read
settings:
  event_subscriptions:
    bot_events:
      - app_home_opened
      - app_mention
      - message.channels
      - message.groups
      - message.im
      - message.mpim
  interactivity:
    is_enabled: true
  org_deploy_enabled: false
  socket_mode_enabled: true
  token_rotation_enabled: false
```

6. Click **"Create"** and **"Create"** again

### 2. Configure App Permissions and Tokens

1. Go to **"OAuth & Permissions"**
   - **Bot Token**: Should start with `xoxb-` (copy this)
2. Go to **"Socket Mode"**
   - Enable Socket Mode if not already enabled
   - **App-Level Token**: Should start with `xapp-` (copy this)
3. Go to **"Basic Information"**
   - **Signing Secret**: Copy this value

### 3. Install Development App

1. Go to **"Install App"**
2. Click **"Install to Workspace"**
3. Authorize the app (it will install alongside your production FlowCoach)

### 4. Update Development Configuration

1. Edit `.env.dev` file and replace the placeholder tokens:

```bash
# Replace these with your new development app tokens:
SLACK_BOT_TOKEN=xoxb-YOUR-NEW-DEV-BOT-TOKEN
SLACK_APP_TOKEN=xapp-YOUR-NEW-DEV-APP-TOKEN
SLACK_SIGNING_SECRET=your-new-dev-signing-secret
```

### 5. Test Development Environment

Run the development environment:

```bash
# Load development environment
export FLOWCOACH_ENV=development
python3 app.py
```

## Environment Switching

### Development Mode

```bash
export FLOWCOACH_ENV=development
python3 app.py
```

### Production Mode

```bash
export FLOWCOACH_ENV=production
python3 app.py
```

## Verification

After setup, you should see:

- **Two bots in your Slack workspace**: "FlowCoach" (production) and "FlowCoach Dev"
- **No Socket Mode conflicts**: Development bot connects without cycling
- **Separate databases**: `flowcoach.db` (prod) and `flowcoach_dev.db` (dev)

## Troubleshooting

### Bot appears offline

- Check that Socket Mode is enabled in app settings
- Verify app is installed to workspace
- Confirm tokens are correct in `.env.dev`

### Still getting connection cycling

- Ensure you're using the NEW development app tokens
- Check that `FLOWCOACH_ENV=development` is set
- Verify no other development instances are running

### Bot not responding to messages

- Check bot permissions include `chat:write` and `im:write`
- Verify app is installed to workspace
- Test with direct message to "FlowCoach Dev" bot

## Next Steps

Once development app is working:

1. Test GTD formatting: Send message "gtd do cash flow for best self"
2. Test Socket Mode stability: Should maintain connection without cycling
3. Develop features safely without affecting production users
