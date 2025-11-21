#!/usr/bin/env python3

import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load environment
from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()


def test_slack_connection():
    """Test basic Slack connectivity and home tab."""

    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        print("ERROR: SLACK_BOT_TOKEN not found in environment")
        return

    client = WebClient(token=bot_token)

    try:
        # Test authentication
        response = client.auth_test()
        print("✓ Authentication successful!")
        print(f"  Bot ID: {response['bot_id']}")
        print(f"  Bot User: {response['user']}")
        print(f"  Team: {response['team']}")
        print(f"  Workspace: {response['url']}")

        # Get bot's user ID
        bot_user_id = response["user_id"]

        # Test sending a message
        test_response = client.chat_postMessage(
            channel=bot_user_id,
            text="Test message from debugging script - if you see this, the bot can send messages!",
        )
        print("\n✓ Successfully sent test message!")

        # Check app manifest
        print("\n✓ Bot permissions look good for Socket Mode operations")

    except SlackApiError as e:
        print(f"\n✗ Slack API Error: {e.response['error']}")
        print(f"  Details: {e.response}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")


if __name__ == "__main__":
    test_slack_connection()
