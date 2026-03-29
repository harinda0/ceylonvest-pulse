"""
Director Dealings Scraper
Extracts director share transactions from CSE quarterly report PDFs.

CSE requires directors to disclose all share transactions in quarterly filings.
Since no dedicated API endpoint exists, we extract this data from the quarterly
report PDFs that are already available via POST /api/financials.

Data is stored in the director_dealings DB table and displayed on the
Insiders button in the ticker card.

Runs daily at 7 PM SLT (1:30 PM UTC) via APScheduler (after announcements scraper).
"""

import json
import logging
import os
import re
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pdfplumber
import requests

from services.pulse_db import get_db, _execute, _fetchone, _fetchall

logger = logging.getLogger("pulse.director_dealings")

BASE_URL = "https://www.cse.lk/api/"
CDN_URL = "https://cdn.cse.lk/"
SLT = timezone(timedelta(hours=5, minutes=30))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}


# ---------------------------------------------------------------------------
# DB schema
# ---------------------------------------------------------------------------

_PG_TABLE = """
CREATE TABLE IF NOT EXISTS director_dealings (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    director_name TEXT NOT NULL,
    deal_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price DOUBLE PRECISION,
    deal_date DATE,
    source_pdf TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dd_ticker ON director_dealings(ticker);
CREATE INDEX IF NOT EXISTS idx_dd_date ON director_dealings(deal_date);
CREATE INDEX IF NOT EXISTS idx_dd_ticker_date ON director_dealings(ticker, deal_date);

CREATE TABLE IF NOT EXISTS seen_quarterly_pdfs (
    pdf_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_SQLITE_TABLE = """
CREATE TABLE IF NOT EXISTS director_dealings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    director_name TEXT NOT NULL,
    deal_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL,
    deal_date TEXT,
    source_pdf TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dd_ticker ON director_dealings(ticker);
CREATE INDEX IF NOT EXISTS idx_dd_date ON director_dealings(deal_date);
CREATE INDEX IF NOT EXISTS idx_dd_ticker_date ON director_dealings(ticker, deal_date);

