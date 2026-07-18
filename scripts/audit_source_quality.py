"""
Source quality audit.

Runs the production Selenium -> Scrapling fallback chain (src/utils/web.py)
against every source of a given `type` in a sources CSV, records exactly what
happened per URL, and writes a markdown report flagging problem sources.

Usage:
    uv run python scripts/audit_source_quality.py --csv cognitive-assets/sources/tech_research_sources.csv
    uv run python scripts/audit_source_quality.py --csv cognitive-assets/sources/tech_research_sources.csv --type analysis --limit 20
    uv run python scripts/audit_source_quality.py --csv ... --resume outputs/quality_audits/tech_research_sources_datapoint_20260719_101500.json
"""

import argparse
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from src.utils.io import CheckpointManager
from src.utils.web import (
    WebPageExtractor,
    MIN_CONTENT_CHARS,
    MIN_NEGLIGIBLE_CHARS,
    _parse_content,
    _parse_title,
    _scrapling_fetch_html,
    _is_bot_challenge_title,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

STATUS_ORDER = {
    "ERROR": 0,
    "FAIL": 1,
    "WARN_BOT_BLOCKED": 2,
    "WARN_FALLBACK": 3,
    "WARN_SHORT_CONTENT": 4,
    "OK": 5,
}


def load_sources(csv_path: str, source_type: str, limit: int | None) -> list[dict]:
    df = pd.read_csv(csv_path)
    for field in ("id", "name", "url", "type", "rank", "tags", "format"):
        if field not in df.columns:
            df[field] = ""
    df = df[df["type"].astype(str).str.lower() == source_type.lower()]

    # Only "webpage" sources (the default when unset) go through the
    # Selenium -> Scrapling chain in production; youtube/podcast/manual
    # sources use entirely different extractors and would misreport as FAIL.
    fmt = df["format"].astype(str).str.lower().replace({"": "webpage", "nan": "webpage"})
    skipped = df[fmt != "webpage"]
    for _, row in skipped.iterrows():
        logger.info(f"Skipping non-webpage source (format={row.get('format')}): {row.get('url')}")
    df = df[fmt == "webpage"]

    rows = df.to_dict("records")
    if limit:
        rows = rows[:limit]
    return rows


def inspect_url(extractor: WebPageExtractor, url: str) -> dict:
    """Drive the Selenium -> Scrapling chain step by step, mirroring the
    accept/reject logic in WebPageExtractor.get_webpage_content so the report
    can attribute which fetcher produced the final content, whether a
    bot-challenge was hit, and how many characters were actually usable."""
    result = {
        "selenium_chars": 0,
        "scrapling_chars": 0,
        "final_chars": 0,
        "method": "none",
        "bot_blocked": False,
        "error": "",
    }
    t0 = time.time()
    try:
        extractor._ensure_page_loaded(url)
    except RuntimeError as e:
        # Selenium exceptions can carry multi-line stacktraces; collapse to one
        # line so the error doesn't break the markdown table it's rendered into.
        result["error"] = " ".join(str(e).split())
        result["elapsed_seconds"] = round(time.time() - t0, 1)
        result["status"] = "ERROR"
        return result

    driver = extractor.manager.get_driver()
    selenium_html = driver.page_source
    selenium_content = _parse_content(selenium_html)
    result["selenium_chars"] = len(selenium_content)

    if len(selenium_content) >= MIN_CONTENT_CHARS:
        result["method"] = "selenium"
        result["final_chars"] = len(selenium_content)
        title_html = selenium_html
    else:
        scrapling_html = _scrapling_fetch_html(url)
        scrapling_content = _parse_content(scrapling_html) if scrapling_html else ""
        result["scrapling_chars"] = len(scrapling_content)

        if len(scrapling_content) >= MIN_CONTENT_CHARS:
            result["method"] = "scrapling"
            result["final_chars"] = len(scrapling_content)
            title_html = scrapling_html
        else:
            # Neither cleared the threshold - mirror production's "return the
            # best available" behavior instead of discarding real short content.
            if len(selenium_content) >= len(scrapling_content):
                best_content, title_html, best_method = selenium_content, selenium_html, "selenium_short"
            else:
                best_content, title_html, best_method = scrapling_content, scrapling_html, "scrapling_short"
            result["final_chars"] = len(best_content)
            result["method"] = best_method if len(best_content) >= MIN_NEGLIGIBLE_CHARS else "none"

    title = _parse_title(title_html) if title_html else ""
    result["bot_blocked"] = bool(title) and _is_bot_challenge_title(title)

    result["elapsed_seconds"] = round(time.time() - t0, 1)

    if result["method"] == "none":
        result["status"] = "FAIL"
    elif result["bot_blocked"]:
        result["status"] = "WARN_BOT_BLOCKED"
    elif result["method"] == "scrapling":
        result["status"] = "WARN_FALLBACK"
    elif result["method"] in ("selenium_short", "scrapling_short"):
        result["status"] = "WARN_SHORT_CONTENT"
    else:
        result["status"] = "OK"

    return result


def run_audit(sources: list[dict], checkpoint_path: str, resume: bool) -> dict:
    data = CheckpointManager.load(checkpoint_path) if resume else {}
    results = data.get("results", {})

    extractor = WebPageExtractor()
    total = len(sources)
    try:
        for i, source in enumerate(sources, start=1):
            url = str(source.get("url", "")).strip()
            if not url:
                continue
            key = str(source.get("id", url))
            if key in results:
                logger.info(f"[{i}/{total}] SKIP (already recorded): {url}")
                continue

            logger.info(f"[{i}/{total}] Testing: {url}")
            inspection = inspect_url(extractor, url)
            record = {
                "id": source.get("id", ""),
                "name": source.get("name", ""),
                "url": url,
                "rank": source.get("rank", ""),
                "tags": source.get("tags", ""),
                **inspection,
            }
            results[key] = record
            logger.info(
                f"  -> {record['status']} via {record['method']} "
                f"(selenium={record['selenium_chars']}, scrapling={record['scrapling_chars']}, "
                f"final={record['final_chars']}, {record['elapsed_seconds']}s)"
            )

            CheckpointManager.save(checkpoint_path, {"results": results})
    finally:
        extractor.manager.quit_driver()

    return results


def _cell(text) -> str:
    """Sanitize a value for use inside a markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def render_report(results: dict, csv_path: str, source_type: str) -> str:
    rows = list(results.values())
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    total = len(rows)
    ok = counts.get("OK", 0)

    lines = []
    lines.append(f"# Source Quality Audit — {Path(csv_path).name} ({source_type})")
    lines.append("")
    lines.append(f"- **Run at**: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- **CSV**: `{csv_path}`")
    lines.append(f"- **Type filter**: `{source_type}`")
    lines.append(f"- **Sources tested**: {total}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Status | Count | % |")
    lines.append("|---|---|---|")
    for status in ("OK", "WARN_FALLBACK", "WARN_SHORT_CONTENT", "WARN_BOT_BLOCKED", "FAIL", "ERROR"):
        n = counts.get(status, 0)
        pct = f"{(n / total * 100):.0f}%" if total else "0%"
        lines.append(f"| {status} | {n} | {pct} |")
    pass_pct = f"{(ok / total * 100):.0f}%" if total else "0%"
    lines.append("")
    lines.append(f"**Pass rate (OK): {pass_pct}** ({ok}/{total})")
    lines.append("")

    problems = [r for r in rows if r["status"] != "OK"]
    problems.sort(key=lambda r: STATUS_ORDER.get(r["status"], 99))

    lines.append("## Problem sources")
    lines.append("")
    if not problems:
        lines.append("None — every tested source passed cleanly.")
    else:
        lines.append("| Status | Id | Name | URL | Reason | Selenium chars | Scrapling chars | Final chars | Elapsed |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in problems:
            reason = r["error"] if r["error"] else {
                "FAIL": "Both Selenium and Scrapling returned negligible content (< 200 chars)",
                "WARN_BOT_BLOCKED": "Bot-challenge / cookie-wall page detected",
                "WARN_FALLBACK": "Selenium alone insufficient; Scrapling fallback engaged",
                "WARN_SHORT_CONTENT": "Neither fetcher reached the 2000-char threshold; returning best available (real but short) content",
                "ERROR": "Navigation error",
            }.get(r["status"], "")
            lines.append(
                f"| {r['status']} | {_cell(r['id'])} | {_cell(r['name'])} | {_cell(r['url'])} | {_cell(reason)} | "
                f"{r['selenium_chars']} | {r['scrapling_chars']} | {r['final_chars']} | {r['elapsed_seconds']}s |"
            )
    lines.append("")

    lines.append("## Full results")
    lines.append("")
    lines.append("<details><summary>All tested sources</summary>")
    lines.append("")
    lines.append("| Status | Id | Name | URL | Method | Selenium chars | Scrapling chars | Final chars | Elapsed |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: STATUS_ORDER.get(r["status"], 99)):
        lines.append(
            f"| {r['status']} | {_cell(r['id'])} | {_cell(r['name'])} | {_cell(r['url'])} | {r['method']} | "
            f"{r['selenium_chars']} | {r['scrapling_chars']} | {r['final_chars']} | {r['elapsed_seconds']}s |"
        )
    lines.append("")
    lines.append("</details>")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit source CSV extraction quality")
    parser.add_argument("--csv", required=True, help="Path to a sources CSV")
    parser.add_argument("--type", default="datapoint", help="Source 'type' column value to test (default: datapoint)")
    parser.add_argument("--limit", type=int, default=None, help="Cap the number of URLs tested")
    parser.add_argument("--out-dir", default="outputs/quality_audits", help="Directory for the JSON checkpoint and markdown report")
    parser.add_argument("--resume", default=None, help="Path to a prior run's JSON checkpoint to resume")
    args = parser.parse_args()

    sources = load_sources(args.csv, args.type, args.limit)
    if not sources:
        print(f"No sources of type '{args.type}' found in {args.csv}")
        return

    if args.resume:
        checkpoint_path = args.resume
    else:
        stem = Path(args.csv).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_path = str(Path(args.out_dir) / f"{stem}_{args.type}_{timestamp}.json")

    print(f"\nAuditing {len(sources)} '{args.type}' sources from {args.csv}")
    print(f"Checkpoint: {checkpoint_path}\n")

    results = run_audit(sources, checkpoint_path, resume=bool(args.resume))

    report = render_report(results, args.csv, args.type)
    report_path = str(Path(checkpoint_path).with_suffix(".md"))
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(report, encoding="utf-8")

    print(f"\nReport written to: {report_path}\n")


if __name__ == "__main__":
    main()
