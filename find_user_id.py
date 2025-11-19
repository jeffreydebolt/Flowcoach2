#!/usr/bin/env python3

import os
from apps.server.core.env_bootstrap import bootstrap_env

bootstrap_env()

from slack_sdk import WebClient

client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# Get users list
response = client.users_list()
for user in response["members"]:
    if not user.get("is_bot") and not user.get("deleted"):
        print(
            f"User: {user['name']} - ID: {user['id']} - Real name: {user.get('real_name', 'N/A')}"
        )
