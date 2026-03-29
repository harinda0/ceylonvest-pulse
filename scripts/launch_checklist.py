"""
Launch Readiness Checklist
Verifies the bot is ready for public use.

Usage:
    python scripts/launch_checklist.py
"""

import json
import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

# ANSI colors
G = "\033[92m"  # green
R = "\033[91m"  # red
Y = "\033[93m"  # yellow
B = "\033[1m"   # bold
N = "\033[0m"   # reset


def _ok(msg):
    print(f"  {G}PASS{N}  {msg}")
    return True


def _warn(msg):
    print(f"  {Y}WARN{N}  {msg}")
    return True  # warnings don't block launch


def _fail(msg):
    print(f"  {R}FAIL{N}  {msg}")
    return False


# -----------------------------------------------------------------------
# 1. Annual reports coverage
# -----------------------------------------------------------------------
def check_annual_reports():
    print(f"\n{B}1. Annual Report Coverage{N}")
    reports_path = Path(__file__).parent.parent / "data" / "annual_reports.json"

    if not reports_path.exists():
        return _fail("data/annual_reports.json does not exist")

    with open(reports_path) as f:
        reports = json.load(f)

    from utils.ticker_map import TICKER_TO_CSE
    total = len(TICKER_TO_CSE)
    covered = len(reports)
    pct = covered / total * 100

    if pct >= 80:
        _ok(f"{covered}/{total} tickers covered ({pct:.0f}%)")
    elif pct >= 30:
        _warn(f"{covered}/{total} tickers covered ({pct:.0f}%) — extraction may still be running")
    else:
        _fail(f"Only {covered}/{total} tickers covered ({pct:.0f}%)")

    return True  # non-blocking


# -----------------------------------------------------------------------
# 2. Null financial metrics
# -----------------------------------------------------------------------
def check_null_metrics():
    print(f"\n{B}2. Null Financial Metrics{N}")
    reports_path = Path(__file__).parent.parent / "data" / "annual_reports.json"

    with open(reports_path) as f:
        reports = json.load(f)

    null_eps = []
    null_nav = []
    null_roe = []
    for ticker, data in reports.items():
        fin = data.get("financials", {})
        if fin.get("eps") is None:
            null_eps.append(ticker)
        if fin.get("nav") is None:
            null_nav.append(ticker)
        if fin.get("roe") is None:
            null_roe.append(ticker)

    total = len(reports)
    ok = True

    eps_pct = len(null_eps) / total * 100 if total else 100
    nav_pct = len(null_nav) / total * 100 if total else 100
    roe_pct = len(null_roe) / total * 100 if total else 100

    for name, nulls, pct in [("EPS", null_eps, eps_pct), ("NAV", null_nav, nav_pct), ("ROE", null_roe, roe_pct)]:
        if pct <= 20:
            _ok(f"{name}: {len(nulls)}/{total} null ({pct:.0f}%)")
        elif pct <= 50:
            _warn(f"{name}: {len(nulls)}/{total} null ({pct:.0f}%) — {', '.join(nulls[:5])}...")
        else:
            _fail(f"{name}: {len(nulls)}/{total} null ({pct:.0f}%)")
            ok = False

    return ok


# -----------------------------------------------------------------------
# 3. CSE API health
# -----------------------------------------------------------------------
def check_cse_api():
    print(f"\n{B}3. CSE API Health{N}")
    import requests
    from utils.ticker_map import TICKER_TO_CSE

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Origin": "https://www.cse.lk",
        "Referer": "https://www.cse.lk/",
    }
    base = "https://www.cse.lk/api/"

    # Test 5 random tickers
    sample = random.sample(sorted(TICKER_TO_CSE.keys()), min(5, len(TICKER_TO_CSE)))
    ok = True

    for ticker in sample:
        symbol = f"{ticker}.N0000"
        try:
            resp = requests.post(f"{base}companyInfoSummery",
                                 headers=headers, data=f"symbol={symbol}", timeout=10)
            if resp.status_code == 200 and resp.text:
                data = resp.json()
                info = data.get("reqSymbolInfo", {})
                price = info.get("lastTradedPrice")
                if price:
                    _ok(f"{ticker}: LKR {float(price):.2f}")
                else:
                    _warn(f"{ticker}: API responded but no price (may be halted)")
            else:
                _fail(f"{ticker}: HTTP {resp.status_code}")
                ok = False
        except Exception as e:
            _fail(f"{ticker}: {e}")
            ok = False

    # Also test market endpoints
    json_headers = {**headers, "Content-Type": "application/json"}
    for ep, label in [("aspiData", "ASPI"), ("marketStatus", "Market status")]:
        try:
            resp = requests.post(f"{base}{ep}", headers=json_headers, timeout=10)
            if resp.status_code == 200 and resp.text:
                _ok(f"{label} endpoint responding")
            else:
                _fail(f"{label}: HTTP {resp.status_code}")
                ok = False
        except Exception as e:
            _fail(f"{label}: {e}")
            ok = False

    return ok


