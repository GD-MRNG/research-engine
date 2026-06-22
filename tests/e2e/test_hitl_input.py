"""
E2E test for the _prompt_file_input HITL input flow.

Interactive — follow the on-screen instructions for each case.
Tests normal input, empty-then-retry, and empty-then-skip.

Usage:
    python tests/e2e/test_hitl_input.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tasks.extractors import _prompt_file_input

TEST_FILE = "inputs/test_input.txt"

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"


def run_case(label: str, instruction: str, expect_empty: bool = False) -> bool:
    print(f"\n{BOLD}{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}Case: {label}{RESET}")
    print(f"{'─' * 60}")
    print(f"{YELLOW}What to do:{RESET} {instruction}\n")

    result = _prompt_file_input(TEST_FILE, f">>> [TEST] {label}")

    passed = (result == "") if expect_empty else bool(result)
    status = f"{GREEN}PASSED{RESET}" if passed else f"{RED}FAILED{RESET}"
    preview = repr(result[:80] + "..." if len(result) > 80 else result)
    print(f"\n  Got:    {preview}")
    print(f"  Result: {status}")
    return passed


CASES = [
    {
        "label": "Normal input",
        "instruction": (
            f"Open '{TEST_FILE}', paste any text (e.g. a URL or sentence), "
            "save, then press Enter."
        ),
        "expect_empty": False,
    },
    {
        "label": "Empty file → retry → fill in",
        "instruction": (
            f"Leave '{TEST_FILE}' empty and press Enter. "
            "At the retry prompt, fill in the file and press Enter again."
        ),
        "expect_empty": False,
    },
    {
        "label": "Empty file → skip",
        "instruction": (
            f"Leave '{TEST_FILE}' empty and press Enter. "
            "At the retry prompt, type 'skip' and press Enter."
        ),
        "expect_empty": True,
    },
]


def main():
    print(f"\n{BOLD}HITL Input Flow — E2E Test{RESET}")
    print(f"File: {os.path.abspath(TEST_FILE)}")
    print(f"Cases: {len(CASES)}\n")
    print("Follow the instructions for each case.\n")

    results = []
    for case in CASES:
        passed = run_case(
            label=case["label"],
            instruction=case["instruction"],
            expect_empty=case["expect_empty"],
        )
        results.append((case["label"], passed))

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
