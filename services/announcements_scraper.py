"""
CSE Announcements Scraper
Monitors CSE for new quarterly and annual report filings.
When detected, downloads the PDF, extracts financial data,
updates annual_reports.json, and sends an alert to the Telegram channel.

Runs daily at 6 PM SLT (12:30 PM UTC) via APScheduler.

CSE API endpoints used:
- POST /api/getFinancialAnnouncement — latest ~10 filings site-wide
- POST /api/financials?symbol=X.N0000 — per-company quarterly + annual reports
"""

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

from services.pulse_db import get_db, _execute, _fetchone, _fetchall

logger = logging.getLogger("pulse.announcements")

BASE_URL = "https://www.cse.lk/api/"
CDN_URL = "https://cdn.cse.lk/"
REPORTS_PATH = Path(__file__).parent.parent / "data" / "annual_reports.json"
SLT = timezone(timedelta(hours=5, minutes=30))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}

FORM_HEADERS = {**HEADERS, "Content-Type": "application/x-www-form-urlencoded"}

# Filing types we care about (lowercase substrings)
_QUARTERLY_KEYWORDS = ["interim financial", "quarter ended", "quarterly"]
_ANNUAL_KEYWORDS = ["annual report", "audited financial"]
_SKIP_KEYWORDS = ["errata", "prospectus", "trust deed", "accountant", "framework"]


# ---------------------------------------------------------------------------
# DB: track seen filings to avoid re-processing
# ---------------------------------------------------------------------------

_PG_TABLE = """
CREATE TABLE IF NOT EXISTS seen_filings (
    filing_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    file_text TEXT,
    filing_type TEXT,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_SQLITE_TABLE = """
