"""
Morning Brief Generator
Produces a daily 8:30 AM SLT market intelligence summary for the free Telegram channel.

Sections:
1. Market snapshot (ASPI / S&P SL20 from CSE API)
2. Top 5 sentiment movers (strongest bullish/bearish signals)
3. Most mentioned tickers (buzz leaders)
4. Velocity spikes / pump alerts
5. Key overnight headlines from RSS feeds

Runs as a scheduled job via APScheduler.
"""

import os
import logging
from datetime import datetime, timezone, timedelta

from services.cse_api import fetch_market_summary, SLT
from services.pulse_db import (
    get_top_sentiment_movers,
    get_most_mentioned,
    get_recent_headlines,
    get_mention_velocity,
)
from utils.ticker_map import get_company_name, TICKER_TO_CSE

logger = logging.getLogger("pulse.morning_brief")


def _sentiment_bar(score: float) -> str:
    """Visual bar for sentiment score: -1.0 to +1.0 → emoji bar."""
    if score >= 0.5:
        return "++++"
    elif score >= 0.2:
        return "+++"
    elif score >= 0.05:
        return "++"
    elif score > -0.05:
        return "~"
    elif score > -0.2:
        return "--"
    elif score > -0.5:
        return "---"
    else:
        return "----"


def _format_market_section() -> str:
    """Section 1: Market indices snapshot."""
    data = fetch_market_summary()
    if not data:
        return "Market data unavailable.\n"

    lines = []

    # ASPI
    aspi = data.get("aspi")
    if aspi:
        val = float(aspi.get("value", aspi.get("indexValue", 0)))
        chg = float(aspi.get("change", 0))
        pct = float(aspi.get("percentage", aspi.get("changePercentage", 0)))
        sign = "+" if chg >= 0 else ""
        lines.append(f"  ASPI: {val:,.2f} ({sign}{chg:,.2f} / {sign}{pct:.2f}%)")

    # S&P SL20
    snp = data.get("snp")
    if snp:
        val = float(snp.get("value", snp.get("indexValue", 0)))
        chg = float(snp.get("change", 0))
        pct = float(snp.get("percentage", snp.get("changePercentage", 0)))
        sign = "+" if chg >= 0 else ""
        lines.append(f"  S&P SL20: {val:,.2f} ({sign}{chg:,.2f} / {sign}{pct:.2f}%)")

    # Trade summary (dailyMarketSummery returns list of lists)
    trade = data.get("trade")
    if trade and isinstance(trade, list) and trade and isinstance(trade[0], list) and trade[0]:
        t = trade[0][0]  # First entry of first list
        turnover = float(t.get("marketTurnover", 0))
        if turnover >= 1e9:
            lines.append(f"  Turnover: LKR {turnover/1e9:.1f}B")
        elif turnover >= 1e6:
            lines.append(f"  Turnover: LKR {turnover/1e6:.1f}M")

    return "\n".join(lines) + "\n" if lines else "Market data unavailable.\n"


def _format_sentiment_section(hours: int = 24) -> str:
    """Section 2: Top sentiment movers."""
    movers = get_top_sentiment_movers(hours=hours, limit=5)
    if not movers:
        return "  No sentiment data yet.\n"

    lines = []
    for m in movers:
        ticker = m["ticker"]
        score = m["avg_score"]
        count = m["count"]
        name = get_company_name(ticker) or ticker
        bar = _sentiment_bar(score)
        direction = "Bullish" if score > 0.05 else "Bearish" if score < -0.05 else "Neutral"
        lines.append(f"  {ticker} ({name}): {score:+.2f} [{bar}] {direction} ({count} mentions)")

    return "\n".join(lines) + "\n"


def _format_buzz_section(hours: int = 24) -> str:
    """Section 3: Most mentioned tickers."""
    mentioned = get_most_mentioned(hours=hours, limit=5)
    if not mentioned:
        return "  No mentions yet.\n"

    lines = []
    for m in mentioned:
        ticker = m["ticker"]
        count = m["count"]
        name = get_company_name(ticker) or ticker
        lines.append(f"  {ticker} ({name}): {count} mentions")

    return "\n".join(lines) + "\n"


