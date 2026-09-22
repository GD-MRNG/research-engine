"""
Send a share-summary style message to the Discord notification channel.

Edit TEXT and LINK below, then run:

    uv run python scripts/send_notification.py

The post is the summary text, then a blank line, then the link.
NotificationTask sends it, so the notification channel pings @everyone.
"""

import json
import logging
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.core.context import WorkflowContext
from src.tasks.notifications import NotificationTask

load_dotenv(Path(__file__).parent.parent / ".env")

# Summary body. Title, blank line, then one paragraph — same shape as ShareSummaryTask.
TEXT = """
Singapore Faces Growth Gains and Daily Strains

Singapore is prospering financially, but everyday life feels more expensive and uncertain. Strong banks, rising stocks, and major data-center investment contrast with costly fuel, food, housing, car ownership, and business rents. Families are getting more childcare support, while tougher scam laws aim to protect consumers. Jobs are split: AI and infrastructure roles are growing, but fitness, food, and retail closures show pressure on service workers. Haze, construction challenges, and regional instability add friction. Closer links with Johor may lower some costs and expand healthcare options, but also increase competition for Singapore businesses and exposure to shared regional risks.
""".strip()

# Published briefing URL. Placed on its own line at the bottom of the post.
LINK = "https://gd-mrng.github.io/political-economy-blog/weekly/briefing/2026/09/13/Singapore-Briefing.html"

for stream in (sys.stdout, sys.stdin):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    text = TEXT.strip()
    link = LINK.strip()
    if not text or not link:
        print("Set both TEXT and LINK at the top of this script. Nothing sent.")
        sys.exit(1)

    body = f"{text}\n\n{link}"
    delivered = {"ok": False}

    class _ResultHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            message = record.getMessage()
            if message.startswith("NotificationTask: Sent "):
                delivered["ok"] = True
            elif "was not delivered" in message or "Skipping send" in message:
                delivered["ok"] = False

    logging.getLogger("src.tasks.notifications").addHandler(_ResultHandler())

    with tempfile.TemporaryDirectory() as workspace:
        checkpoint_name = "notify_preview.json"
        checkpoint_path = Path(workspace) / checkpoint_name
        checkpoint_path.write_text(
            json.dumps({"intelligence": {"Share_Summary": body}}, ensure_ascii=False),
            encoding="utf-8",
        )
        print("Sending to the notification channel...")
        NotificationTask().execute(
            WorkflowContext({"_workspace_dir": workspace}),
            {
                "channel": "notification",
                "level": "info",
                "checkpoint_file": checkpoint_name,
                "content_path": "intelligence.Share_Summary",
            },
        )

    if delivered["ok"]:
        print("Sent.")
        return
    print("Not sent.")
    sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
