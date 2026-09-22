import logging
import os
import requests
from typing import Optional

logger = logging.getLogger(__name__)

DISCORD_CONTENT_LIMIT = 2000

# Logical channel name -> environment variable holding that channel's webhook URL.
CHANNEL_ENV = {
    "diagnostics": "DISCORD_DIAGNOSTIC_WEBHOOK_URL",
    "notification": "DISCORD_NOTIFICATION_WEBHOOK_URL",
}


class DiscordNotifier:
    """
    Utility to send alerts to a Discord webhook.

    Each channel name maps to its own webhook URL in the environment.
    'diagnostics' is the operator channel (phase updates, HITL, crashes).
    'notification' is the reader channel (share summaries) and pings @everyone.
    Also reads optional 'DISCORD_USER_ID' for @mentions on critical alerts.
    """

    def __init__(
        self, channel: str = "diagnostics", webhook_url: Optional[str] = None
    ):
        self.channel = channel
        self.user_id = os.getenv("DISCORD_USER_ID")  # Optional: for @mentions

        if webhook_url:
            self.webhook_url = webhook_url
            return

        env_key = CHANNEL_ENV.get(channel)
        if not env_key:
            logger.warning(
                f"DiscordNotifier: Unknown channel '{channel}'. Notifications disabled."
            )
            self.webhook_url = None
            return

        self.webhook_url = os.getenv(env_key)
        if not self.webhook_url:
            logger.warning(
                f"DiscordNotifier: {env_key} is not set. Channel '{channel}' disabled."
            )

    def send(self, message: str, level: str = "info") -> bool:
        """
        Sends a formatted message to Discord.
        Returns True if successful, False otherwise.
        """
        if not self.webhook_url:
            return False

        payload = self._build_payload(message, level)

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=5)
            resp.raise_for_status()
            return True
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            body = ""
            if e.response is not None:
                body = (e.response.text or "")[:200]
            logger.error(
                f"Failed to send Discord notification: HTTP {status} {body}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to send Discord notification: {type(e).__name__}"
            )
            return False

    def _build_payload(self, message: str, level: str) -> dict:
        """
        Formats the webhook body. The notification channel mentions @everyone.
        """
        # Add a ping if it's a critical alert or HITL request
        prefix = ""
        if self.user_id and level in ["critical", "hitl"]:
            prefix = f"<@{self.user_id}> "

        # Add emoji indicators
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "🚨",
            "hitl": "🛑 **ACTION REQUIRED**",
        }
        emoji = emoji_map.get(level, "📢")

        mention = "@everyone " if self.channel == "notification" else ""
        full_content = f"{mention}{prefix}{emoji} {message}"
        if len(full_content) > DISCORD_CONTENT_LIMIT:
            logger.warning(
                "DiscordNotifier: Message truncated from %s to %s characters.",
                len(full_content),
                DISCORD_CONTENT_LIMIT,
            )
            full_content = full_content[: DISCORD_CONTENT_LIMIT - 1] + "…"

        payload = {"content": full_content}
        if self.channel == "notification":
            # Webhooks ignore @everyone unless it is explicitly allowed.
            payload["allowed_mentions"] = {"parse": ["everyone"]}
        return payload
