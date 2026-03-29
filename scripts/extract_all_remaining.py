"""
Batch extractor for ALL CSE annual reports using two-pass strategy.

Phase 1: Re-run Pass 2 for existing stocks that have null metrics
Phase 2: Process all remaining tickers with two-pass extraction
Saves progress every 5 stocks.

Usage:
    python scripts/extract_all_remaining.py              # full run
    python scripts/extract_all_remaining.py --fix-nulls  # only fix existing nulls
    python scripts/extract_all_remaining.py --new-only   # only new tickers
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.ticker_map import TICKER_TO_CSE
from scripts.extract_annual_report import (
    process_ticker, process_ticker_pass2_only,
    OUTPUT_PATH, _get_missing_metrics,
    PASS1_PAGES, PASS2_PAGES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("batch_extractor")

SAVE_INTERVAL = 5  # Save after every N successful extractions
API_COOLDOWN = 35  # Seconds between API calls to avoid rate limits


def load_existing() -> dict:
    """Load existing annual_reports.json."""
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load existing data: {e}")
    return {}


def save_data(data: dict):
    """Save to annual_reports.json."""
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fix_existing_nulls(existing: dict) -> dict:
    """Phase 1: Re-run Pass 2 for existing stocks with null critical metrics."""
    needs_fix = {}
    for ticker, data in existing.items():
        missing = _get_missing_metrics(data)
        if missing:
            needs_fix[ticker] = missing

    if not needs_fix:
        logger.info("All existing stocks have complete metrics!")
        return existing

    logger.info(f"{'='*60}")
    logger.info(f"PHASE 1: Fix {len(needs_fix)} existing stocks with null metrics")
    for t, m in needs_fix.items():
        logger.info(f"  {t}: missing {m}")
    logger.info(f"{'='*60}")

    fixed = 0
    for i, (ticker, missing) in enumerate(needs_fix.items(), 1):
        logger.info(f"[{i}/{len(needs_fix)}] Fixing {ticker} (missing: {missing})")
        try:
            updated = process_ticker_pass2_only(ticker, existing[ticker])
            if updated:
                existing[ticker] = updated
                existing[ticker]["updated"] = time.strftime("%Y-%m")
                new_missing = _get_missing_metrics(updated)
                if len(new_missing) < len(missing):
                    fixed += 1
                    save_data(existing)
                    logger.info(f"  IMPROVED: {ticker} (was missing {missing}, now missing {new_missing})")
                else:
                    logger.info(f"  No improvement for {ticker}")
        except Exception as e:
            logger.error(f"  FAIL: {ticker} - {e}")

        if i < len(needs_fix):
            time.sleep(API_COOLDOWN)

    logger.info(f"Phase 1 complete: improved {fixed}/{len(needs_fix)} stocks")
    return existing


def process_remaining(existing: dict) -> dict:
    """Phase 2: Process all remaining tickers not in existing data."""
    all_tickers = sorted(TICKER_TO_CSE.keys())
    remaining = [t for t in all_tickers if t not in existing]

    logger.info(f"{'='*60}")
    logger.info(f"PHASE 2: Process {len(remaining)} remaining tickers")
    logger.info(f"  Total tickers: {len(all_tickers)}")
    logger.info(f"  Already done: {len(existing)}")
    logger.info(f"  Remaining: {len(remaining)}")
    logger.info(f"{'='*60}")

    if not remaining:
        logger.info("All tickers already extracted!")
        return existing

    success_count = 0
    failed = []
    no_report = []
    new_since_save = 0

    for i, ticker in enumerate(remaining, 1):
        logger.info(f"[{i}/{len(remaining)}] Processing {ticker}...")
        try:
            data = process_ticker(ticker)
            if data:
                source = data.pop("source_pdf", None)
                existing[ticker] = data
                success_count += 1
                new_since_save += 1
                fin = data.get("financials", {})
                logger.info(f"  OK: {data.get('company', '?')} EPS={fin.get('eps')} ROE={fin.get('roe')}")

                # Save periodically
                if new_since_save >= SAVE_INTERVAL:
                    save_data(existing)
                    logger.info(f"  SAVED ({len(existing)} total entries)")
                    new_since_save = 0
            else:
                logger.warning(f"  SKIP: No data for {ticker}")
                no_report.append(ticker)
        except Exception as e:
            logger.error(f"  FAIL: {ticker} - {e}")
            failed.append(ticker)

        # Rate limit — wait between API calls to avoid 429s
        if i < len(remaining):
            wait = API_COOLDOWN if data else 3
            time.sleep(wait)

    # Final save
    if new_since_save > 0:
        save_data(existing)

    # Summary
    logger.info(f"{'='*60}")
    logger.info(f"PHASE 2 COMPLETE")
    logger.info(f"  Successful: {success_count}/{len(remaining)}")
    logger.info(f"  Total entries: {len(existing)}")
    logger.info(f"  No annual report available: {len(no_report)}")
    logger.info(f"  Failed (errors): {len(failed)}")
    logger.info(f"{'='*60}")

    if no_report:
        logger.info(f"No report: {', '.join(no_report)}")
    if failed:
        logger.info(f"Failed: {', '.join(failed)}")

    return existing


def main():
    args = sys.argv[1:]
    fix_only = "--fix-nulls" in args
    new_only = "--new-only" in args

    existing = load_existing()
    logger.info(f"Loaded {len(existing)} existing entries")

    if not new_only:
        # Phase 1: Fix existing stocks with null metrics
        existing = fix_existing_nulls(existing)

    if not fix_only:
        # Phase 2: Process remaining tickers
        existing = process_remaining(existing)

    # Final save
    save_data(existing)
    logger.info(f"Done. Total entries: {len(existing)}")


if __name__ == "__main__":
    main()
