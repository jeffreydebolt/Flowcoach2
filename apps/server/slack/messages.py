"""Slack message builders."""

import json
import random
from typing import List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MessageBuilder:
    """Build formatted Slack messages."""

    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / 'templates'
        self.phrases = self._load_phrases()
        self.morning_template = self._load_template('morning_brief.json')
        self.evening_template = self._load_template('evening_wrap.json')

    def _load_phrases(self) -> Dict[str, Any]:
        """Load phrase variations."""
        phrases_path = self.templates_dir / 'phrases.json'
        with open(phrases_path, 'r') as f:
            return json.load(f)

    def _load_template(self, filename: str) -> Dict[str, Any]:
        """Load message template."""
        template_path = self.templates_dir / filename
        with open(template_path, 'r') as f:
            return json.load(f)

    def build_morning_brief(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build morning brief message.

        Args:
            tasks: List of prioritized tasks (up to 3)

        Returns:
            Slack blocks payload
        """
        # Get random phrases
        intro = random.choice(self.phrases['morning_brief']['intros'])
        outro = random.choice(self.phrases['morning_brief']['outros'])

        # Format tasks
        task_texts = []
        for i, task in enumerate(tasks[:3]):
            task_text = task['content']

            # Add time estimate if available
            labels = task.get('labels', [])
            time_labels = [l for l in labels if l.startswith('t_')]
            if time_labels:
                time_str = time_labels[0].replace('t_', '').replace('plus', '+')
                task_text += f" _{time_str}_"

            # Add due date if today or overdue
            due = task.get('due')
            if due and due.get('date'):
                task_text += " 🔴"

            task_texts.append(task_text)

        # Pad with empty tasks if less than 3
        while len(task_texts) < 3:
            task_texts.append("_No more tasks for now_")

        # Build message from template
        template_str = json.dumps(self.morning_template)

        # Replace placeholders
        replacements = {
            '{intro}': intro,
            '{item1}': task_texts[0],
            '{item2}': task_texts[1],
            '{item3}': task_texts[2],
            '{close}': outro
        }

        for placeholder, value in replacements.items():
            template_str = template_str.replace(placeholder, value)

        message = json.loads(template_str)

        # Store task IDs in block IDs for action handling
        for i, task in enumerate(tasks[:3]):
            if i < len(message['blocks']):
                block_idx = 2 + i * 1  # Skip intro and divider
                if block_idx < len(message['blocks']):
                    message['blocks'][block_idx]['block_id'] = f"task_block_{task['id']}"

        return message

    def build_evening_wrap(
        self,
        surfaced_tasks: List[Dict[str, Any]],
        completed_ids: List[str]
    ) -> Dict[str, Any]:
        """Build evening wrap-up message."""
        intro = random.choice(self.phrases['evening_wrap']['intros'])
        outro = random.choice(self.phrases['evening_wrap']['outros'])

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": intro}
            },
            {"type": "divider"}
        ]

        # Categorize tasks
        completed = []
        still_open = []

        for task in surfaced_tasks:
            if task['task_id'] in completed_ids:
                completed.append(f"✅ ~{task['task_content']}~")
            else:
                still_open.append(task)

        # Add completed section
        if completed:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Completed today:*\n" + "\n".join(completed)
                }
            })

        # Add open tasks with actions
        if still_open:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Still open:*"
                }
            })

            for task in still_open:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔁 {task['task_content']}"
                    },
                    "block_id": f"wrap_task_{task['task_id']}",
                    "accessory": {
                        "type": "overflow",
                        "action_id": f"wrap_actions_{task['task_id']}",
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "📅 Move to Tomorrow"},
                                "value": f"tomorrow_{task['task_id']}"
                            },
                            {
                                "text": {"type": "plain_text", "text": "⏸️ Pause Project"},
                                "value": f"pause_{task['task_id']}"
                            },
                            {
                                "text": {"type": "plain_text", "text": "📦 Archive"},
                                "value": f"archive_{task['task_id']}"
                            }
                        ]
                    }
                })

        blocks.extend([
            {"type": "divider"},
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": outro}]
            }
        ])

        return {"blocks": blocks}

    def build_weekly_outcomes_prompt(self) -> Dict[str, Any]:
        """Build weekly outcomes prompt message."""
        prompt = random.choice(self.phrases['weekly_outcomes']['prompts'])

        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Monday Planning* 📋\n\n{prompt}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "_Reply with 3 bullet points or numbered items_"
                        }
                    ]
                }
            ]
        }

    def build_fallback_message(self, error_type: str = "general") -> Dict[str, Any]:
        """Build fallback message for errors."""
        messages = {
            "todoist": "I'm having trouble reaching Todoist right now. Please try again in a few minutes.",
            "no_tasks": "No tasks found for your morning brief. Time to add some tasks to Todoist!",
            "general": "Something went wrong. I've logged the issue and will try again next time."
        }

        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": messages.get(error_type, messages["general"])
                    }
                }
            ]
        }