def _format_alerts_section(hours: int = 24) -> str:
    """Section 4: Velocity spikes and pump alerts."""
    alerts = []

    # Check all tickers that have mentions in the last 24h
    mentioned = get_most_mentioned(hours=hours, limit=20)
    for m in mentioned:
        ticker = m["ticker"]
        velocity = get_mention_velocity(ticker)

        if velocity["is_pump_alert"]:
            conc = velocity["concentration"]
            top = conc.get("top_source", "unknown")
            pct = conc.get("max_pct", 0)
            alerts.append(
                f"  PUMP ALERT: {ticker} — {velocity['velocity']}x velocity, "
                f"{pct:.0f}% from {top}"
            )
        elif velocity["is_spike"]:
            alerts.append(
                f"  SPIKE: {ticker} — {velocity['velocity']}x above 30d average "
                f"({velocity['count_24h']} mentions vs {velocity['avg_daily_30d']}/day avg)"
            )

    if not alerts:
        return "  No unusual activity detected.\n"

    return "\n".join(alerts) + "\n"


def _format_headlines_section(hours: int = 24) -> str:
    """Section 5: Key overnight headlines."""
    headlines = get_recent_headlines(hours=hours, limit=8)
    if not headlines:
        return "  No recent headlines.\n"

    lines = []
    seen_content = set()
    for h in headlines:
        # Deduplicate by first 80 chars of content (same article, different tickers)
        key = (h["content"] or "")[:80]
        if key in seen_content:
            continue
        seen_content.add(key)

        ticker = h["ticker"]
        source = h["source_name"] or "Unknown"
        # Extract just the headline (before the " — " separator added by news_scraper)
        content = h["content"] or ""
        headline = content.split(" — ")[0][:120] if content else "No headline"

        score_str = ""
        if h["sentiment_score"] is not None:
            score_str = f" [{h['sentiment_score']:+.2f}]"

        lines.append(f"  [{source}] {ticker}: {headline}{score_str}")

    return "\n".join(lines) + "\n"


def generate_brief(hours: int = 24) -> str:
    """
    Generate the full morning brief text.

    Args:
        hours: Look-back window for data (default 24h).

    Returns:
        Formatted text string ready to send via Telegram.
    """
    now_slt = datetime.now(SLT)
    date_str = now_slt.strftime("%A, %d %B %Y")

    brief = f"CeylonVest Pulse — Morning Brief\n"
    brief += f"{date_str}\n\n"

    # 1. Market snapshot
    brief += "Market Snapshot\n"
    brief += _format_market_section()
    brief += "\n"

    # 2. Sentiment movers
    brief += "Top Sentiment Movers (24h)\n"
    brief += _format_sentiment_section(hours=hours)
    brief += "\n"

    # 3. Buzz leaders
    brief += "Most Mentioned\n"
    brief += _format_buzz_section(hours=hours)
    brief += "\n"

    # 4. Alerts
    brief += "Alerts\n"
    brief += _format_alerts_section(hours=hours)
    brief += "\n"

    # 5. Headlines
    brief += "Key Headlines\n"
    brief += _format_headlines_section(hours=hours)
    brief += "\n"

    # Disclaimer
    brief += (
        "---\n"
        "AI-generated market intelligence. Not investment advice.\n"
        "Sentiment scores are AI-derived from news and social media.\n"
        "Data from CSE, EconomyNext, Ada Derana Biz, NewsWire."
    )

    return brief


async def send_morning_brief(bot) -> bool:
    """
    Send the morning brief to the free Telegram channel.

    Args:
        bot: telegram.Bot instance.

    Returns:
        True if sent successfully, False otherwise.
    """
    channel_id = os.getenv("PULSE_FREE_CHANNEL_ID")
    if not channel_id:
        logger.warning("PULSE_FREE_CHANNEL_ID not set — skipping morning brief")
        return False

    try:
        brief = generate_brief()
        await bot.send_message(
            chat_id=channel_id,
            text=brief,
            parse_mode=None,  # Plain text — no markdown parsing issues
        )
        logger.info("Morning brief sent to free channel")
        return True
    except Exception as e:
        logger.error(f"Failed to send morning brief: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")

    brief = generate_brief()
    print(brief)
