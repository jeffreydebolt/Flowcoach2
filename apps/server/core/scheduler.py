"""Task scheduling and deep work prompting."""

import logging
import os
from typing import Any

from slack_sdk import WebClient

from ..core.errors import log_event
from ..core.scoring import TaskScorer
from ..db.dal import get_dal
from ..todoist.client import TodoistClient

logger = logging.getLogger(__name__)


class DeepWorkScheduler:
    """Handle deep work task identification and scoring prompts."""

    def __init__(self):
        self.slack_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack = WebClient(token=self.slack_token) if self.slack_token else None
        self.todoist = TodoistClient()
        self.dal = get_dal()

        # Ensure t_30plus label exists
        self.deep_work_label_id = None
        self._ensure_deep_work_label()

    def _ensure_deep_work_label(self) -> None:
        """Ensure t_30plus label exists in Todoist."""
        try:
            self.deep_work_label_id = self.todoist.ensure_label("t_30plus")
            logger.info(f"Deep work label ID: {self.deep_work_label_id}")
        except Exception as e:
            logger.error(f"Failed to ensure deep work label: {e}")

    def process_new_tasks(self, user_id: str | None = None) -> None:
        """
        Process new tasks to identify and score deep work.

        Args:
            user_id: Optional Slack user ID for prompting
        """
        try:
            # Get all tasks without scores
            tasks = self.todoist.get_tasks()
            if not tasks:
                return

            for task in tasks:
                task_id = task["id"]

                # Skip if already scored
                if self.dal.task_scores.get_score(task_id):
                    continue

                # Check if it's deep work
                duration = TaskScorer.extract_duration(task["content"])
                is_deep = TaskScorer.is_deep_work(task["content"], duration)

                if is_deep:
                    # Add deep work label
                    labels = task.get("labels", [])
                    if "t_30plus" not in labels:
                        labels.append("t_30plus")
                        self.todoist.update_task(task_id, labels=labels)
                        logger.info(f"Added deep work label to task {task_id}")

                    # Send scoring prompt if we have a user
                    if user_id and self.slack:
                        self._send_scoring_prompt(user_id, task)

        except Exception as e:
            logger.error(f"Error processing new tasks: {e}")
            log_event("error", "deep_work_processing_error", {"error": str(e)})

    def _send_scoring_prompt(self, user_id: str, task: dict[str, Any]) -> None:
        """Send scoring prompt for deep work task."""
        try:
            message = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🎯 *Deep work task detected:*\n_{task['content']}_",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Please score this task:\n`Impact/Urgency/Energy`\n\nExample: `4/3/am`",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "Impact: 1-5 (low to high)\nUrgency: 1-5 (low to high)\nEnergy: am or pm",
                            }
                        ],
                    },
                ]
            }

            # Store task ID in metadata for response handling
            message["metadata"] = {"event_type": "deep_work_score", "task_id": task["id"]}

            self.slack.chat_postMessage(channel=user_id, **message)

            log_event("info", "deep_work_prompt_sent", {"user_id": user_id, "task_id": task["id"]})

        except Exception as e:
            logger.error(f"Failed to send scoring prompt: {e}")

    def batch_process_unscored_tasks(self) -> dict[str, Any]:
        """
        Batch process all unscored deep work tasks.

        Returns:
            Summary of processing results
        """
        results = {"processed": 0, "labeled": 0, "already_scored": 0, "errors": 0}

        try:
            # Get all tasks with t_30plus label
            tasks = self.todoist.get_tasks(label="t_30plus")
            if not tasks:
                return results

            for task in tasks:
                results["processed"] += 1
                task_id = task["id"]

                # Check if already scored
                if self.dal.task_scores.get_score(task_id):
                    results["already_scored"] += 1
                    continue

                # For batch processing, assign default scores based on content analysis
                # In a real implementation, you might use AI to estimate these
                impact = 3  # Default medium impact
                urgency = 3  # Default medium urgency
                energy = "am"  # Default morning energy

                # Look for urgency indicators
                content_lower = task["content"].lower()
                if any(
                    word in content_lower for word in ["urgent", "asap", "critical", "deadline"]
                ):
                    urgency = 5
                elif any(word in content_lower for word in ["important", "priority"]):
                    urgency = 4

                # Look for impact indicators
                if any(word in content_lower for word in ["strategic", "key", "major", "critical"]):
                    impact = 5
                elif any(word in content_lower for word in ["improve", "enhance", "optimize"]):
                    impact = 4

                # Calculate total score
                total_score = TaskScorer.calculate_total_score(impact, urgency, energy)

                # Save score
                self.dal.task_scores.save_score(task_id, impact, urgency, energy, total_score)

                # Update task labels
                labels = TaskScorer.get_score_labels(impact, urgency, energy)
                existing_labels = task.get("labels", [])

                # Remove old score labels
                existing_labels = [
                    l
                    for l in existing_labels
                    if not (
                        l.startswith("impact") or l.startswith("urgency") or l.startswith("energy_")
                    )
                ]

                # Add new labels
                all_labels = existing_labels + labels
                self.todoist.update_task(task_id, labels=all_labels)

                results["labeled"] += 1

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            results["errors"] += 1

        return results
