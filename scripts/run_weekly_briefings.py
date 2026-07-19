"""
Weekly run script — experimental.

Usage:
    uv run python scripts/run_weekly_briefings.py
"""

import subprocess
import sys
import time
from datetime import datetime

# ── Steps ─────────────────────────────────────────────────────────────────────

STEPS = [
    {
        "label": "E2E: Title scraper",
        "cmd": [sys.executable, "tests/e2e/test_title_scraper.py", "--csv", "tests/e2e/inputs/title_urls.csv"],
        "group": "tests",
    },
    {
        "label": "E2E: Content scraper",
        "cmd": [sys.executable, "tests/e2e/test_content_scraper.py", "--csv", "tests/e2e/inputs/content_urls.csv"],
        "group": "tests",
    },
    {
        "label": "Pipeline: SG Research",
        "cmd": [sys.executable, "main.py", "--workflow", "cognitive-assets/workflows/sg_research_pipeline.yaml"],
        "group": "pipelines",
    },
    {
        "label": "Pipeline: Tech Research",
        "cmd": [sys.executable, "main.py", "--workflow", "cognitive-assets/workflows/tech_research_pipeline.yaml"],
        "group": "pipelines",
    },
    {
        "label": "Pipeline: News Research (Global Briefing — HITL)",
        "cmd": [sys.executable, "main.py", "--workflow", "cognitive-assets/workflows/news_research_pipeline.yaml"],
        "group": "global_briefing",
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
DIM    = "\033[2m"


def header(text: str):
    width = 60
    print(f"\n{BOLD}{CYAN}{'─' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}\n")


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def run_step(step: dict) -> bool:
    """Stream step output live. Returns True if exit code 0."""
    print(f"{DIM}$ {' '.join(step['cmd'])}{RESET}\n")
    t0 = time.time()
    try:
        proc = subprocess.Popen(step["cmd"], stdout=sys.stdout, stderr=sys.stderr)
        proc.wait()
        elapsed = time.time() - t0
        ok = proc.returncode == 0
        status = f"{GREEN}PASSED{RESET}" if ok else f"{RED}FAILED (exit {proc.returncode}){RESET}"
        print(f"\n{BOLD}{status}{RESET} — {elapsed:.1f}s\n")
        return ok
    except Exception as e:
        elapsed = time.time() - t0
        print(f"\n{RED}ERROR: {e}{RESET} — {elapsed:.1f}s\n")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}Weekly Run{RESET} — {datetime.now().strftime('%A %d %B %Y, %H:%M')}")
    print(f"Steps: {len(STEPS)}\n")

    for i, step in enumerate(STEPS, start=1):
        print(f"  {DIM}[{i}]{RESET} {step['label']}")
    print()

    ans = ask("Run all steps? [Y/n/select]: ")

    if ans in ("n", "no"):
        print("Aborted.")
        return

    # Build list of steps to run
    if ans in ("s", "select"):
        chosen = []
        print()
        for i, step in enumerate(STEPS, start=1):
            a = ask(f"  Run [{i}] {step['label']}? [Y/n]: ")
            if a not in ("n", "no"):
                chosen.append(step)
        if not chosen:
            print("Nothing selected.")
            return
    else:
        chosen = list(STEPS)

    # Execute
    results = []
    for i, step in enumerate(chosen, start=1):
        header(f"[{i}/{len(chosen)}] {step['label']}")
        ok = run_step(step)
        results.append((step["label"], ok))

        if not ok and step["group"] == "tests":
            ans = ask(f"{YELLOW}Tests failed. Continue to pipelines anyway?{RESET} [y/N]: ")
            if ans not in ("y", "yes"):
                print("Stopped.")
                break

    # Summary
    header("Summary")
    all_ok = True
    for label, ok in results:
        icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        print(f"  {icon}  {label}")
        if not ok:
            all_ok = False
    print()
    if all_ok:
        print(f"{GREEN}{BOLD}All steps passed.{RESET}\n")
    else:
        print(f"{RED}{BOLD}Some steps failed — check output above.{RESET}\n")


if __name__ == "__main__":
    main()
