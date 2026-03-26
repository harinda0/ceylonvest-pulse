"""
CeylonVest Pulse Card Generator
Generates BonkBot-style ticker info cards as images for Telegram.
Uses Pillow to create dark-themed, data-dense cards.
"""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from dataclasses import dataclass
from typing import Optional


# Color palette (dark theme matching TG dark mode)
BG = (26, 26, 46)         # #1a1a2e
BG_CARD = (34, 34, 58)    # #22223a
BG_ACCENT = (42, 42, 74)  # #2a2a4a
TEXT_PRIMARY = (255, 255, 255)
TEXT_SECONDARY = (155, 155, 190)  # #9a9abe
TEXT_MUTED = (122, 122, 154)     # #7a7a9a
GREEN = (93, 202, 165)    # #5dcaa5
RED = (226, 75, 74)       # #e24b4a
AMBER = (239, 159, 39)    # #ef9f27
BLUE = (55, 138, 221)     # #378add
PURPLE = (127, 119, 221)  # #7f77dd
ALERT_BG = (58, 26, 26)   # #3a1a1a


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load font with fallback."""
    # Try common system fonts, fall back to default
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# Pre-load fonts
FONT_BRAND = _get_font(14, bold=True)
FONT_TICKER = _get_font(28, bold=True)
FONT_COMPANY = _get_font(14)
FONT_PRICE = _get_font(32, bold=True)
FONT_CHANGE = _get_font(16, bold=True)
FONT_METRIC_LABEL = _get_font(12)
FONT_METRIC_VALUE = _get_font(16, bold=True)
FONT_SECTION = _get_font(14, bold=True)
FONT_SMALL = _get_font(12)
FONT_ALERT = _get_font(13, bold=True)
FONT_ALERT_TEXT = _get_font(12)


def _format_number(n: float | int | None, prefix: str = "", suffix: str = "") -> str:
    """Format a number with K/M/B suffixes."""
    if n is None:
        return "N/A"
    if isinstance(n, (int, float)):
        if abs(n) >= 1_000_000_000:
            return f"{prefix}{n / 1_000_000_000:.1f}B{suffix}"
        elif abs(n) >= 1_000_000:
            return f"{prefix}{n / 1_000_000:.1f}M{suffix}"
        elif abs(n) >= 1_000:
            return f"{prefix}{n / 1_000:.0f}K{suffix}"
        else:
            return f"{prefix}{n:.2f}{suffix}"
    return str(n)


def _draw_rounded_rect(draw, xy, fill, radius=8):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def _change_color(val: float | None) -> tuple:
    """Color based on positive/negative value."""
    if val is None:
        return TEXT_MUTED
    return GREEN if val >= 0 else RED


def _draw_metric_box(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
                     label: str, value: str, value_color=TEXT_PRIMARY):
    """Draw a small metric box with label and value."""
    _draw_rounded_rect(draw, (x, y, x + w, y + h), BG_CARD, radius=6)
    draw.text((x + 8, y + 8), label, fill=TEXT_MUTED, font=FONT_SMALL)
    draw.text((x + 8, y + 26), value, fill=value_color, font=FONT_METRIC_VALUE)


def generate_main_card(
    ticker: str,
    company_name: str,
    sector: str,
    last_price: float,
    change: float,
    change_pct: float,
    market_cap: float,
    volume: int,
    pe_ratio: float | None,
    spread_pct: float | None,
    change_7d: float | None,
    change_30d: float | None,
    change_90d: float | None,
    sentiment_score: float | None,
    mention_count_24h: int,
    mention_velocity: float,
    is_pump_alert: bool = False,
    pump_alert_text: str = "",
) -> BytesIO:
    """
    Generate the main ticker card image.
    Returns a BytesIO object containing the PNG image.
    """
    # Card dimensions
    WIDTH = 520
    PADDING = 20
    INNER_W = WIDTH - 2 * PADDING

    # Determine which optional sections to show
    has_price_changes = any(v is not None for v in [change_7d, change_30d, change_90d])
    has_pe = pe_ratio is not None

    # Calculate height dynamically
    height = 20  # top padding
    height += 50  # header (brand + ticker)
    height += 50  # price
    height += 60  # metric boxes row 1
    if has_price_changes:
        height += 50  # price change row
    height += 16  # spacer
    height += 80  # sentiment section
    if is_pump_alert:
        height += 50  # pump alert
    height += 20  # bottom padding

    img = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(img)

    y = 16

    # === HEADER ===
    draw.text((PADDING, y), "CEYLONVEST PULSE", fill=TEXT_MUTED, font=FONT_BRAND)

    # Sector badge (right aligned)
    sector_text = sector
    sector_w = draw.textlength(sector_text, font=FONT_SMALL) + 16
    _draw_rounded_rect(
        draw,
        (WIDTH - PADDING - sector_w, y - 2, WIDTH - PADDING, y + 18),
        BG_ACCENT, radius=10,
    )
    draw.text(
        (WIDTH - PADDING - sector_w + 8, y),
        sector_text, fill=TEXT_SECONDARY, font=FONT_SMALL,
    )

    y += 26

    # Ticker + company name
    draw.text((PADDING, y), ticker, fill=TEXT_PRIMARY, font=FONT_TICKER)
    ticker_w = draw.textlength(ticker, font=FONT_TICKER)
    draw.text(
        (PADDING + ticker_w + 10, y + 10),
        company_name, fill=TEXT_MUTED, font=FONT_COMPANY,
    )
    y += 42

    # === PRICE ===
    price_text = f"LKR {last_price:,.2f}"
    draw.text((PADDING, y), price_text, fill=TEXT_PRIMARY, font=FONT_PRICE)

    price_w = draw.textlength(price_text, font=FONT_PRICE)
    sign = "+" if change >= 0 else ""
    change_text = f"{sign}{change:.2f} ({sign}{change_pct:.2f}%)"
    draw.text(
        (PADDING + price_w + 12, y + 10),
        change_text,
        fill=_change_color(change),
        font=FONT_CHANGE,
    )
    y += 48

    # === METRIC BOXES ROW 1 ===
    # Show 3 or 4 boxes depending on whether P/E is available
    if has_pe:
        box_w = (INNER_W - 18) // 4  # 4 boxes, 3 gaps of 6px
        _draw_metric_box(draw, PADDING, y, box_w, 48, "Mkt cap", _format_number(market_cap))
        _draw_metric_box(draw, PADDING + box_w + 6, y, box_w, 48, "Volume", _format_number(volume))
        _draw_metric_box(
            draw, PADDING + 2 * (box_w + 6), y, box_w, 48, "P/E",
            f"{pe_ratio:.1f}x",
        )
        _draw_metric_box(
            draw, PADDING + 3 * (box_w + 6), y, box_w, 48, "Spread",
            f"{spread_pct:.1f}%" if spread_pct else "N/A",
        )
    else:
        box_w = (INNER_W - 12) // 3  # 3 boxes, 2 gaps of 6px
        _draw_metric_box(draw, PADDING, y, box_w, 48, "Mkt cap", _format_number(market_cap))
        _draw_metric_box(draw, PADDING + box_w + 6, y, box_w, 48, "Volume", _format_number(volume))
        _draw_metric_box(
            draw, PADDING + 2 * (box_w + 6), y, box_w, 48, "Spread",
            f"{spread_pct:.1f}%" if spread_pct else "N/A",
        )
    y += 58

    # === PRICE CHANGE ROW (only if we have data) ===
    if has_price_changes:
        box3_w = (INNER_W - 12) // 3
        for i, (label, val) in enumerate([("7d", change_7d), ("30d", change_30d), ("90d", change_90d)]):
            bx = PADDING + i * (box3_w + 6)
            _draw_rounded_rect(draw, (bx, y, bx + box3_w, y + 42), BG_CARD, radius=6)
            draw.text(
                (bx + box3_w // 2, y + 6), label,
                fill=TEXT_MUTED, font=FONT_SMALL, anchor="mt",
            )
            val_text = f"{val:+.1f}%" if val is not None else "N/A"
            draw.text(
                (bx + box3_w // 2, y + 24), val_text,
                fill=_change_color(val), font=FONT_METRIC_VALUE, anchor="mt",
            )
        y += 52

    # === DIVIDER ===
    draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill=BG_ACCENT, width=1)
    y += 12

    # === SENTIMENT SECTION ===
    draw.text((PADDING, y), "Pulse sentiment", fill=TEXT_SECONDARY, font=FONT_SECTION)

    # Sentiment score (right aligned)
    if sentiment_score is not None:
        score_text = f"{sentiment_score:+.2f}"
        score_color = GREEN if sentiment_score > 0.1 else RED if sentiment_score < -0.1 else AMBER
        draw.text(
            (WIDTH - PADDING, y), score_text,
            fill=score_color, font=FONT_SECTION, anchor="rt",
        )
    y += 22

    # Sentiment bar
    bar_x = PADDING
    bar_w = INNER_W - 80
    bar_h = 6
    _draw_rounded_rect(draw, (bar_x, y, bar_x + bar_w, y + bar_h), BG_ACCENT, radius=3)
    if sentiment_score is not None:
        fill_pct = (sentiment_score + 1) / 2  # normalize -1..1 to 0..1
        fill_w = max(4, int(bar_w * fill_pct))
        bar_color = GREEN if sentiment_score > 0.1 else RED if sentiment_score < -0.1 else AMBER
        _draw_rounded_rect(draw, (bar_x, y, bar_x + fill_w, y + bar_h), bar_color, radius=3)
    y += 16

    # Mention stats
    draw.text((PADDING, y), str(mention_count_24h), fill=TEXT_PRIMARY, font=FONT_METRIC_VALUE)
    num_w = draw.textlength(str(mention_count_24h), font=FONT_METRIC_VALUE)
    draw.text((PADDING + num_w + 4, y + 3), "mentions 24h", fill=TEXT_MUTED, font=FONT_SMALL)

    vel_text = f"{mention_velocity:.1f}x"
    vel_color = AMBER if mention_velocity >= 3 else TEXT_PRIMARY
    mid_x = PADDING + INNER_W // 2
    draw.text((mid_x, y), vel_text, fill=vel_color, font=FONT_METRIC_VALUE)
    vel_w = draw.textlength(vel_text, font=FONT_METRIC_VALUE)
    draw.text((mid_x + vel_w + 4, y + 3), "vs avg", fill=TEXT_MUTED, font=FONT_SMALL)
    y += 28

    # === PUMP ALERT (conditional) ===
    if is_pump_alert:
        alert_y = y
        _draw_rounded_rect(
            draw,
            (PADDING, alert_y, WIDTH - PADDING, alert_y + 38),
            ALERT_BG, radius=6,
        )
        # Red dot
        draw.ellipse(
            (PADDING + 10, alert_y + 14, PADDING + 16, alert_y + 20),
            fill=RED,
        )
        draw.text(
            (PADDING + 22, alert_y + 8),
            "Pump alert:", fill=RED, font=FONT_ALERT,
        )
        alert_label_w = draw.textlength("Pump alert: ", font=FONT_ALERT)
        draw.text(
            (PADDING + 22 + alert_label_w, alert_y + 9),
            pump_alert_text or "High velocity, concentrated sources",
            fill=(192, 160, 160), font=FONT_ALERT_TEXT,
        )
        y += 48

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


def generate_fundamentals_card(
    ticker: str,
    eps: float | None,
    book_value: float | None,
    nav: float | None,
    pb_ratio: float | None,
    div_yield: float | None,
    div_ex_date: str | None,
    foreign_pct: float | None,
    local_pct: float | None,
    foreign_net: str | None,
    broker_coverage: str | None,
) -> BytesIO:
    """Generate the fundamentals detail card."""
    WIDTH = 520
    PADDING = 20
    INNER_W = WIDTH - 2 * PADDING

    # Check if we have any real data to show
    has_data = any(v is not None for v in [eps, book_value, nav, pb_ratio,
                                            div_yield, foreign_pct])

    if not has_data:
        return _generate_coming_soon_card(ticker, "FUNDAMENTALS",
            "Fundamentals data coming soon\n\n"
            "We're building the data source for EPS,\n"
            "book value, NAV, P/B, and dividend yield.\n\n"
            "This will be available once we connect\n"
            "to CSE quarterly filings.")

    HEIGHT = 320
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    y = 16
    draw.text((PADDING, y), f"{ticker} FUNDAMENTALS", fill=TEXT_MUTED, font=FONT_BRAND)
    y += 28

    # EPS + Book Value + NAV + P/B (2x2 grid)
    box_w = (INNER_W - 6) // 2
    _draw_metric_box(draw, PADDING, y, box_w, 48, "EPS (TTM)",
                     f"LKR {eps:.2f}" if eps else "N/A")
    _draw_metric_box(draw, PADDING + box_w + 6, y, box_w, 48, "Book value/share",
                     f"LKR {book_value:.2f}" if book_value else "N/A")
    y += 56
    _draw_metric_box(draw, PADDING, y, box_w, 48, "NAV per share",
                     f"LKR {nav:.2f}" if nav else "N/A")
    _draw_metric_box(draw, PADDING + box_w + 6, y, box_w, 48, "P/B ratio",
                     f"{pb_ratio:.2f}x" if pb_ratio else "N/A",
                     GREEN if pb_ratio and pb_ratio < 1 else TEXT_PRIMARY)
    y += 56

    # Dividend yield + ex-date
    _draw_rounded_rect(draw, (PADDING, y, WIDTH - PADDING, y + 48), BG_CARD, radius=6)
    draw.text((PADDING + 8, y + 6), "Div yield", fill=TEXT_MUTED, font=FONT_SMALL)
    draw.text((PADDING + 8, y + 24), f"{div_yield:.1f}%" if div_yield else "N/A",
              fill=GREEN if div_yield and div_yield > 2 else TEXT_PRIMARY, font=FONT_METRIC_VALUE)
    draw.text((WIDTH - PADDING - 8, y + 6), "Next ex-date",
              fill=TEXT_MUTED, font=FONT_SMALL, anchor="rt")
    draw.text((WIDTH - PADDING - 8, y + 24), div_ex_date or "N/A",
              fill=TEXT_PRIMARY, font=FONT_METRIC_VALUE, anchor="rt")
    y += 56

    # Foreign vs local bar
    _draw_rounded_rect(draw, (PADDING, y, WIDTH - PADDING, y + 56), BG_CARD, radius=6)
    draw.text((PADDING + 8, y + 6), "Foreign / local ratio", fill=TEXT_MUTED, font=FONT_SMALL)

    bar_y = y + 24
    bar_w = INNER_W - 100
    _draw_rounded_rect(draw, (PADDING + 8, bar_y, PADDING + 8 + bar_w, bar_y + 6), BG_ACCENT, radius=3)
    if foreign_pct:
        f_w = int(bar_w * foreign_pct / 100)
        _draw_rounded_rect(draw, (PADDING + 8, bar_y, PADDING + 8 + f_w, bar_y + 6), BLUE, radius=3)
        _draw_rounded_rect(draw, (PADDING + 8 + f_w, bar_y, PADDING + 8 + bar_w, bar_y + 6), GREEN, radius=3)
    ratio_text = f"{foreign_pct:.0f}% / {local_pct:.0f}%" if foreign_pct else "N/A"
    draw.text((WIDTH - PADDING - 8, bar_y), ratio_text,
              fill=TEXT_MUTED, font=FONT_SMALL, anchor="rt")

    if foreign_net:
        draw.text((PADDING + 8, bar_y + 14), foreign_net, fill=TEXT_MUTED, font=FONT_SMALL)
    y += 64

    # Broker coverage
    if broker_coverage:
        draw.text((PADDING, y), f"Broker: {broker_coverage}", fill=TEXT_MUTED, font=FONT_SMALL)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


def _generate_coming_soon_card(ticker: str, section: str, message: str) -> BytesIO:
    """Generate a placeholder card for features not yet available."""
    WIDTH = 520
    PADDING = 20
    HEIGHT = 200

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    y = 16
    draw.text((PADDING, y), f"{ticker} {section}", fill=TEXT_MUTED, font=FONT_BRAND)
    y += 36

    # Icon-like decoration
    _draw_rounded_rect(draw, (PADDING, y, WIDTH - PADDING, HEIGHT - 16), BG_CARD, radius=8)

    for i, line in enumerate(message.split("\n")):
        color = TEXT_SECONDARY if i == 0 else TEXT_MUTED
        font = FONT_SECTION if i == 0 else FONT_SMALL
        draw.text((PADDING + 16, y + 12 + i * 20), line, fill=color, font=font)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


def generate_technicals_card(
    ticker: str,
    company_name: str,
    last_price: float,
    change: float,
    change_pct: float,
    high: float,
    low: float,
    prev_close: float,
    high_wtd: float | None,
    low_wtd: float | None,
    high_mtd: float | None,
    low_mtd: float | None,
    high_ytd: float | None,
    low_ytd: float | None,
    high_52w: float,
    low_52w: float,
    support: float | None,
    resistance: float | None,
    beta_aspi: float | None,
    beta_spsl: float | None,
    volume: int,
    avg_daily_volume_mtd: int | None,
    price_position_52w: float | None,
    spread_pct: float | None,
) -> BytesIO:
    """Generate the technicals detail card as a dark-themed Pillow image."""
    WIDTH = 520
    PADDING = 20
    INNER_W = WIDTH - 2 * PADDING

    # Calculate height
    height = 16  # top padding
    height += 26  # header
    height += 40  # price line
    height += 16  # spacer
    height += 5 * 36  # 5 range rows (Today, WTD, MTD, YTD, 52W)
    height += 16  # spacer
    height += 56  # support/resistance boxes
    height += 12  # spacer
    height += 56  # beta + volume boxes
    if price_position_52w is not None:
        height += 12  # spacer
        height += 36  # 52w position bar
    height += 20  # bottom padding

    img = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(img)

    y = 16

    # === HEADER ===
    draw.text((PADDING, y), f"{ticker} TECHNICALS", fill=TEXT_MUTED, font=FONT_BRAND)
    name_w = draw.textlength(f"{ticker} TECHNICALS  ", font=FONT_BRAND)
    draw.text((PADDING + name_w, y), company_name, fill=TEXT_MUTED, font=FONT_SMALL)
    y += 26

    # === PRICE LINE ===
    price_text = f"LKR {last_price:,.2f}"
    draw.text((PADDING, y), price_text, fill=TEXT_PRIMARY, font=FONT_PRICE)
    price_w = draw.textlength(price_text, font=FONT_PRICE)
    sign = "+" if change >= 0 else ""
    change_text = f"{sign}{change:.2f} ({sign}{change_pct:.2f}%)"
    draw.text(
        (PADDING + price_w + 12, y + 10),
        change_text, fill=_change_color(change), font=FONT_CHANGE,
    )
    y += 44

    # === RANGE ROWS ===
    # Each row: [Label] [low --- bar --- high]  showing where price sits
    draw.text((PADDING, y - 4), "Price ranges", fill=TEXT_SECONDARY, font=FONT_SECTION)
    y += 18

    ranges = [
        ("Today", low, high),
        ("WTD", low_wtd, high_wtd),
        ("MTD", low_mtd, high_mtd),
        ("YTD", low_ytd, high_ytd),
        ("52W", low_52w, high_52w),
    ]

    label_w = 40
    bar_start = PADDING + label_w + 8
    bar_end = WIDTH - PADDING - 70  # leave room for high value
    bar_w = bar_end - bar_start

    for label, r_low, r_high in ranges:
        if r_low is None or r_high is None or r_low == 0 or r_high == 0:
            # Skip rows with no data
            continue

        draw.text((PADDING, y + 4), label, fill=TEXT_MUTED, font=FONT_SMALL)

        # Low value
        draw.text((bar_start - 4, y + 4), f"{r_low:.1f}",
                  fill=TEXT_MUTED, font=FONT_SMALL, anchor="rt")

        # Bar background
        bar_y = y + 8
        _draw_rounded_rect(draw, (bar_start, bar_y, bar_start + bar_w, bar_y + 6),
                          BG_ACCENT, radius=3)

        # Price position within range
        if r_high > r_low and r_low <= last_price <= r_high:
            pos = (last_price - r_low) / (r_high - r_low)
            fill_w = max(4, int(bar_w * pos))
            bar_color = GREEN if change >= 0 else RED
            _draw_rounded_rect(draw, (bar_start, bar_y, bar_start + fill_w, bar_y + 6),
                              bar_color, radius=3)
            # Dot at current position
            dot_x = bar_start + fill_w
            draw.ellipse((dot_x - 3, bar_y - 1, dot_x + 3, bar_y + 7),
                        fill=TEXT_PRIMARY)
        elif last_price > r_high:
            # Price above range — fill entire bar
            _draw_rounded_rect(draw, (bar_start, bar_y, bar_start + bar_w, bar_y + 6),
                              GREEN, radius=3)
        elif last_price < r_low:
            # Price below range — empty bar with red tint
            _draw_rounded_rect(draw, (bar_start, bar_y, bar_start + 4, bar_y + 6),
                              RED, radius=3)

        # High value
        draw.text((bar_start + bar_w + 6, y + 4), f"{r_high:.1f}",
                  fill=TEXT_MUTED, font=FONT_SMALL)

        y += 28

    y += 8

    # === SUPPORT / RESISTANCE ===
    box_w = (INNER_W - 6) // 2
    _draw_rounded_rect(draw, (PADDING, y, PADDING + box_w, y + 48), BG_CARD, radius=6)
    draw.text((PADDING + 8, y + 6), "Support (MTD low)", fill=TEXT_MUTED, font=FONT_SMALL)
    s_text = f"LKR {support:.2f}" if support else "N/A"
    s_color = GREEN if support and last_price > support else TEXT_PRIMARY
    draw.text((PADDING + 8, y + 24), s_text, fill=s_color, font=FONT_METRIC_VALUE)

    _draw_rounded_rect(draw, (PADDING + box_w + 6, y, WIDTH - PADDING, y + 48), BG_CARD, radius=6)
    draw.text((PADDING + box_w + 14, y + 6), "Resistance (MTD high)", fill=TEXT_MUTED, font=FONT_SMALL)
    r_text = f"LKR {resistance:.2f}" if resistance else "N/A"
    r_color = RED if resistance and last_price < resistance else TEXT_PRIMARY
    draw.text((PADDING + box_w + 14, y + 24), r_text, fill=r_color, font=FONT_METRIC_VALUE)
    y += 56

    # === BETA + VOLUME ROW ===
    y += 4
    metrics = []
    if beta_aspi is not None:
        metrics.append(("Beta (ASPI)", f"{beta_aspi:.2f}",
                       GREEN if beta_aspi < 1 else AMBER if beta_aspi < 1.5 else RED))
    if beta_spsl is not None:
        metrics.append(("Beta (S&P SL20)", f"{beta_spsl:.2f}", TEXT_PRIMARY))
    metrics.append(("Volume", _format_number(volume), TEXT_PRIMARY))
    if avg_daily_volume_mtd:
        metrics.append(("Avg daily (MTD)", _format_number(avg_daily_volume_mtd), TEXT_PRIMARY))
    if spread_pct is not None:
        metrics.append(("Spread", f"{spread_pct:.1f}%", TEXT_PRIMARY))

    # Render as evenly spaced boxes (up to 4)
    visible = metrics[:4]
    if visible:
        m_box_w = (INNER_W - 6 * (len(visible) - 1)) // len(visible)
        for i, (m_label, m_val, m_color) in enumerate(visible):
            mx = PADDING + i * (m_box_w + 6)
            _draw_metric_box(draw, mx, y, m_box_w, 48, m_label, m_val, m_color)
    y += 56

    # === 52W POSITION BAR ===
    if price_position_52w is not None:
        y += 4
        draw.text((PADDING, y), "52-week position", fill=TEXT_MUTED, font=FONT_SMALL)
        pct_text = f"{price_position_52w:.0f}%"
        draw.text((WIDTH - PADDING, y), pct_text,
                  fill=TEXT_SECONDARY, font=FONT_SMALL, anchor="rt")
        y += 16
        pos_bar_w = INNER_W
        _draw_rounded_rect(draw, (PADDING, y, PADDING + pos_bar_w, y + 8),
                          BG_ACCENT, radius=4)
        fill_w = max(6, int(pos_bar_w * price_position_52w / 100))
        bar_color = GREEN if price_position_52w > 50 else AMBER if price_position_52w > 25 else RED
        _draw_rounded_rect(draw, (PADDING, y, PADDING + fill_w, y + 8),
                          bar_color, radius=4)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# Quick test
if __name__ == "__main__":
    print("Generating test card...")
    buf = generate_main_card(
        ticker="KPHL",
        company_name="Kapruka Holdings PLC",
        sector="Consumer",
        last_price=18.50,
        change=-0.80,
        change_pct=-4.15,
        market_cap=1_200_000_000,
        volume=342_000,
        pe_ratio=8.2,
        spread_pct=1.4,
        change_7d=-8.2,
        change_30d=-12.5,
        change_90d=4.1,
        sentiment_score=-0.32,
        mention_count_24h=47,
        mention_velocity=3.6,
        is_pump_alert=True,
        pump_alert_text="High velocity, concentrated sources, no catalyst",
    )

    with open("/tmp/test_card.png", "wb") as f:
        f.write(buf.read())
    print("Card saved to /tmp/test_card.png")
