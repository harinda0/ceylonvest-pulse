"""
Morning Brief Generator
Produces a daily 8:30 AM SLT market intelligence image card for the free Telegram channel.

Sections:
1. Market snapshot (ASPI / S&P SL20 with change arrows)
2. Trade summary (turnover, volume, trades)
3. Top 5 sentiment movers with mini bars
4. Velocity spikes / pump alerts
5. Key overnight headlines with source attribution
6. Disclaimer footer

Guards:
- Skips posting if DB has < 5 mentions (fresh Railway deploy)
- Skips posting if < 3 meaningful data points available

Runs as a scheduled job via APScheduler.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from io import BytesIO

from PIL import Image, ImageDraw

from services.cse_api import fetch_market_summary, SLT
from services.pulse_db import (
    get_top_sentiment_movers,
    get_most_mentioned,
    get_recent_headlines,
    get_mention_velocity,
    get_total_mentions,
)
from utils.ticker_map import get_company_name, TICKER_TO_CSE
from utils.card_generator import (
    _font, _rounded_rect, _draw_divider,
    BG, BG_CARD, BG_SURFACE, BG_ACCENT, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DIM,
    GREEN, GREEN_DIM, RED, RED_DIM, AMBER, BLUE, PURPLE,
    BRAND_ACCENT, ALERT_BG,
    FONT_BRAND, FONT_TICKER, FONT_COMPANY, FONT_PRICE, FONT_CHANGE,
    FONT_LABEL, FONT_VALUE, FONT_SECTION, FONT_SMALL, FONT_TINY, FONT_ALERT,
)

logger = logging.getLogger("pulse.morning_brief")

# Larger fonts for the brief header
FONT_BRIEF_TITLE = _font("InterDisplay-Bold.ttf", 28)
FONT_BRIEF_DATE = _font("Inter-Regular.ttf", 18)
FONT_INDEX_VALUE = _font("InterDisplay-Bold.ttf", 32)
FONT_INDEX_CHANGE = _font("Inter-SemiBold.ttf", 18)
FONT_INDEX_LABEL = _font("Inter-Medium.ttf", 14)
FONT_HEADLINE = _font("Inter-Regular.ttf", 16)
FONT_SOURCE = _font("Inter-Medium.ttf", 14)

WIDTH = 800
PAD = 32
INNER = WIDTH - 2 * PAD
SECTION_GAP = 22
MIN_DATA_POINTS = 3


# =========================================================================
# Data collection
# =========================================================================

def _collect_market_data() -> dict | None:
    """Fetch market indices and trade data."""
    data = fetch_market_summary()
    if not data:
        return None
    result = {}
    aspi = data.get("aspi")
    if aspi:
        result["aspi"] = {
            "value": float(aspi.get("value", 0)),
            "change": float(aspi.get("change", 0)),
            "pct": float(aspi.get("percentage", 0)),
        }
    snp = data.get("snp")
    if snp:
        result["snp"] = {
            "value": float(snp.get("value", 0)),
            "change": float(snp.get("change", 0)),
            "pct": float(snp.get("percentage", 0)),
        }
    trade_raw = data.get("trade")
    if trade_raw and isinstance(trade_raw, list) and trade_raw and isinstance(trade_raw[0], list) and trade_raw[0]:
        t = trade_raw[0][0]
        result["turnover"] = float(t.get("marketTurnover", 0))
        result["volume"] = float(t.get("volumeOfTurnOverNumber", 0))
        result["trades"] = int(t.get("marketTrades", 0))
    status = data.get("status")
    if status:
        result["status"] = status.get("status", "")
    return result if result else None


def _collect_movers(hours: int = 24) -> list[dict]:
    """Collect top sentiment movers."""
    movers = get_top_sentiment_movers(hours=hours, limit=5)
    result = []
    for m in movers:
        result.append({
            "ticker": m["ticker"],
            "name": get_company_name(m["ticker"]) or m["ticker"],
            "score": m["avg_score"],
            "count": m["count"],
        })
    return result


def _collect_alerts(hours: int = 24) -> list[dict]:
    """Collect velocity spikes and pump alerts."""
    alerts = []
    mentioned = get_most_mentioned(hours=hours, limit=20)
    for m in mentioned:
        ticker = m["ticker"]
        velocity = get_mention_velocity(ticker)
        if velocity["is_pump_alert"]:
            conc = velocity["concentration"]
            alerts.append({
                "type": "pump",
                "ticker": ticker,
                "velocity": velocity["velocity"],
                "source": conc.get("top_source", "unknown"),
                "pct": conc.get("max_pct", 0),
            })
        elif velocity["is_spike"]:
            alerts.append({
                "type": "spike",
                "ticker": ticker,
                "velocity": velocity["velocity"],
                "count": velocity["count_24h"],
                "avg": velocity["avg_daily_30d"],
            })
    return alerts


def _collect_headlines(hours: int = 24) -> list[dict]:
    """Collect deduplicated headlines."""
    raw = get_recent_headlines(hours=hours, limit=8)
    result = []
    seen = set()
    for h in raw:
        key = (h["content"] or "")[:80]
        if key in seen:
            continue
        seen.add(key)
        content = h["content"] or ""
        headline = content.split(" \u2014 ")[0][:100] if content else ""
        if not headline:
            continue
        result.append({
            "ticker": h["ticker"],
            "source": h["source_name"] or "Unknown",
            "headline": headline,
            "score": h["sentiment_score"],
        })
    return result[:6]


# =========================================================================
# Data quality gate
# =========================================================================

def _count_data_points(market, movers, alerts, headlines) -> int:
    """Count meaningful data points to decide if brief is worth posting."""
    count = 0
    if market and market.get("aspi"):
        count += 1
    if market and market.get("snp"):
        count += 1
    if market and market.get("turnover"):
        count += 1
    count += len(movers)
    count += len(alerts)
    count += len(headlines)
    return count


# =========================================================================
# Image generation
# =========================================================================

def _draw_brand_header(draw: ImageDraw.ImageDraw, y: int, date_str: str) -> int:
    """Draw the brand header bar with logo area and date."""
    # Top accent bar
    draw.rectangle([(0, 0), (WIDTH, 5)], fill=BRAND_ACCENT)

    # Brand name
    draw.text((PAD, y), "CEYLONVEST PULSE", fill=BRAND_ACCENT, font=FONT_BRAND)
    y += 26

    # Title and date
    draw.text((PAD, y), "Morning Brief", fill=TEXT_PRIMARY, font=FONT_BRIEF_TITLE)
    draw.text((WIDTH - PAD, y + 8), date_str, fill=TEXT_MUTED,
              font=FONT_BRIEF_DATE, anchor="rt")
    y += 40

    _draw_divider(draw, PAD, y, INNER)
    return y + 12


def _draw_index_card(draw: ImageDraw.ImageDraw, x: int, y: int, w: int,
                     label: str, value: float, change: float, pct: float) -> None:
    """Draw a single index card with value and change."""
    h = 90
    _rounded_rect(draw, (x, y, x + w, y + h), BG_SURFACE, radius=10)

    # Label
    draw.text((x + 16, y + 12), label, fill=TEXT_MUTED, font=FONT_INDEX_LABEL)

    # Value
    draw.text((x + 16, y + 30), f"{value:,.2f}", fill=TEXT_PRIMARY, font=FONT_INDEX_VALUE)

    # Change pill
    is_positive = change >= 0
    color = GREEN if is_positive else RED
    bg_color = GREEN_DIM if is_positive else RED_DIM
    sign = "+" if is_positive else ""
    arrow = "\u25b2" if is_positive else "\u25bc"
    change_text = f"{arrow} {sign}{change:,.2f} ({sign}{pct:.2f}%)"
    tw = draw.textlength(change_text, font=FONT_INDEX_CHANGE)
    pill_x = x + 16
    pill_y = y + 66
    _rounded_rect(draw, (pill_x, pill_y, pill_x + tw + 16, pill_y + 22), bg_color, radius=6)
    draw.text((pill_x + 8, pill_y + 1), change_text, fill=color, font=FONT_INDEX_CHANGE)


def _draw_trade_stats(draw: ImageDraw.ImageDraw, y: int, market: dict) -> int:
    """Draw turnover / volume / trades row."""
    box_w = (INNER - 16) // 3
    items = []
    turnover = market.get("turnover", 0)
    if turnover:
        if turnover >= 1e9:
            items.append(("TURNOVER", f"LKR {turnover/1e9:.1f}B"))
        elif turnover >= 1e6:
            items.append(("TURNOVER", f"LKR {turnover/1e6:.0f}M"))
    volume = market.get("volume", 0)
    if volume:
        if volume >= 1e6:
            items.append(("VOLUME", f"{volume/1e6:.1f}M shares"))
        else:
            items.append(("VOLUME", f"{volume:,.0f}"))
    trades = market.get("trades", 0)
    if trades:
        items.append(("TRADES", f"{trades:,}"))

    if not items:
        return y

    gap = 8
    bw = (INNER - gap * (len(items) - 1)) // len(items)
    for i, (label, val) in enumerate(items):
        bx = PAD + i * (bw + gap)
        _rounded_rect(draw, (bx, y, bx + bw, y + 52), BG_SURFACE, radius=8)
        draw.text((bx + 14, y + 8), label, fill=TEXT_MUTED, font=FONT_INDEX_LABEL)
        draw.text((bx + 14, y + 26), val, fill=TEXT_PRIMARY, font=FONT_SECTION)
    return y + 52 + SECTION_GAP


def _draw_movers_section(draw: ImageDraw.ImageDraw, y: int, movers: list[dict]) -> int:
    """Draw sentiment movers with mini horizontal bars."""
    draw.text((PAD, y), "TOP SENTIMENT MOVERS", fill=TEXT_MUTED, font=FONT_LABEL)
    y += 24

    for m in movers:
        ticker = m["ticker"]
        name = m["name"]
        score = m["score"]
        count = m["count"]

        # Ticker + name
        draw.text((PAD + 8, y), ticker, fill=TEXT_PRIMARY, font=FONT_SECTION)
        tw = draw.textlength(ticker, font=FONT_SECTION)
        # Truncate name to fit
        max_name_w = 280
        display_name = name
        while draw.textlength(display_name, font=FONT_SMALL) > max_name_w and len(display_name) > 5:
            display_name = display_name[:-2] + ".."
        draw.text((PAD + 8 + tw + 10, y + 2), display_name, fill=TEXT_MUTED, font=FONT_SMALL)

        # Score + direction label
        is_bullish = score > 0.05
        is_bearish = score < -0.05
        color = GREEN if is_bullish else RED if is_bearish else AMBER
        label = "Bullish" if is_bullish else "Bearish" if is_bearish else "Neutral"
        score_text = f"{score:+.2f} {label}"
        draw.text((WIDTH - PAD - 8, y + 2), score_text, fill=color,
                  font=FONT_SMALL, anchor="rt")

        y += 22

        # Mini sentiment bar
        bar_x = PAD + 8
        bar_w = INNER - 16
        bar_h = 6
        _rounded_rect(draw, (bar_x, y, bar_x + bar_w, y + bar_h), BG_ACCENT, radius=3)
        # Map score from [-1, 1] to [0, 1]
        fill_pct = (score + 1) / 2
        fill_w = max(4, int(bar_w * fill_pct))
        _rounded_rect(draw, (bar_x, y, bar_x + fill_w, y + bar_h), color, radius=3)

        # Mention count
        draw.text((WIDTH - PAD - 8, y - 1), f"{count} mentions",
                  fill=TEXT_DIM, font=FONT_TINY, anchor="rt")

        y += bar_h + 14

    return y + 4


def _draw_alerts_section(draw: ImageDraw.ImageDraw, y: int, alerts: list[dict]) -> int:
    """Draw pump/spike alerts."""
    draw.text((PAD, y), "ALERTS", fill=TEXT_MUTED, font=FONT_LABEL)
    y += 24

    for a in alerts:
        if a["type"] == "pump":
            # Red alert box
            _rounded_rect(draw, (PAD, y, WIDTH - PAD, y + 40), ALERT_BG, radius=8, outline=RED)
            draw.ellipse((PAD + 14, y + 15, PAD + 22, y + 23), fill=RED)
            draw.text((PAD + 30, y + 10), f"PUMP ALERT: {a['ticker']}", fill=RED, font=FONT_ALERT)
            detail = f"{a['velocity']}x velocity, {a['pct']:.0f}% from {a['source']}"
            draw.text((PAD + 30, y + 28), detail, fill=TEXT_SECONDARY, font=FONT_TINY)
            y += 48
        else:
            # Amber spike box
            _rounded_rect(draw, (PAD, y, WIDTH - PAD, y + 36), BG_SURFACE, radius=8, outline=AMBER)
            draw.text((PAD + 14, y + 9), f"SPIKE: {a['ticker']}", fill=AMBER, font=FONT_SECTION)
            detail = f"{a['velocity']}x above avg ({a['count']} mentions vs {a['avg']:.0f}/day)"
            dtw = draw.textlength(detail, font=FONT_TINY)
            draw.text((WIDTH - PAD - 14, y + 11), detail, fill=TEXT_MUTED,
                      font=FONT_TINY, anchor="rt")
            y += 44

    return y


def _draw_headlines_section(draw: ImageDraw.ImageDraw, y: int, headlines: list[dict]) -> int:
    """Draw headline rows with source attribution."""
    draw.text((PAD, y), "KEY HEADLINES", fill=TEXT_MUTED, font=FONT_LABEL)
    y += 24

    for h in headlines:
        # Source pill
        src = h["source"]
        stw = draw.textlength(src, font=FONT_SOURCE)
        _rounded_rect(draw, (PAD + 8, y, PAD + 8 + stw + 14, y + 20), BG_ACCENT, radius=5)
        draw.text((PAD + 15, y + 3), src, fill=BLUE, font=FONT_SOURCE)

        # Ticker
        tx = PAD + 8 + stw + 22
        draw.text((tx, y + 2), h["ticker"], fill=TEXT_SECONDARY, font=FONT_SOURCE)
        ttw = draw.textlength(h["ticker"], font=FONT_SOURCE)

        # Sentiment score pill (if available)
        if h["score"] is not None:
            sc = h["score"]
            sc_color = GREEN if sc > 0.1 else RED if sc < -0.1 else AMBER
            sc_text = f"{sc:+.2f}"
            sctw = draw.textlength(sc_text, font=FONT_TINY)
            sc_x = WIDTH - PAD - 8 - sctw - 10
            sc_bg = GREEN_DIM if sc > 0.1 else RED_DIM if sc < -0.1 else BG_ACCENT
            _rounded_rect(draw, (sc_x, y, sc_x + sctw + 10, y + 20), sc_bg, radius=5)
            draw.text((sc_x + 5, y + 3), sc_text, fill=sc_color, font=FONT_TINY)

        y += 24

        # Headline text (truncate if needed)
        headline = h["headline"]
        max_w = INNER - 24
        while draw.textlength(headline, font=FONT_HEADLINE) > max_w and len(headline) > 10:
            headline = headline[:-4] + "..."
        draw.text((PAD + 8, y), headline, fill=TEXT_SECONDARY, font=FONT_HEADLINE)
        y += 24

    return y


def _draw_footer(draw: ImageDraw.ImageDraw, y: int) -> int:
    """Draw disclaimer footer."""
    _draw_divider(draw, PAD, y, INNER, style="dots")
    y += 14
    draw.text((PAD, y), "ceylonvest.com", fill=TEXT_DIM, font=FONT_TINY)
    draw.text((WIDTH - PAD, y), "AI-powered market intelligence",
              fill=TEXT_DIM, font=FONT_TINY, anchor="rt")
    y += 18
    draw.text((PAD, y),
              "Not investment advice. Sentiment scores are AI-derived.",
              fill=TEXT_DIM, font=FONT_TINY)
    return y + 20


def generate_brief_image(hours: int = 24) -> BytesIO | None:
    """
    Generate the morning brief as a premium image card.

    Returns BytesIO with PNG data, or None if not enough data to post.
    """
    # Gate 1: Check DB has enough data
    total = get_total_mentions()
    if total < 5:
        logger.info(f"Not enough data for morning brief yet ({total} mentions in DB)")
        return None

    # Collect all data
    market = _collect_market_data()
    movers = _collect_movers(hours=hours)
    alerts = _collect_alerts(hours=hours)
    headlines = _collect_headlines(hours=hours)

    # Gate 2: Need at least MIN_DATA_POINTS meaningful items
    dp = _count_data_points(market, movers, alerts, headlines)
    if dp < MIN_DATA_POINTS:
        logger.info(f"Only {dp} data points for morning brief (need {MIN_DATA_POINTS}) — skipping")
        return None

    now_slt = datetime.now(SLT)
    date_str = now_slt.strftime("%A, %d %B %Y")

    # --- Calculate height ---
    h = 30  # top padding
    h += 80  # brand header
    h += 12

    has_market = market and (market.get("aspi") or market.get("snp"))
    has_trade = market and market.get("turnover")
    has_movers = len(movers) > 0
    has_alerts = len(alerts) > 0
    has_headlines = len(headlines) > 0

    if has_market:
        h += 90 + SECTION_GAP  # index cards
    if has_trade:
        h += 52 + SECTION_GAP  # trade stats
    if has_movers:
        h += 24  # section label
        h += len(movers) * 46  # each mover row
        h += SECTION_GAP
    if has_alerts:
        h += 24  # section label
        for a in alerts:
            h += 48 if a["type"] == "pump" else 44
        h += SECTION_GAP
    if has_headlines:
        h += 24  # section label
        h += len(headlines) * 48  # each headline
        h += SECTION_GAP
    h += 60  # footer

    # --- Draw ---
    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    # Brand header
    y = _draw_brand_header(draw, y, date_str)

    # Market indices
    if has_market:
        cards = []
        if market.get("aspi"):
            a = market["aspi"]
            cards.append(("ALL SHARE PRICE INDEX", a["value"], a["change"], a["pct"]))
        if market.get("snp"):
            s = market["snp"]
            cards.append(("S&P SL20", s["value"], s["change"], s["pct"]))

        if len(cards) == 2:
            card_w = (INNER - 12) // 2
            _draw_index_card(draw, PAD, y, card_w, *cards[0])
            _draw_index_card(draw, PAD + card_w + 12, y, card_w, *cards[1])
        elif len(cards) == 1:
            _draw_index_card(draw, PAD, y, INNER, *cards[0])
        y += 90 + SECTION_GAP

    # Trade stats
    if has_trade:
        y = _draw_trade_stats(draw, y, market)

    # Movers
    if has_movers:
        _draw_divider(draw, PAD, y, INNER)
        y += 12
        y = _draw_movers_section(draw, y, movers)
        y += SECTION_GAP // 2

    # Alerts
    if has_alerts:
        _draw_divider(draw, PAD, y, INNER)
        y += 12
        y = _draw_alerts_section(draw, y, alerts)
        y += SECTION_GAP // 2

    # Headlines
    if has_headlines:
        _draw_divider(draw, PAD, y, INNER)
        y += 12
        y = _draw_headlines_section(draw, y, headlines)
        y += SECTION_GAP // 2

    # Footer
    y += 4
    actual_h = _draw_footer(draw, y)

    # Crop to actual height
    img = img.crop((0, 0, WIDTH, actual_h))

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


def generate_brief(hours: int = 24) -> str:
    """
    Generate a plain-text fallback brief (used by /brief admin command).

    Returns formatted text string.
    """
    now_slt = datetime.now(SLT)
    date_str = now_slt.strftime("%A, %d %B %Y")

    market = _collect_market_data()
    movers = _collect_movers(hours=hours)
    headlines = _collect_headlines(hours=hours)

    brief = f"CeylonVest Pulse — Morning Brief\n"
    brief += f"{date_str}\n\n"

    # Market
    brief += "Market Snapshot\n"
    if market:
        if market.get("aspi"):
            a = market["aspi"]
            sign = "+" if a["change"] >= 0 else ""
            brief += f"  ASPI: {a['value']:,.2f} ({sign}{a['change']:,.2f} / {sign}{a['pct']:.2f}%)\n"
        if market.get("snp"):
            s = market["snp"]
            sign = "+" if s["change"] >= 0 else ""
            brief += f"  S&P SL20: {s['value']:,.2f} ({sign}{s['change']:,.2f} / {sign}{s['pct']:.2f}%)\n"
        turnover = market.get("turnover", 0)
        if turnover >= 1e9:
            brief += f"  Turnover: LKR {turnover/1e9:.1f}B\n"
        elif turnover >= 1e6:
            brief += f"  Turnover: LKR {turnover/1e6:.0f}M\n"
    else:
        brief += "  Market data unavailable.\n"
    brief += "\n"

    # Movers
    brief += "Top Sentiment Movers (24h)\n"
    if movers:
        for m in movers:
            direction = "Bullish" if m["score"] > 0.05 else "Bearish" if m["score"] < -0.05 else "Neutral"
            brief += f"  {m['ticker']} ({m['name']}): {m['score']:+.2f} {direction} ({m['count']} mentions)\n"
    else:
        brief += "  No sentiment data yet.\n"
    brief += "\n"

    # Headlines
    brief += "Key Headlines\n"
    if headlines:
        for h in headlines:
            brief += f"  [{h['source']}] {h['ticker']}: {h['headline']}\n"
    else:
        brief += "  No recent headlines.\n"
    brief += "\n"

    brief += (
        "---\n"
        "AI-generated market intelligence. Not investment advice.\n"
        "Sentiment scores are AI-derived from news and social media."
    )

    return brief


async def send_morning_brief(bot) -> bool:
    """
    Send the morning brief image to the free Telegram channel.

    Guards:
    - Skips if PULSE_FREE_CHANNEL_ID not set
    - Skips if DB has < 5 mentions (fresh deploy)
    - Skips if < 3 meaningful data points

    Returns True if sent, False if skipped/failed.
    """
    channel_id = os.getenv("PULSE_FREE_CHANNEL_ID")
    if not channel_id:
        logger.warning("PULSE_FREE_CHANNEL_ID not set — skipping morning brief")
        return False

    try:
        img_buf = generate_brief_image()
        if img_buf is None:
            # Guards triggered — already logged the reason
            return False

        await bot.send_photo(
            chat_id=channel_id,
            photo=img_buf,
            caption="CeylonVest Pulse — Morning Brief\nAI-generated market intelligence. Not investment advice.",
        )
        logger.info("Morning brief image sent to free channel")
        return True
    except Exception as e:
        logger.error(f"Failed to send morning brief: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")

    # Preview: generate and save locally
    buf = generate_brief_image()
    if buf:
        with open("morning_brief_preview.png", "wb") as f:
            f.write(buf.getvalue())
        print("Saved morning_brief_preview.png")
    else:
        print("Brief skipped (not enough data)")
        # Fall back to text preview
        print(generate_brief())
