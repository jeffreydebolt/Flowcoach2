"""Scheduled job for weekly project audit."""

import os
import logging
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..slack.commands_audit import AuditCommandHandler
from ..core.errors import log_event

logger = logging.getLogger(__name__)


class ProjectAuditJob:
    """Scheduled job to send weekly project audit."""

    def __init__(self):
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        if not self.slack_token:
            raise ValueError("SLACK_BOT_TOKEN not found in environment")

        self.slack = WebClient(token=self.slack_token)
        self.audit_handler = AuditCommandHandler()

        # Get active users
        self.active_users = os.getenv('FC_ACTIVE_USERS', '').split(',')
        self.active_users = [user.strip() for user in self.active_users if user.strip()]

    def run(self) -> bool:
        """
        Run weekly audit job.

        Returns:
            True if job completed successfully
        """
        try:
            logger.info("Starting weekly project audit job")

            if not self.active_users:
                logger.warning("No active users configured for audit job")
                return True

            success_count = 0

            for user_id in self.active_users:
                try:
                    self._send_audit_to_user(user_id)
                    success_count += 1

                except Exception as user_error:
                    logger.error(f"Failed to send audit to user {user_id}: {user_error}")

                    log_event(
                        severity="error",
                        action="audit_job_user_failed",
                        payload={
                            "user_id": user_id,
                            "error": str(user_error)
                        },
                        user_id=user_id
                    )

            # Log job completion
            log_event(
                severity="info",
                action="audit_job_completed",
                payload={
                    "users_processed": len(self.active_users),
                    "successful_audits": success_count,
                    "timestamp": datetime.now().isoformat()
                }
            )

            logger.info(f"Weekly audit job completed: {success_count}/{len(self.active_users)} users")
            return True

        except Exception as e:
            logger.error(f"Weekly audit job failed: {e}")

            log_event(
                severity="error",
                action="audit_job_failed",
                payload={
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

            return False

    def _send_audit_to_user(self, user_id: str):
        """Send audit message to a specific user."""
        logger.info(f"Sending weekly audit to user {user_id}")

        # Use the audit handler to generate and send the audit
        # Create a mock command object for the handler
        mock_command = {
            'user_id': user_id,
            'channel_id': user_id,  # DM channel
            'command': '/flow',
            'text': 'audit'
        }

        # Mock ack function
        def mock_ack():
            pass

        # Send the audit
        self.audit_handler.handle_audit_command(mock_ack, mock_command, self.slack)

        # Send weekly audit header
        self.slack.chat_postMessage(
            channel=user_id,
            text=":calendar: Weekly Project Audit",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":calendar: *Weekly Project Audit*\n\nHere's your weekly project health check. Use the actions below to keep your projects moving!"
                    }
                }
            ]
        )


def run_weekly_audit_job() -> bool:
    """Entry point for weekly audit job."""
    job = ProjectAuditJob()
    return job.run()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run the job
    success = run_weekly_audit_job()
    exit(0 if success else 1)
