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


def pause(prompt="Press [ENTER] to continue..."):
    input(f"\n{DIM}{prompt}{RESET}")


def section(title, n, total):
    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}  Case {n} of {total}: {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")


def result_line(label, passed):
    icon = f"{GREEN}✓  PASSED{RESET}" if passed else f"{RED}✗  FAILED{RESET}"
    print(f"\n  {BOLD}{label}{RESET} → {icon}")


def main():
    total = 3

    print(f"\n{BOLD}HITL Input Flow — E2E Test{RESET}")
    print(f"\nKeep this file open in your editor the whole time:")
    print(f"  {BOLD}{ABS_FILE}{RESET}")
    print(f"\nThe pipeline writes a header line to that file before each prompt.")
    print(f"You paste your content below it. The header line is ignored when reading.")
    pause("Ready? Press [ENTER] to start...")

    results = []

    # ── Case 1: Normal input ────────────────────────────────────────────────────

    section("Normal input", 1, total)
    print(f"""
  The file will refresh with a header line.
  Paste anything below it, save, then press [ENTER] here.
""")
    pause("Press [ENTER] to begin...")

    r1 = _prompt_file_input(TEST_FILE, ">>> [TEST 1] Paste any text below this line:")
    passed1 = bool(r1)
    result_line("Case 1", passed1)
    results.append(("Normal input", passed1))

    # ── Case 2: Empty → retry → fill in ────────────────────────────────────────

    section("Empty file → retry → fill in", 2, total)
    print(f"""
  The file will refresh with a header line.
  Press [ENTER] here WITHOUT adding anything to the file.
  You'll get a warning. The file will refresh with a RETRY header —
  paste something below it, save, then press [ENTER] here.
""")
    pause("Press [ENTER] to begin...")

    r2 = _prompt_file_input(TEST_FILE, ">>> [TEST 2] Leave this file empty and press Enter in the terminal:")
    passed2 = bool(r2)
    result_line("Case 2", passed2)
    results.append(("Empty → retry → fill in", passed2))

    # ── Case 3: Empty → skip ────────────────────────────────────────────────────

    section("Empty file → skip", 3, total)
    print(f"""
  The file will refresh with a header line.
  Press [ENTER] here WITHOUT adding anything to the file.
  You'll get a warning. At the retry prompt, type  skip  and press [ENTER].
""")
    pause("Press [ENTER] to begin...")

    r3 = _prompt_file_input(TEST_FILE, ">>> [TEST 3] Leave this file empty and press Enter in the terminal:")
    passed3 = (r3 == "")
    result_line("Case 3", passed3)
    if not passed3:
        print(f"  {RED}Expected empty after skip but got: {repr(r3)}{RESET}")
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
