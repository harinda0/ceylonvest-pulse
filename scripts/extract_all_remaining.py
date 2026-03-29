"""
Batch extractor for ALL remaining CSE annual reports.
Skips tickers already in data/annual_reports.json.
Saves progress every 5 stocks.

Usage:
    python scripts/extract_all_remaining.py              # all remaining
    python scripts/extract_all_remaining.py --jkh-first  # re-extract JKH with 150 pages, then all remaining
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
from scripts.extract_annual_report import process_ticker, OUTPUT_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("batch_extractor")

SAVE_INTERVAL = 5  # Save after every N successful extractions
PAGES_PER_PDF = 100  # Balance between coverage and API cost


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


def main():
    args = sys.argv[1:]
    jkh_first = "--jkh-first" in args

    # Load existing data
    existing = load_existing()
    logger.info(f"Loaded {len(existing)} existing entries")

    # Build list of tickers to process
    all_tickers = sorted(TICKER_TO_CSE.keys())

    if jkh_first:
        # Re-extract JKH first with 150 pages (already set in extract_annual_report.py)
        logger.info("=" * 60)
        logger.info("RE-EXTRACTING JKH with 150 pages")
        logger.info("=" * 60)
        try:
            data = process_ticker("JKH")
            if data:
                source = data.pop("source_pdf", None)
                existing["JKH"] = data
                save_data(existing)
                logger.info(f"JKH re-extracted successfully. EPS: {data.get('financials', {}).get('eps')}, NAV: {data.get('financials', {}).get('nav')}, ROE: {data.get('financials', {}).get('roe')}")
            else:
                logger.error("JKH re-extraction failed")
        except Exception as e:
            logger.error(f"JKH re-extraction error: {e}")
        time.sleep(2)

    # Skip already-extracted tickers
    remaining = [t for t in all_tickers if t not in existing]
    logger.info(f"Total tickers: {len(all_tickers)}, Already done: {len(existing)}, Remaining: {len(remaining)}")

    if not remaining:
        logger.info("All tickers already extracted!")
        return

    # Override MAX_PDF_PAGES for batch mode (100 pages for cost efficiency)
    import scripts.extract_annual_report as extractor
    extractor.MAX_PDF_PAGES = PAGES_PER_PDF

    # Process remaining tickers
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
                logger.info(f"  OK: {data.get('company', '?')} - {data.get('year', '?')}")

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
        # 30k token/min limit means ~2 requests/min max for large PDFs
        if i < len(remaining):
            wait = 35 if data else 3  # shorter wait if no PDF/API call was made
            time.sleep(wait)

    # Final save
    if new_since_save > 0:
        save_data(existing)

    # Summary
    logger.info("=" * 60)
    logger.info(f"BATCH EXTRACTION COMPLETE")
    logger.info(f"  Successful: {success_count}/{len(remaining)}")
    logger.info(f"  Total entries: {len(existing)}")
    logger.info(f"  No annual report available: {len(no_report)}")
    logger.info(f"  Failed (errors): {len(failed)}")
    logger.info("=" * 60)

    if no_report:
        logger.info(f"No report: {', '.join(no_report)}")
    if failed:
        logger.info(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
