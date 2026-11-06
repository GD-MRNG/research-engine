"""
Launcher for the weekly briefing pipelines.

From the repo root:

    uv run python scripts/launcher.py
"""

import subprocess
import sys
import time
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Steps ─────────────────────────────────────────────────────────────────────

TESTS = [
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
]

BRIEFINGS = [
    {
        "label": "Singapore",
        "cmd": [sys.executable, "main.py", "--workflow", "cognitive-assets/workflows/sg_research_pipeline.yaml"],
        "group": "pipelines",
    },
    {
        "label": "Technology",
        "cmd": [sys.executable, "main.py", "--workflow", "cognitive-assets/workflows/tech_research_pipeline.yaml"],
        "group": "pipelines",
    },
    {
        "label": "Global news",
        "cmd": [sys.executable, "main.py", "--workflow", "cognitive-assets/workflows/news_research_pipeline.yaml"],
        "group": "pipelines",
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[2m"


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


def parse_choice(answer: str):
    """
    Returns the steps to run, None to quit, or False when the answer is not recognised.
    Enter, a, and all run the three briefings. t runs the scraper checks first.
    """
    if answer in ("q", "quit", "exit"):
        return None
    if answer in ("", "a", "all"):
        return list(BRIEFINGS)
    if answer in ("t", "tests", "test"):
        return list(TESTS) + list(BRIEFINGS)

    chosen = []
    for part in answer.replace(",", " ").split():
        if part not in ("1", "2", "3"):
            return False
        step = BRIEFINGS[int(part) - 1]
        if step not in chosen:
            chosen.append(step)
    return chosen


def show_menu():
    print(f"\n{BOLD}Weekly briefings{RESET} — {datetime.now().strftime('%A %d %B %Y')}\n")
    print(f"  {DIM}[1]{RESET} Singapore")
    print(f"  {DIM}[2]{RESET} Technology")
    print(f"  {DIM}[3]{RESET} Global news")
    print(f"  {DIM}[a]{RESET} All three briefings")
    print(f"  {DIM}[t]{RESET} Scraper checks, then the briefings")
    print()
    print("Enter runs all three. Or type 1,3, a, t, or q.")


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


def main():
    show_menu()
    while True:
        chosen = parse_choice(ask("\nChoice: "))
        if chosen is None:
            print("Aborted.")
            return
        if chosen is False:
            print("Use 1, 2, 3, a, t, or q.")
            continue
        break

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

    header("Summary")
    all_ok = all(ok for _, ok in results)
    for label, ok in results:
        icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        print(f"  {icon}  {label}")
    print()
    if all_ok:
        print(f"{GREEN}{BOLD}All steps passed.{RESET}\n")
    else:
        print(f"{RED}{BOLD}Some steps failed — check output above.{RESET}\n")


if __name__ == "__main__":
    main()