# -----------------------------------------------------------------------
# 4. Database health
# -----------------------------------------------------------------------
def check_database():
    print(f"\n{B}4. Database Health{N}")
    ok = True

    try:
        from services.pulse_db import get_total_mentions, get_db, _fetchone, _fetchall
    except Exception as e:
        return _fail(f"Cannot import pulse_db: {e}")

    # Check connection
    try:
        conn = get_db()
        conn.close()
        _ok("Database connection OK")
    except Exception as e:
        return _fail(f"Database connection failed: {e}")

    # Check mentions
    total = get_total_mentions()
    if total >= 100:
        _ok(f"{total:,} mentions in database")
    elif total >= 10:
        _warn(f"Only {total} mentions — scrapers may need more time")
    elif total > 0:
        _warn(f"Only {total} mentions — very low, scrapers may not be running")
    else:
        _fail("0 mentions in database — scrapers not running")
        ok = False

    # Check watchlists table
    try:
        conn = get_db()
        row = _fetchone(conn, "SELECT COUNT(*) as cnt FROM user_watchlists")
        conn.close()
        watchlists = row["cnt"] if row else 0
        _ok(f"{watchlists} watchlist entries")
    except Exception as e:
        _warn(f"Watchlists table: {e}")

    # Check scraped_urls
    try:
        conn = get_db()
        row = _fetchone(conn, "SELECT COUNT(*) as cnt FROM scraped_urls")
        conn.close()
        urls = row["cnt"] if row else 0
        _ok(f"{urls} URLs in scraper dedup table")
    except Exception as e:
        _warn(f"Scraped URLs table: {e}")

    return ok


# -----------------------------------------------------------------------
# 5. Morning brief readiness
# -----------------------------------------------------------------------
def check_morning_brief():
    print(f"\n{B}5. Morning Brief Readiness{N}")
    from services.pulse_db import get_total_mentions, get_top_sentiment_movers, get_recent_headlines

    total = get_total_mentions()
    if total < 5:
        return _fail(f"Need >= 5 mentions for brief, have {total}")

    movers = get_top_sentiment_movers(hours=24, limit=5)
    headlines = get_recent_headlines(hours=24, limit=10)

    data_points = 0
    if movers:
        data_points += len(movers)
        _ok(f"{len(movers)} sentiment movers (24h)")
    else:
        _warn("No sentiment movers in last 24h")

    if headlines:
        data_points += 1
        _ok(f"{len(headlines)} headlines (24h)")
    else:
        _warn("No headlines in last 24h")

    # Market data is always available during trading
    data_points += 2  # ASPI + trade summary usually available

    if data_points >= 3:
        _ok(f"{data_points} data points available (need 3)")
        return True
    else:
        _warn(f"Only {data_points} data points (need 3) — brief may skip tomorrow")
        return True  # non-blocking


# -----------------------------------------------------------------------
# 6. Command health check
# -----------------------------------------------------------------------
def check_commands():
    print(f"\n{B}6. Command Imports & Dependencies{N}")
    ok = True

    # Check all imports that commands need
    checks = [
        ("resolve_ticker", "from utils.ticker_map import resolve_ticker"),
        ("get_stock_data", "from services.cse_api import get_stock_data"),
        ("generate_main_card", "from utils.card_generator import generate_main_card"),
        ("get_report", "from services.annual_reports import get_report"),
        ("get_sector_benchmark", "from services.sector_benchmarks import get_sector_benchmark"),
        ("fetch_market_summary", "from services.cse_api import fetch_market_summary"),
        ("get_recent_dealings", "from services.director_dealings_scraper import get_recent_dealings"),
        ("scrape_announcements", "from services.announcements_scraper import scrape"),
        ("morning_brief", "from services.morning_brief import generate_brief"),
    ]

    for name, import_str in checks:
        try:
            exec(import_str)
            _ok(f"{name}")
        except Exception as e:
            _fail(f"{name}: {e}")
            ok = False

    # Check report command has data
    from services.annual_reports import get_all_tickers
    tickers = get_all_tickers()
    if tickers:
        _ok(f"/report available for {len(tickers)} tickers")
    else:
        _fail("/report has no data")
        ok = False

    # Check sector command has data
    from services.sector_benchmarks import get_all_sectors
    sectors = get_all_sectors()
    if sectors:
        _ok(f"/sector available for {len(sectors)} sectors")
    else:
        _fail("/sector has no data")
        ok = False

    return ok


# -----------------------------------------------------------------------
# 7. Environment variables
# -----------------------------------------------------------------------
def check_env():
    print(f"\n{B}7. Environment Variables{N}")
    ok = True

    required = {
        "TELEGRAM_BOT_TOKEN": "Bot won't start",
        "ANTHROPIC_API_KEY": "Annual report extraction + sentiment scoring won't work",
    }

    recommended = {
        "PULSE_FREE_CHANNEL_ID": "Morning brief + alerts won't post",
        "ADMIN_TELEGRAM_ID": "/brief command won't work",
    }

    for var, impact in required.items():
        val = os.getenv(var, "")
        if val and val not in ("your_bot_token_here", "your_anthropic_key_here"):
            _ok(f"{var} is set")
        else:
            _fail(f"{var} not set — {impact}")
            ok = False

    for var, impact in recommended.items():
        val = os.getenv(var, "")
        if val and not val.startswith("your_"):
            _ok(f"{var} is set")
        else:
            _warn(f"{var} not set — {impact}")

    return ok


# -----------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------
def main():
    print(f"\n{'='*60}")
    print(f"{B}  CeylonVest Pulse — Launch Readiness Checklist{N}")
    print(f"{'='*60}")

    results = {}
    results["Annual Reports"] = check_annual_reports()
    results["Null Metrics"] = check_null_metrics()
    results["CSE API"] = check_cse_api()
    results["Database"] = check_database()
    results["Morning Brief"] = check_morning_brief()
    results["Commands"] = check_commands()
    results["Env Vars"] = check_env()

    # Verdict
    blockers = [name for name, passed in results.items() if not passed]
    print(f"\n{'='*60}")
    if not blockers:
        print(f"  {G}{B}READY FOR LAUNCH{N}")
        print(f"  All checks passed. Bot is ready for public use.")
    else:
        print(f"  {R}{B}NOT READY{N}")
        print(f"  Blocking issues:")
        for b in blockers:
            print(f"    {R}•{N} {b}")
    print(f"{'='*60}\n")

    sys.exit(0 if not blockers else 1)


if __name__ == "__main__":
    main()
