"""
E2E test for the _prompt_file_input HITL input flow.

Interactive — follow the on-screen instructions at each step.

Usage:
    python tests/e2e/test_hitl_input.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tasks.extractors import _prompt_file_input

TEST_FILE = "inputs/test_input.txt"
ABS_FILE  = os.path.abspath(TEST_FILE)

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
DIM    = "\033[2m"


def pause(prompt: str = "Press [ENTER] to continue..."):
    input(f"\n{DIM}{prompt}{RESET}")


def section(title: str, n: int, total: int):
    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}  Case {n} of {total}: {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")


def result_line(label: str, passed: bool):
    icon   = f"{GREEN}✓  PASSED{RESET}" if passed else f"{RED}✗  FAILED{RESET}"
    print(f"\n  {BOLD}{label}{RESET} → {icon}")


def main():
    total = 3

    print(f"\n{BOLD}HITL Input Flow — E2E Test{RESET}")
    print(f"\nThis test walks you through {total} input scenarios.")
    print(f"At each step you will be told exactly what to do.")
    print(f"\nInput file: {BOLD}{ABS_FILE}{RESET}")
    print(f"\nOpen that file in your editor now and keep it visible alongside this terminal.")
    pause("Ready? Press [ENTER] to start...")

    results = []

    # ── Case 1: Normal input ────────────────────────────────────────────────────

    section("Normal input", 1, total)
    print(f"""
What will happen:
  The file will be overwritten with a >>> header line.
  You paste your content, save, then press Enter here.

Your steps:
  1. Go to {BOLD}{ABS_FILE}{RESET}
  2. Delete the >>> header line
  3. Paste any text — a URL or sentence is fine
  4. Save the file
  5. Come back here and press [ENTER]
""")
    pause("Ready? Press [ENTER] to begin this case...")

    r1 = _prompt_file_input(TEST_FILE, ">>> [TEST CASE 1] Normal input — paste any text below:")
    passed1 = bool(r1)
    result_line("Case 1", passed1)
    if not passed1:
        print(f"  {RED}Expected some content but got nothing.{RESET}")
    results.append(("Normal input", passed1))

    # ── Case 2: Empty → retry → fill in ────────────────────────────────────────

    section("Empty file → retry → fill in", 2, total)
    print(f"""
What will happen:
  The file will be overwritten with a >>> header line.
  You press Enter WITHOUT adding anything — triggering the empty warning.
  You then fill in the file and press Enter again to retry.

Your steps:
  1. Go to {BOLD}{ABS_FILE}{RESET}
  2. Do NOT change anything — leave it with just the >>> header
  3. Come back here and press [ENTER]
     → You will see: "I didn't get anything from the file."
     → You will see: "Fill it in and press [ENTER] to retry, or type 'skip'..."
  4. Go back to the file, delete the >>> header, paste any text, save
  5. Come back here and press [ENTER]  (do NOT type 'skip')
""")
    pause("Ready? Press [ENTER] to begin this case...")

    r2 = _prompt_file_input(TEST_FILE, ">>> [TEST CASE 2] Leave this file as-is and press Enter in the terminal:")
    passed2 = bool(r2)
    result_line("Case 2", passed2)
    if not passed2:
        print(f"  {RED}Expected content after retry but got nothing.{RESET}")
    results.append(("Empty → retry → fill in", passed2))

    # ── Case 3: Empty → skip ────────────────────────────────────────────────────

    section("Empty file → skip", 3, total)
    print(f"""
What will happen:
  The file will be overwritten with a >>> header line.
  You press Enter WITHOUT adding anything — triggering the empty warning.
  You then type 'skip' to continue without providing input.

Your steps:
  1. Go to {BOLD}{ABS_FILE}{RESET}
  2. Do NOT change anything — leave it with just the >>> header
  3. Come back here and press [ENTER]
     → You will see: "I didn't get anything from the file."
     → You will see: "Fill it in and press [ENTER] to retry, or type 'skip'..."
  4. Type  skip  and press [ENTER]
""")
    pause("Ready? Press [ENTER] to begin this case...")

    r3 = _prompt_file_input(TEST_FILE, ">>> [TEST CASE 3] Leave this file as-is and press Enter in the terminal:")
    passed3 = (r3 == "")
    result_line("Case 3", passed3)
    if not passed3:
        print(f"  {RED}Expected empty result after skip but got: {repr(r3)}{RESET}")
    results.append(("Empty → skip", passed3))

    # ── Summary ─────────────────────────────────────────────────────────────────

    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}Summary{RESET}")
    print(f"{'─' * 60}")

    all_ok = True
    for label, passed in results:
        icon = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"  {icon}  {label}")
        if not passed:
            all_ok = False

    print()
    if all_ok:
        print(f"{GREEN}{BOLD}All cases passed.{RESET}\n")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}Some cases failed — check output above.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
