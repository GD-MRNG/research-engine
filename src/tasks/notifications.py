import logging
from typing import Any, Dict, Optional

from src.core.interfaces import PipelineTask
from src.core.context import WorkflowContext
from src.core.registry import register_task
from src.utils.io import CheckpointManager
from src.utils.notifications import DiscordNotifier

logger = logging.getLogger(__name__)


def _resolve_content(data: Dict[str, Any], content_path: str) -> Optional[str]:
    """Walk a dotted path such as 'intelligence.Share_Summary' and return the string."""
    current: Any = data
    for part in content_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]

    if not isinstance(current, str) or not current.strip():
        return None
    return current.strip()


@register_task("NotificationTask")
class NotificationTask(PipelineTask):
    """
    Sends a configured message to a named Discord channel.

    channel: 'diagnostics' (default) or 'notification'.
    message: static text. Used alone for operator alerts.
    content_path: dotted path into the checkpoint. When set, that value is the
    body. An explicit message is prepended as a label.
    """

    def execute(
        self, context: WorkflowContext, config: Dict[str, Any]
    ) -> WorkflowContext:
        level = config.get("level", "info")
        channel = config.get("channel", "diagnostics")
        message = config.get("message")
        content_path = config.get("content_path")

        if content_path:
            checkpoint_file = self.get_workspace_path(
                context, config.get("checkpoint_file", "research.json")
            )
            artifact = CheckpointManager.load(checkpoint_file)
            content = _resolve_content(artifact, content_path)
            if not content:
                logger.warning(
                    "NotificationTask: '%s' is empty in %s. Skipping send.",
                    content_path,
                    checkpoint_file,
                )
                return context
            message = f"{message}\n\n{content}" if message else content
        elif not message:
            message = "Pipeline step completed."

        notifier = DiscordNotifier(channel=channel)
        sent = notifier.send(message, level=level)
        if sent:
            logger.info(f"NotificationTask: Sent '{level}' alert to '{channel}'.")
        else:
            logger.warning(
                f"NotificationTask: '{level}' alert to '{channel}' was not delivered."
            )
        return context