CREATE TABLE IF NOT EXISTS seen_filings (
    filing_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    file_text TEXT,
    filing_type TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _init_table():
    """Create seen_filings table if needed."""
    conn = get_db()
    try:
        from services.pulse_db import _USE_PG
        if _USE_PG:
            cur = conn.cursor()
            cur.execute(_PG_TABLE)
        else:
            conn.executescript(_SQLITE_TABLE)
        conn.commit()
    finally:
        conn.close()


def _is_filing_seen(filing_id: int) -> bool:
    """Check if a filing has already been processed."""
    conn = get_db()
    try:
        row = _fetchone(conn, "SELECT 1 as found FROM seen_filings WHERE filing_id = ?", (filing_id,))
        return row is not None
    finally:
        conn.close()


def _mark_filing_seen(filing_id: int, symbol: str, file_text: str, filing_type: str):
    """Record that we've processed a filing."""
    conn = get_db()
    try:
        from services.pulse_db import _USE_PG
        if _USE_PG:
            _execute(conn,
                "INSERT INTO seen_filings (filing_id, symbol, file_text, filing_type) "
                "VALUES (?, ?, ?, ?) ON CONFLICT (filing_id) DO NOTHING",
                (filing_id, symbol, file_text, filing_type))
        else:
            _execute(conn,
                "INSERT OR IGNORE INTO seen_filings (filing_id, symbol, file_text, filing_type) "
                "VALUES (?, ?, ?, ?)",
                (filing_id, symbol, file_text, filing_type))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CSE API
# ---------------------------------------------------------------------------

def fetch_latest_announcements() -> list[dict]:
    """Fetch latest financial announcements from CSE."""
    try:
        resp = requests.post(f"{BASE_URL}getFinancialAnnouncement", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("reqFinancialAnnouncemnets", [])
    except Exception as e:
        logger.error(f"Failed to fetch announcements: {e}")
        return []


def fetch_company_filings(symbol: str) -> dict:
    """Fetch quarterly + annual filing list for a specific company."""
    try:
        resp = requests.post(f"{BASE_URL}financials", headers=FORM_HEADERS,
                             data=f"symbol={symbol}", timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch filings for {symbol}: {e}")
        return {}


def _classify_filing(file_text: str) -> str | None:
    """Classify a filing as 'quarterly', 'annual', or None (skip)."""
    lower = file_text.lower()
    for kw in _SKIP_KEYWORDS:
        if kw in lower:
            return None
    for kw in _ANNUAL_KEYWORDS:
        if kw in lower:
            return "annual"
    for kw in _QUARTERLY_KEYWORDS:
        if kw in lower:
            return "quarterly"
    return None


def _extract_quarter(file_text: str) -> str | None:
    """Extract quarter info from filing text, e.g. 'Q3 2025'."""
    lower = file_text.lower()
    import re
    # "quarter ended 31st december 2025" -> Q3 Dec
    month_map = {
        "march": "Q4", "mar": "Q4",
        "june": "Q1", "jun": "Q1",
        "september": "Q2", "sep": "Q2",
        "december": "Q3", "dec": "Q3",
    }
    for month, q in month_map.items():
        if month in lower:
            # Find year
            year_match = re.search(r"20\d{2}", file_text)
            year = year_match.group(0) if year_match else ""
            return f"{q} {year}"
    return None


# ---------------------------------------------------------------------------
# Extraction + alert
# ---------------------------------------------------------------------------

def _extract_and_update(ticker: str, pdf_url: str, filing_type: str) -> dict | None:
    """Download PDF, extract with Claude, update annual_reports.json."""
    try:
        from scripts.extract_annual_report import (
            download_pdf, extract_text_from_pdf, extract_pass1,
            fetch_company_info, PASS1_PAGES,
        )
    except ImportError:
        logger.error("Could not import extract_annual_report")
        return None

    symbol = f"{ticker}.N0000"
    info = fetch_company_info(symbol)
    company_name = info["name"] if info else None

    pdf_bytes = download_pdf(pdf_url)
    if not pdf_bytes:
        return None

    text = extract_text_from_pdf(pdf_bytes, max_pages=PASS1_PAGES)
    if not text:
        return None

    result = extract_pass1(text, company_name)
    if not result:
        return None

    # Add metadata
    if info and info.get("sector"):
        result["sector"] = info["sector"]
    result["updated"] = time.strftime("%Y-%m")

    # Update annual_reports.json
    existing = {}
    if REPORTS_PATH.exists():
        try:
            with open(REPORTS_PATH) as f:
                existing = json.load(f)
        except Exception:
            pass

    existing[ticker] = result
    with open(REPORTS_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated annual_reports.json with {ticker}")

    return result


def _build_alert_text(ticker: str, data: dict, filing_type: str, quarter: str | None) -> str:
    """Build a Telegram alert message for a new filing."""
    company = data.get("company", ticker)
    fin = data.get("financials", {})

    if filing_type == "quarterly" and quarter:
        header = f"NEW: {ticker} {quarter} results released"
    elif filing_type == "annual":
        year = data.get("year", "")
        header = f"NEW: {ticker} Annual Report {year} released"
    else:
        header = f"NEW: {ticker} financial filing"

    parts = [header]

    # Revenue
    rev = fin.get("revenue", {})
    if isinstance(rev, dict) and rev.get("value"):
        val = rev["value"]
        if val >= 1e9:
            parts.append(f"Revenue: LKR {val/1e9:.1f}B")
        elif val >= 1e6:
            parts.append(f"Revenue: LKR {val/1e6:.1f}M")
        yoy = rev.get("yoy_change")
        if yoy is not None:
            sign = "+" if yoy >= 0 else ""
            parts[-1] += f" ({sign}{yoy:.0f}% YoY)"

    # EPS
    eps = fin.get("eps")
    if eps is not None:
        parts.append(f"EPS: {eps}")

    # ROE
    roe = fin.get("roe")
    if roe is not None:
        parts.append(f"ROE: {roe}%")

    return " — ".join(parts[:1]) + "\n" + "\n".join(parts[1:]) if len(parts) > 1 else parts[0]


# ---------------------------------------------------------------------------
# Main scrape function
# ---------------------------------------------------------------------------

def scrape(bot=None):
    """
    Check for new CSE financial filings.
    Processes new annual/quarterly reports and sends alerts.
    """
    _init_table()
    logger.info("Checking CSE for new financial announcements...")

    announcements = fetch_latest_announcements()
    if not announcements:
        logger.info("No announcements to process")
        return

    new_count = 0
    for ann in announcements:
        filing_id = ann.get("id")
        symbol = ann.get("symbol", "")
        file_text = ann.get("fileText", "")
        path = ann.get("path", "")

        if not filing_id or not symbol or not path:
            continue

        # Already processed?
        if _is_filing_seen(filing_id):
            continue

        # Classify the filing
        filing_type = _classify_filing(file_text)
        if filing_type is None:
            _mark_filing_seen(filing_id, symbol, file_text, "skipped")
            logger.info(f"Skipping non-report filing: {symbol} - {file_text}")
            continue

        ticker = symbol.split(".")[0] if "." in symbol else symbol
        pdf_url = f"{CDN_URL}{path}"
        quarter = _extract_quarter(file_text) if filing_type == "quarterly" else None

        logger.info(f"New {filing_type} filing: {ticker} - {file_text}")

        # Extract data from the PDF
        try:
            data = _extract_and_update(ticker, pdf_url, filing_type)
        except Exception as e:
            logger.error(f"Extraction failed for {ticker}: {e}")
            data = None

        _mark_filing_seen(filing_id, symbol, file_text, filing_type)
        new_count += 1

        if data and bot:
            # Send alert to free channel
            alert_text = _build_alert_text(ticker, data, filing_type, quarter)
            channel_id = os.getenv("FREE_CHANNEL_ID")
            if channel_id:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(bot.send_message(chat_id=channel_id, text=alert_text))
                    else:
                        loop.run_until_complete(bot.send_message(chat_id=channel_id, text=alert_text))
                except Exception as e:
                    logger.error(f"Failed to send alert for {ticker}: {e}")

        # Recalculate sector benchmarks after new data
        if data:
            try:
                from services.sector_benchmarks import recalculate_and_save
                recalculate_and_save()
            except Exception as e:
                logger.error(f"Benchmark recalc failed: {e}")

    logger.info(f"Announcements scrape complete: {new_count} new filings processed")