CREATE TABLE IF NOT EXISTS seen_quarterly_pdfs (
    pdf_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _init_tables():
    """Create tables if needed."""
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


def _is_pdf_seen(pdf_id: int) -> bool:
    conn = get_db()
    try:
        row = _fetchone(conn, "SELECT 1 as found FROM seen_quarterly_pdfs WHERE pdf_id = ?", (pdf_id,))
        return row is not None
    finally:
        conn.close()


def _mark_pdf_seen(pdf_id: int, symbol: str):
    conn = get_db()
    try:
        from services.pulse_db import _USE_PG
        if _USE_PG:
            _execute(conn,
                "INSERT INTO seen_quarterly_pdfs (pdf_id, symbol) VALUES (?, ?) "
                "ON CONFLICT (pdf_id) DO NOTHING", (pdf_id, symbol))
        else:
            _execute(conn,
                "INSERT OR IGNORE INTO seen_quarterly_pdfs (pdf_id, symbol) VALUES (?, ?)",
                (pdf_id, symbol))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def add_dealing(ticker: str, director_name: str, deal_type: str,
                quantity: int, price: float | None, deal_date: str | None,
                source_pdf: str | None):
    """Store a director dealing record."""
    conn = get_db()
    try:
        _execute(conn,
            "INSERT INTO director_dealings "
            "(ticker, director_name, deal_type, quantity, price, deal_date, source_pdf) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticker, director_name[:200], deal_type, quantity, price, deal_date, source_pdf))
        conn.commit()
    finally:
        conn.close()


def get_recent_dealings(ticker: str, limit: int = 10) -> list[dict]:
    """Get recent director dealings for a ticker."""
    _init_tables()
    conn = get_db()
    try:
        rows = _fetchall(conn,
            "SELECT director_name, deal_type, quantity, price, deal_date "
            "FROM director_dealings WHERE ticker = ? "
            "ORDER BY deal_date DESC, created_at DESC LIMIT ?",
            (ticker, limit))
        return rows
    finally:
        conn.close()


def get_net_activity(ticker: str, days: int = 90) -> dict:
    """
    Calculate net director buy/sell activity over the given period.
    Returns: {"net_buys": int, "net_sells": int, "net_quantity": int, "signal": str}
    """
    _init_tables()
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = _fetchall(conn,
            "SELECT deal_type, SUM(quantity) as total_qty, COUNT(*) as cnt "
            "FROM director_dealings WHERE ticker = ? AND deal_date >= ? "
            "GROUP BY deal_type",
            (ticker, cutoff))
    finally:
        conn.close()

    buys = 0
    sells = 0
    buy_count = 0
    sell_count = 0
    for r in rows:
        if r["deal_type"] == "buy":
            buys = r["total_qty"] or 0
            buy_count = r["cnt"]
        elif r["deal_type"] == "sell":
            sells = r["total_qty"] or 0
            sell_count = r["cnt"]

    net = buys - sells
    if buy_count > 0 and sell_count == 0:
        signal = "bullish"
    elif sell_count > 0 and buy_count == 0:
        signal = "bearish"
    elif net > 0:
        signal = "slightly bullish"
    elif net < 0:
        signal = "slightly bearish"
    else:
        signal = "neutral"

    return {
        "net_buys": buys,
        "net_sells": sells,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "net_quantity": net,
        "signal": signal,
    }


# ---------------------------------------------------------------------------
# PDF extraction — director dealings from quarterly reports
# ---------------------------------------------------------------------------

def _extract_dealings_from_pdf(pdf_bytes: bytes, ticker: str) -> list[dict]:
    """
    Extract director share dealings from a quarterly report PDF.
    Looks for the "Directors' Interest in Shares" or similar sections.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name

    dealings = []
    try:
        with pdfplumber.open(tmp_path) as pdf:
            # Scan all pages for director dealings section
            target_pages = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                lower = text.lower()
                if any(kw in lower for kw in [
                    "director", "interest in shares",
                    "director dealing", "insider trading",
                    "share transactions by directors",
                    "directors' shareholding",
                ]):
                    target_pages.append((i, text))

            if not target_pages:
                return []

            # Try to extract structured data from tables
            for page_idx, text in target_pages:
                page = pdf.pages[page_idx]
                tables = page.extract_tables()
                for table in tables:
                    dealings.extend(_parse_dealings_table(table, ticker))

                # Also try regex on text for common patterns
                dealings.extend(_parse_dealings_text(text, ticker))

    except Exception as e:
        logger.error(f"PDF extraction failed for {ticker}: {e}")
    finally:
        os.unlink(tmp_path)

    # Deduplicate by (director, type, quantity, date)
    seen = set()
    unique = []
    for d in dealings:
        key = (d["director_name"], d["deal_type"], d["quantity"], d.get("deal_date"))
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return unique


def _parse_dealings_table(table: list[list], ticker: str) -> list[dict]:
    """Parse a pdfplumber table for director dealing rows."""
    if not table or len(table) < 2:
        return []

    dealings = []
    # Try to identify column headers
    header = [str(c).lower().strip() if c else "" for c in table[0]]

    name_col = None
    type_col = None
    qty_col = None
    price_col = None
    date_col = None

    for i, h in enumerate(header):
        if "name" in h or "director" in h:
            name_col = i
        elif "type" in h or "nature" in h or "buy" in h and "sell" in h:
            type_col = i
        elif "quantity" in h or "no. of" in h or "shares" in h:
            qty_col = i
        elif "price" in h or "value" in h:
            price_col = i
        elif "date" in h:
            date_col = i

    if name_col is None or qty_col is None:
        return []

    for row in table[1:]:
        if not row or len(row) <= max(name_col, qty_col):
            continue

        name = str(row[name_col] or "").strip()
        if not name or len(name) < 3:
            continue

        # Parse quantity
        qty_str = str(row[qty_col] or "").strip().replace(",", "").replace(" ", "")
        try:
            quantity = int(float(qty_str))
        except (ValueError, TypeError):
            continue

        if quantity <= 0:
            continue

        # Parse deal type
        deal_type = "buy"  # default
        if type_col is not None and row[type_col]:
            t = str(row[type_col]).lower()
            if "sell" in t or "sale" in t or "dispose" in t:
                deal_type = "sell"

        # Parse price
        price = None
        if price_col is not None and row[price_col]:
            try:
                price = float(str(row[price_col]).replace(",", "").replace("Rs.", "").strip())
            except (ValueError, TypeError):
                pass

        # Parse date
        deal_date = None
        if date_col is not None and row[date_col]:
            deal_date = _parse_date(str(row[date_col]))

        dealings.append({
            "director_name": name[:200],
            "deal_type": deal_type,
            "quantity": quantity,
            "price": price,
            "deal_date": deal_date,
        })

    return dealings


def _parse_dealings_text(text: str, ticker: str) -> list[dict]:
    """
    Regex-based extraction for common director dealing patterns in text.
    Patterns like: "Mr. X purchased 100,000 shares at Rs. 45.50 on 15/01/2026"
    """
    dealings = []

    # Pattern: Name ... bought/purchased/sold/disposed ... N shares ... at Rs. X
    patterns = [
        re.compile(
            r"(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-zA-Z\s.]+?)\s+"
            r"(?:purchased|bought|acquired)\s+"
            r"([\d,]+)\s+(?:ordinary\s+)?shares?"
            r"(?:\s+at\s+(?:Rs\.?\s*)?([\d,.]+))?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-zA-Z\s.]+?)\s+"
            r"(?:sold|disposed|transferred)\s+"
            r"([\d,]+)\s+(?:ordinary\s+)?shares?"
            r"(?:\s+at\s+(?:Rs\.?\s*)?([\d,.]+))?",
            re.IGNORECASE,
        ),
    ]

    for i, pattern in enumerate(patterns):
        deal_type = "buy" if i == 0 else "sell"
        for match in pattern.finditer(text):
            name = match.group(1).strip()
            qty_str = match.group(2).replace(",", "")
            try:
                quantity = int(qty_str)
            except ValueError:
                continue

            price = None
            if match.group(3):
                try:
                    price = float(match.group(3).replace(",", ""))
                except ValueError:
                    pass

            dealings.append({
                "director_name": name[:200],
                "deal_type": deal_type,
                "quantity": quantity,
                "price": price,
                "deal_date": None,
            })

    return dealings


def _parse_date(date_str: str) -> str | None:
    """Try to parse a date string into YYYY-MM-DD."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d",
                "%d %b %Y", "%d %B %Y", "%b %d, %Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# CSE API
# ---------------------------------------------------------------------------

def _fetch_recent_quarterly_pdfs(symbol: str, limit: int = 4) -> list[dict]:
    """Get the most recent quarterly report PDFs for a company."""
    try:
        resp = requests.post(f"{BASE_URL}financials", headers=HEADERS,
                             data=f"symbol={symbol}", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        quarterly = data.get("infoQuarterlyData", [])
        return quarterly[:limit]
    except Exception as e:
        logger.error(f"Failed to fetch filings for {symbol}: {e}")
        return []


def _download_pdf(url: str) -> bytes | None:
    """Download a PDF from CDN."""
    try:
        resp = requests.get(url, timeout=60,
                            headers={"User-Agent": HEADERS["User-Agent"]})
        resp.raise_for_status()
        if "pdf" not in resp.headers.get("Content-Type", "").lower():
            return None
        return resp.content
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

def _build_dealing_alert(ticker: str, dealing: dict) -> str:
    """Build alert text for a significant director dealing."""
    name = dealing["director_name"]
    action = "bought" if dealing["deal_type"] == "buy" else "sold"
    qty = dealing["quantity"]

    qty_str = f"{qty:,}"
    if qty >= 1_000_000:
        qty_str = f"{qty/1_000_000:.1f}M"
    elif qty >= 1_000:
        qty_str = f"{qty/1_000:.0f}K"

    text = f"INSIDER: {ticker} director {name} {action} {qty_str} shares"
    if dealing.get("price"):
        text += f" at LKR {dealing['price']:.2f}"

    return text


# ---------------------------------------------------------------------------
# Main scrape
# ---------------------------------------------------------------------------

def scrape(bot=None, tickers: list[str] | None = None):
    """
    Scan quarterly reports for director dealings.
    If tickers is None, scans the top 50 most-traded stocks.
    """
    _init_tables()
    logger.info("Scanning quarterly reports for director dealings...")

    if tickers is None:
        # Default: scan top 50 by turnover
        try:
            from scripts.extract_annual_report import fetch_top_tickers
            tickers = fetch_top_tickers(50)
        except Exception:
            from utils.ticker_map import TICKER_TO_CSE
            tickers = sorted(TICKER_TO_CSE.keys())[:50]

    total_new = 0
    for ticker in tickers:
        symbol = f"{ticker}.N0000"
        quarterlies = _fetch_recent_quarterly_pdfs(symbol, limit=2)

        for q in quarterlies:
            pdf_id = q.get("id")
            if not pdf_id or _is_pdf_seen(pdf_id):
                continue

            path = q.get("path", "")
            if not path:
                _mark_pdf_seen(pdf_id, symbol)
                continue

            pdf_url = f"{CDN_URL}{path}"
            logger.info(f"Scanning {ticker} quarterly: {q.get('fileText', '')}")

            pdf_bytes = _download_pdf(pdf_url)
            if not pdf_bytes:
                _mark_pdf_seen(pdf_id, symbol)
                continue

            dealings = _extract_dealings_from_pdf(pdf_bytes, ticker)
            _mark_pdf_seen(pdf_id, symbol)

            for d in dealings:
                add_dealing(
                    ticker=ticker,
                    director_name=d["director_name"],
                    deal_type=d["deal_type"],
                    quantity=d["quantity"],
                    price=d.get("price"),
                    deal_date=d.get("deal_date"),
                    source_pdf=pdf_url,
                )
                total_new += 1

                # Alert for significant dealings (>100K shares or >LKR 5M value)
                value = (d["quantity"] * d["price"]) if d.get("price") else 0
                if d["quantity"] >= 100_000 or value >= 5_000_000:
                    if bot:
                        alert = _build_dealing_alert(ticker, d)
                        channel_id = os.getenv("FREE_CHANNEL_ID")
                        if channel_id:
                            try:
                                import asyncio
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    asyncio.ensure_future(
                                        bot.send_message(chat_id=channel_id, text=alert))
                                else:
                                    loop.run_until_complete(
                                        bot.send_message(chat_id=channel_id, text=alert))
                            except Exception as e:
                                logger.error(f"Failed to send dealing alert: {e}")

        time.sleep(1)  # Rate limit between companies

    logger.info(f"Director dealings scan complete: {total_new} new dealings found")
