"""
CeylonVest Pulse Card Generator
Premium fintech-style ticker cards with Inter font family.
Sized at 800px wide for optimal mobile readability on Telegram.
"""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from pathlib import Path


# ==========================================================================
# Font loading
# ==========================================================================

FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load an Inter font with fallback chain."""
    paths = [
        FONT_DIR / name,
        Path("C:/Windows/Fonts/segoeuib.ttf") if "Bold" in name
        else Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if "Bold" in name
        else Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in paths:
        try:
            return ImageFont.truetype(str(p), size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# Typography scale — sized for 800px card width
FONT_BRAND    = _font("Inter-Bold.ttf", 16)
FONT_TICKER   = _font("InterDisplay-Bold.ttf", 36)
FONT_COMPANY  = _font("Inter-Regular.ttf", 20)
FONT_PRICE    = _font("InterDisplay-Bold.ttf", 42)
FONT_CHANGE   = _font("Inter-SemiBold.ttf", 22)
FONT_LABEL    = _font("Inter-Medium.ttf", 16)
FONT_VALUE    = _font("Inter-SemiBold.ttf", 22)
FONT_SECTION  = _font("Inter-SemiBold.ttf", 18)
FONT_SMALL    = _font("Inter-Regular.ttf", 16)
FONT_TINY     = _font("Inter-Regular.ttf", 15)
FONT_ALERT    = _font("Inter-SemiBold.ttf", 18)


# ==========================================================================
# Color palette
# ==========================================================================

BG           = (17, 17, 30)
BG_CARD      = (26, 26, 46)
BG_SURFACE   = (34, 34, 58)
BG_ACCENT    = (44, 44, 70)
BORDER       = (50, 50, 76)

TEXT_PRIMARY   = (245, 245, 255)
TEXT_SECONDARY = (160, 160, 195)
TEXT_MUTED     = (110, 110, 145)
TEXT_DIM       = (80, 80, 110)

GREEN      = (80, 205, 155)
GREEN_DIM  = (40, 80, 65)
RED        = (235, 77, 85)
RED_DIM    = (65, 30, 35)
AMBER      = (245, 175, 55)
BLUE       = (65, 145, 230)
PURPLE     = (130, 120, 225)

BRAND_ACCENT = (80, 205, 155)
ALERT_BG     = (55, 22, 25)


# ==========================================================================
# Drawing helpers
# ==========================================================================

def _rounded_rect(draw, xy, fill, radius=10, outline=None):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def _change_color(val):
    if val is None:
        return TEXT_MUTED
    return GREEN if val >= 0 else RED


def _change_bg(val):
    if val is None:
        return BG_SURFACE
    return GREEN_DIM if val >= 0 else RED_DIM


def _format_num(n, prefix="", suffix=""):
    if n is None:
        return "N/A"
    if isinstance(n, (int, float)):
        if abs(n) >= 1e9:
            return f"{prefix}{n/1e9:.1f}B{suffix}"
        elif abs(n) >= 1e6:
            return f"{prefix}{n/1e6:.1f}M{suffix}"
        elif abs(n) >= 1e3:
            return f"{prefix}{n/1e3:.0f}K{suffix}"
        else:
            return f"{prefix}{n:.2f}{suffix}"
    return str(n)


def _draw_metric(draw, x, y, w, h, label, value, value_color=TEXT_PRIMARY):
    """Draw a metric box with label + value. Generous internal padding."""
    _rounded_rect(draw, (x, y, x+w, y+h), BG_SURFACE, radius=8)
    draw.text((x + 14, y + 12), label, fill=TEXT_MUTED, font=FONT_LABEL)
    draw.text((x + 14, y + 34), value, fill=value_color, font=FONT_VALUE)


def _draw_sparkline(draw, x, y, w, h, points, color):
    if not points or len(points) < 2:
        return
    _rounded_rect(draw, (x, y, x+w, y+h), BG_ACCENT, radius=6)
    values = [(lo + hi) / 2 for lo, hi in points if lo and hi]
    if len(values) < 2:
        return
    v_min = min(values) * 0.998
    v_max = max(values) * 1.002
    v_range = v_max - v_min if v_max > v_min else 1
    pad_x, pad_y = 10, 10
    chart_w = w - 2 * pad_x
    chart_h = h - 2 * pad_y
    line_points = []
    for i, v in enumerate(values):
        px = x + pad_x + (i / (len(values) - 1)) * chart_w
        py = y + pad_y + chart_h - ((v - v_min) / v_range) * chart_h
        line_points.append((px, py))
    # Area fill
    bottom = y + h - pad_y
    for i in range(len(line_points) - 1):
        x1, y1 = line_points[i]
        x2, y2 = line_points[i+1]
        steps = max(1, int(x2 - x1))
        for s in range(steps):
            frac = s / steps
            cx = x1 + (x2 - x1) * frac
            cy = y1 + (y2 - y1) * frac
            dim = (color[0]//5, color[1]//5, color[2]//5)
            draw.line([(cx, cy), (cx, bottom)], fill=dim, width=1)
    draw.line(line_points, fill=color, width=2, joint="curve")
    ex, ey = line_points[-1]
    draw.ellipse((ex-4, ey-4, ex+4, ey+4), fill=color)
    draw.ellipse((ex-6, ey-6, ex+6, ey+6), outline=color, width=1)


def _draw_divider(draw, x, y, w, style="line"):
    if style == "line":
        draw.line([(x, y), (x + w, y)], fill=BORDER, width=1)
    elif style == "dots":
        for dx in range(0, w, 10):
            draw.ellipse((x+dx, y, x+dx+3, y+3), fill=BORDER)


def _draw_footer(draw, y, width, pad):
    inner = width - 2 * pad
    _draw_divider(draw, pad, y, inner, style="dots")
    y += 12
    draw.text((pad, y), "ceylonvest.com", fill=TEXT_DIM, font=FONT_TINY)
    draw.text((width - pad, y), "AI-powered market intelligence",
              fill=TEXT_DIM, font=FONT_TINY, anchor="rt")


def _draw_header(draw, y, width, pad, ticker, section_name, company_name=None):
    """Draw the standard card header: brand accent bar + section title."""
    draw.rectangle([(0, 0), (width, 4)], fill=BRAND_ACCENT)
    draw.text((pad, y), f"{ticker} {section_name}", fill=TEXT_DIM, font=FONT_BRAND)
    if company_name:
        hw = draw.textlength(f"{ticker} {section_name}  ", font=FONT_BRAND)
        draw.text((pad + hw, y + 1), company_name, fill=TEXT_DIM, font=FONT_TINY)


# ==========================================================================
# Main card
# ==========================================================================

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
    high: float,
    low: float,
    prev_close: float,
    high_52w: float,
    low_52w: float,
    price_position_52w: float | None,
    sparkline_points: list[tuple[float, float]] | None = None,
    sentiment_score: float | None = None,
    mention_count_24h: int = 0,
    mention_velocity: float = 0,
    is_pump_alert: bool = False,
    pump_alert_text: str = "",
    parent_group: str | None = None,
) -> BytesIO:
    WIDTH = 800
    PAD = 30
    INNER = WIDTH - 2 * PAD
    SECTION_GAP = 20  # vertical gap between sections
    has_pe = pe_ratio is not None
    has_sparkline = sparkline_points and len(sparkline_points) >= 2

    # Calculate height
    h = 24                    # top padding
    h += 30                   # brand bar
    h += SECTION_GAP
    h += 48                   # ticker + company
    if parent_group:
        h += 20                   # group label
    h += 12
    h += 52                   # price + change pill
    h += SECTION_GAP
    h += 66                   # metric boxes
    if has_sparkline:
        h += SECTION_GAP + 90
    h += SECTION_GAP
    if price_position_52w is not None:
        h += 50 + SECTION_GAP
    h += 1 + SECTION_GAP      # divider
    h += 100                   # sentiment section
    if is_pump_alert:
        h += SECTION_GAP + 52
    h += SECTION_GAP + 24 + 16  # footer

    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    # Brand bar
    draw.rectangle([(0, 0), (WIDTH, 4)], fill=BRAND_ACCENT)
    draw.text((PAD, y), "CEYLONVEST PULSE", fill=TEXT_DIM, font=FONT_BRAND)
    sector_text = sector.upper()
    stw = draw.textlength(sector_text, font=FONT_TINY)
    pill_x = WIDTH - PAD - stw - 22
    _rounded_rect(draw, (pill_x, y-3, WIDTH-PAD, y+20), BG_SURFACE, radius=10, outline=BORDER)
    draw.text((pill_x + 11, y), sector_text, fill=TEXT_SECONDARY, font=FONT_TINY)
    y += 30 + SECTION_GAP

    # Ticker + company
    draw.text((PAD, y), ticker, fill=TEXT_PRIMARY, font=FONT_TICKER)
    tw = draw.textlength(ticker, font=FONT_TICKER)
    draw.text((PAD + tw + 14, y + 14), company_name, fill=TEXT_MUTED, font=FONT_COMPANY)
    y += 48
    if parent_group:
        draw.text((PAD, y), f"Part of {parent_group}", fill=PURPLE, font=FONT_LABEL)
        y += 20
    y += 12

    # Price + change pill
    price_str = f"LKR {last_price:,.2f}"
    draw.text((PAD, y), price_str, fill=TEXT_PRIMARY, font=FONT_PRICE)
    pw = draw.textlength(price_str, font=FONT_PRICE)
    sign = "+" if change >= 0 else ""
    pill_text = f"{sign}{change:.2f}  {sign}{change_pct:.2f}%"
    ptw = draw.textlength(pill_text, font=FONT_CHANGE)
    cpx = PAD + pw + 20
    _rounded_rect(draw, (cpx, y+10, cpx+ptw+24, y+38), _change_bg(change), radius=8)
    draw.text((cpx + 12, y + 12), pill_text, fill=_change_color(change), font=FONT_CHANGE)
    y += 52 + SECTION_GAP

    # Metric boxes — taller with more internal padding
    BOX_H = 62
    if has_pe:
        box_w = (INNER - 24) // 4
        gap = 8
        metrics = [("MKT CAP", _format_num(market_cap)), ("VOLUME", _format_num(volume)),
                   ("P/E", f"{pe_ratio:.1f}x"), ("SPREAD", f"{spread_pct:.1f}%" if spread_pct else "N/A")]
    else:
        box_w = (INNER - 16) // 3
        gap = 8
        metrics = [("MKT CAP", _format_num(market_cap)), ("VOLUME", _format_num(volume)),
                   ("SPREAD", f"{spread_pct:.1f}%" if spread_pct else "N/A")]
    for i, (lbl, val) in enumerate(metrics):
        _draw_metric(draw, PAD + i*(box_w+gap), y, box_w, BOX_H, lbl, val)
    y += BOX_H + 4

    # Sparkline
    if has_sparkline:
        y += SECTION_GAP
        draw.text((PAD, y), "PRICE TREND", fill=TEXT_MUTED, font=FONT_LABEL)
        draw.text((WIDTH-PAD, y), f"Today: {low:.1f} – {high:.1f}",
                  fill=TEXT_MUTED, font=FONT_TINY, anchor="rt")
        y += 22
        _draw_sparkline(draw, PAD, y, INNER, 80, sparkline_points,
                       GREEN if change >= 0 else RED)
        y += 84

    # 52-week range
    if price_position_52w is not None:
        y += SECTION_GAP
        draw.text((PAD, y), "52-WEEK RANGE", fill=TEXT_MUTED, font=FONT_LABEL)
        draw.text((WIDTH-PAD, y), f"{price_position_52w:.0f}%",
                  fill=TEXT_SECONDARY, font=FONT_LABEL, anchor="rt")
        y += 22
        _rounded_rect(draw, (PAD, y, WIDTH-PAD, y+8), BG_ACCENT, radius=4)
        fill_w = max(8, int(INNER * price_position_52w / 100))
        bar_c = GREEN if price_position_52w > 50 else AMBER if price_position_52w > 25 else RED
        _rounded_rect(draw, (PAD, y, PAD+fill_w, y+8), bar_c, radius=4)
        y += 12
        draw.text((PAD, y), f"{low_52w:.1f}", fill=TEXT_DIM, font=FONT_TINY)
        draw.text((WIDTH-PAD, y), f"{high_52w:.1f}", fill=TEXT_DIM, font=FONT_TINY, anchor="rt")
        y += 20

    # Divider
    y += SECTION_GAP // 2
    _draw_divider(draw, PAD, y, INNER)
    y += SECTION_GAP

    # Sentiment
    draw.text((PAD, y), "PULSE SENTIMENT", fill=TEXT_MUTED, font=FONT_LABEL)
    if sentiment_score is not None:
        sc = GREEN if sentiment_score > 0.1 else RED if sentiment_score < -0.1 else AMBER
        score_str = f"{sentiment_score:+.2f}"
        stw = draw.textlength(score_str, font=FONT_VALUE)
        sx = WIDTH - PAD - stw - 18
        sbg = GREEN_DIM if sentiment_score > 0.1 else RED_DIM if sentiment_score < -0.1 else BG_SURFACE
        _rounded_rect(draw, (sx, y-3, WIDTH-PAD, y+22), sbg, radius=8)
        draw.text((sx + 9, y), score_str, fill=sc, font=FONT_VALUE)
    y += 30
    bar_w = INNER
    _rounded_rect(draw, (PAD, y, PAD+bar_w, y+6), BG_ACCENT, radius=3)
    if sentiment_score is not None:
        fill_pct = (sentiment_score + 1) / 2
        fill_w = max(6, int(bar_w * fill_pct))
        sc = GREEN if sentiment_score > 0.1 else RED if sentiment_score < -0.1 else AMBER
        _rounded_rect(draw, (PAD, y, PAD+fill_w, y+6), sc, radius=3)
    y += 18

    mc_str = str(mention_count_24h)
    draw.text((PAD, y), mc_str, fill=TEXT_PRIMARY, font=FONT_VALUE)
    mcw = draw.textlength(mc_str, font=FONT_VALUE)
    draw.text((PAD+mcw+6, y+4), "mentions 24h", fill=TEXT_MUTED, font=FONT_SMALL)
    vel_str = f"{mention_velocity:.1f}x"
    vel_c = AMBER if mention_velocity >= 3 else TEXT_PRIMARY
    mid = PAD + INNER // 2
    draw.text((mid, y), vel_str, fill=vel_c, font=FONT_VALUE)
    vw = draw.textlength(vel_str, font=FONT_VALUE)
    draw.text((mid+vw+6, y+4), "vs avg", fill=TEXT_MUTED, font=FONT_SMALL)
    draw.text((WIDTH-PAD, y+4), f"prev {prev_close:.2f}", fill=TEXT_DIM,
              font=FONT_SMALL, anchor="rt")
    y += 30

    # Pump alert
    if is_pump_alert:
        y += SECTION_GAP // 2
        _rounded_rect(draw, (PAD, y, WIDTH-PAD, y+48), ALERT_BG, radius=8, outline=RED)
        draw.ellipse((PAD+16, y+19, PAD+24, y+27), fill=RED)
        draw.text((PAD+32, y+13), "PUMP ALERT", fill=RED, font=FONT_ALERT)
        atw = draw.textlength("PUMP ALERT  ", font=FONT_ALERT)
        draw.text((PAD+32+atw, y+15),
                  pump_alert_text or "High velocity, concentrated sources",
                  fill=TEXT_SECONDARY, font=FONT_SMALL)
        y += 52

    # Footer
    y += SECTION_GAP // 2
    _draw_footer(draw, y, WIDTH, PAD)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ==========================================================================
# Fundamentals card
# ==========================================================================

def generate_company_info_card(
    ticker: str,
    company_name: str,
    sector: str,
    # CSE API data (always available)
    market_cap: float | None,
    shares_outstanding: int | None,
    par_value: float | None,
    beta_aspi: float | None,
    beta_spsl: float | None,
    high_52w: float | None,
    low_52w: float | None,
    price_position_52w: float | None,
    last_price: float | None,
    foreign_pct: float | None,
    # From companyProfile endpoint
    directors: list[str] | None,
    business_summary: str | None,
    auditors: str | None,
    # From fundamentals.json (manually curated)
    eps: float | None,
    nav: float | None,
    pe: float | None,
    pb: float | None,
    div_yield: float | None,
    dps: float | None,
    fundamentals_period: str | None,
) -> BytesIO:
    WIDTH = 800
    PAD = 30
    INNER = WIDTH - 2 * PAD
    SECTION_GAP = 16
    BOX_H = 62

    # Calculate height dynamically based on content
    HEIGHT = 80  # header + padding
    HEIGHT += BOX_H + 10 + BOX_H + SECTION_GAP  # market data 2x2
    HEIGHT += BOX_H + SECTION_GAP  # beta row
    HEIGHT += 56 + SECTION_GAP  # 52-week range bar
    if any(v is not None for v in [eps, nav, pe, pb, div_yield, dps]):
        HEIGHT += 22 + BOX_H + 10 + BOX_H + SECTION_GAP  # fundamentals section
    if directors:
        dir_lines = min(len(directors), 5)
        HEIGHT += 22 + 20 * dir_lines + SECTION_GAP
    if business_summary:
        # Wrap summary text
        wrapped = _wrap_text(business_summary, FONT_SMALL, INNER - 28)
        HEIGHT += 22 + 20 * len(wrapped) + SECTION_GAP
    HEIGHT += 40  # footer

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    _draw_header(draw, y, WIDTH, PAD, ticker, "COMPANY INFO", company_name)
    y += 30 + SECTION_GAP

    # --- SECTION: Market Data (from CSE API) ---
    box_w = (INNER - 8) // 2
    _draw_metric(draw, PAD, y, box_w, BOX_H, "MARKET CAP",
                 _format_num(market_cap, prefix="LKR ") if market_cap else "N/A")
    _draw_metric(draw, PAD + box_w + 8, y, box_w, BOX_H, "SHARES OUT",
                 _format_num(shares_outstanding) if shares_outstanding else "N/A")
    y += BOX_H + 10
    _draw_metric(draw, PAD, y, box_w, BOX_H, "PAR VALUE",
                 f"LKR {par_value:.2f}" if par_value else "N/A")
    _draw_metric(draw, PAD + box_w + 8, y, box_w, BOX_H, "SECTOR",
                 sector or "N/A", value_color=BLUE)
    y += BOX_H + SECTION_GAP

    # Beta row
    box_w3 = (INNER - 16) // 3
    _draw_metric(draw, PAD, y, box_w3, BOX_H, "BETA (ASPI)",
                 f"{beta_aspi:.2f}" if beta_aspi else "N/A")
    _draw_metric(draw, PAD + box_w3 + 8, y, box_w3, BOX_H, "BETA (S&P SL20)",
                 f"{beta_spsl:.2f}" if beta_spsl else "N/A")
    foreign_val = f"{foreign_pct:.1f}%" if foreign_pct else "N/A"
    _draw_metric(draw, PAD + 2 * (box_w3 + 8), y, box_w3, BOX_H, "FOREIGN %",
                 foreign_val, value_color=BLUE if foreign_pct else TEXT_MUTED)
    y += BOX_H + SECTION_GAP

    # 52-week range bar
    _rounded_rect(draw, (PAD, y, WIDTH - PAD, y + 56), BG_SURFACE, radius=8)
    draw.text((PAD + 14, y + 8), "52-WEEK RANGE", fill=TEXT_MUTED, font=FONT_LABEL)
    bar_y = y + 32
    bar_x = PAD + 14
    bar_w = INNER - 28
    # Background bar
    _rounded_rect(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + 8), BG_ACCENT, radius=4)
    # Position marker
    if price_position_52w is not None:
        pos_x = bar_x + int(bar_w * price_position_52w / 100)
        # Filled portion
        bar_color = GREEN if price_position_52w < 50 else AMBER if price_position_52w < 80 else RED
        _rounded_rect(draw, (bar_x, bar_y, pos_x, bar_y + 8), bar_color, radius=4)
        # Triangle marker
        draw.polygon([(pos_x, bar_y - 4), (pos_x - 4, bar_y - 10), (pos_x + 4, bar_y - 10)],
                     fill=TEXT_PRIMARY)
    low_text = f"LKR {low_52w:.1f}" if low_52w else "?"
    high_text = f"LKR {high_52w:.1f}" if high_52w else "?"
    draw.text((bar_x, bar_y + 12), low_text, fill=TEXT_MUTED, font=FONT_TINY)
    draw.text((bar_x + bar_w, bar_y + 12), high_text, fill=TEXT_MUTED,
              font=FONT_TINY, anchor="rt")
    if price_position_52w is not None:
        pct_text = f"{price_position_52w:.0f}%"
        pos_x = bar_x + int(bar_w * price_position_52w / 100)
        draw.text((pos_x, bar_y + 12), pct_text, fill=TEXT_SECONDARY,
                  font=FONT_TINY, anchor="mt")
    y += 56 + SECTION_GAP

    # --- SECTION: Fundamentals (from JSON file) ---
    has_fundamentals = any(v is not None for v in [eps, nav, pe, pb, div_yield, dps])
    if has_fundamentals:
        period_label = f"  ({fundamentals_period} data)" if fundamentals_period else ""
        draw.text((PAD, y), f"FUNDAMENTALS{period_label}",
                  fill=TEXT_MUTED, font=FONT_LABEL)
        y += 22
        box_w = (INNER - 16) // 3
        _draw_metric(draw, PAD, y, box_w, BOX_H, "EPS",
                     f"LKR {eps:.2f}" if eps else "N/A")
        _draw_metric(draw, PAD + box_w + 8, y, box_w, BOX_H, "NAV / SHARE",
                     f"LKR {nav:.2f}" if nav else "N/A")
        _draw_metric(draw, PAD + 2 * (box_w + 8), y, box_w, BOX_H, "P/E RATIO",
                     f"{pe:.1f}x" if pe else "N/A",
                     GREEN if pe and pe < 15 else AMBER if pe and pe < 25 else TEXT_PRIMARY)
        y += BOX_H + 10
        _draw_metric(draw, PAD, y, box_w, BOX_H, "P/B RATIO",
                     f"{pb:.2f}x" if pb else "N/A",
                     GREEN if pb and pb < 1 else TEXT_PRIMARY)
        _draw_metric(draw, PAD + box_w + 8, y, box_w, BOX_H, "DIV YIELD",
                     f"{div_yield:.1f}%" if div_yield else "N/A",
                     GREEN if div_yield and div_yield > 2 else TEXT_PRIMARY)
        _draw_metric(draw, PAD + 2 * (box_w + 8), y, box_w, BOX_H, "DPS",
                     f"LKR {dps:.2f}" if dps else "N/A")
        y += BOX_H + SECTION_GAP

    # --- SECTION: Directors ---
    if directors:
        draw.text((PAD, y), "BOARD OF DIRECTORS", fill=TEXT_MUTED, font=FONT_LABEL)
        y += 22
        for name in directors[:5]:
            draw.text((PAD + 14, y), name, fill=TEXT_SECONDARY, font=FONT_SMALL)
            y += 20
        if len(directors) > 5:
            draw.text((PAD + 14, y), f"+ {len(directors) - 5} more",
                      fill=TEXT_DIM, font=FONT_TINY)
            y += 20
        y += SECTION_GAP - 10

    # --- SECTION: Business Summary ---
    if business_summary:
        draw.text((PAD, y), "BUSINESS SUMMARY", fill=TEXT_MUTED, font=FONT_LABEL)
        y += 22
        wrapped = _wrap_text(business_summary, FONT_SMALL, INNER - 28)
        for line in wrapped:
            draw.text((PAD + 14, y), line, fill=TEXT_MUTED, font=FONT_SMALL)
            y += 20
        y += SECTION_GAP - 10

    # Footer
    _draw_footer(draw, y, WIDTH, PAD)

    # Crop to actual height
    actual_h = y + 34
    if actual_h < HEIGHT:
        img = img.crop((0, 0, WIDTH, actual_h))

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        try:
            w = font.getlength(test)
        except AttributeError:
            w = len(test) * 8  # fallback
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:6]  # max 6 lines


# Keep old name as alias for backward compatibility in tests
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
    """Legacy wrapper — redirects to generate_company_info_card."""
    return generate_company_info_card(
        ticker=ticker,
        company_name="",
        sector="",
        market_cap=None,
        shares_outstanding=None,
        par_value=None,
        beta_aspi=None,
        beta_spsl=None,
        high_52w=None,
        low_52w=None,
        price_position_52w=None,
        last_price=None,
        foreign_pct=foreign_pct,
        directors=None,
        business_summary=None,
        auditors=None,
        eps=eps,
        nav=nav,
        pe=None,
        pb=pb_ratio,
        div_yield=div_yield,
        dps=None,
        fundamentals_period=None,
    )


def _generate_coming_soon_card(ticker: str, section: str, message: str) -> BytesIO:
    WIDTH = 800
    PAD = 30
    HEIGHT = 300

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    _draw_header(draw, y, WIDTH, PAD, ticker, section)
    y += 44

    _rounded_rect(draw, (PAD, y, WIDTH-PAD, HEIGHT-40), BG_SURFACE, radius=10)
    for i, line in enumerate(message.split("\n")):
        color = TEXT_SECONDARY if i == 0 else TEXT_MUTED
        font = FONT_SECTION if i == 0 else FONT_SMALL
        draw.text((PAD + 24, y + 18 + i * 28), line, fill=color, font=font)

    _draw_footer(draw, HEIGHT - 34, WIDTH, PAD)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ==========================================================================
# Technicals card
# ==========================================================================

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
    WIDTH = 800
    PAD = 30
    INNER = WIDTH - 2 * PAD
    SECTION_GAP = 20
    BOX_H = 62

    # Count valid range rows
    ranges = [
        ("Today", low, high),
        ("WTD", low_wtd, high_wtd),
        ("MTD", low_mtd, high_mtd),
        ("YTD", low_ytd, high_ytd),
        ("52W", low_52w, high_52w),
    ]
    valid_ranges = [(l, lo, hi) for l, lo, hi in ranges
                    if lo and hi and lo > 0 and hi > 0]

    # Calculate height
    h = 24                          # top padding
    h += 30                         # header
    h += SECTION_GAP
    h += 52                         # price
    h += SECTION_GAP
    h += 22                         # "PRICE RANGES" label
    h += len(valid_ranges) * 36 + 12
    h += SECTION_GAP
    h += BOX_H                      # support/resistance
    h += SECTION_GAP
    h += BOX_H                      # metrics row
    if price_position_52w is not None:
        h += SECTION_GAP + 46
    h += SECTION_GAP + 24 + 16      # footer

    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    # Header
    _draw_header(draw, y, WIDTH, PAD, ticker, "TECHNICALS", company_name)
    y += 30 + SECTION_GAP

    # Price + change pill
    price_str = f"LKR {last_price:,.2f}"
    draw.text((PAD, y), price_str, fill=TEXT_PRIMARY, font=FONT_PRICE)
    pw = draw.textlength(price_str, font=FONT_PRICE)
    sign = "+" if change >= 0 else ""
    pill_text = f"{sign}{change:.2f}  {sign}{change_pct:.2f}%"
    ptw = draw.textlength(pill_text, font=FONT_CHANGE)
    cpx = PAD + pw + 20
    _rounded_rect(draw, (cpx, y+10, cpx+ptw+24, y+38), _change_bg(change), radius=8)
    draw.text((cpx + 12, y + 12), pill_text, fill=_change_color(change), font=FONT_CHANGE)
    y += 52 + SECTION_GAP

    # Range rows
    draw.text((PAD, y), "PRICE RANGES", fill=TEXT_MUTED, font=FONT_LABEL)
    y += 24

    label_w = 60
    low_val_w = 80
    bar_start = PAD + label_w + low_val_w + 12
    bar_end = WIDTH - PAD - 100
    bar_w = bar_end - bar_start

    for label, r_low, r_high in valid_ranges:
        draw.text((PAD, y + 6), label, fill=TEXT_MUTED, font=FONT_SMALL)
        draw.text((PAD + label_w + low_val_w, y + 6), f"{r_low:.1f}",
                  fill=TEXT_DIM, font=FONT_SMALL, anchor="rt")

        bar_y = y + 12
        _rounded_rect(draw, (bar_start, bar_y, bar_start+bar_w, bar_y+8), BG_ACCENT, radius=4)

        bar_color = GREEN if change >= 0 else RED
        if r_high > r_low and r_low <= last_price <= r_high:
            pos = (last_price - r_low) / (r_high - r_low)
            fill_w = max(6, int(bar_w * pos))
            _rounded_rect(draw, (bar_start, bar_y, bar_start+fill_w, bar_y+8), bar_color, radius=4)
            dot_x = bar_start + fill_w
            draw.ellipse((dot_x-4, bar_y-2, dot_x+4, bar_y+10), fill=TEXT_PRIMARY)
        elif last_price > r_high:
            _rounded_rect(draw, (bar_start, bar_y, bar_start+bar_w, bar_y+8), GREEN, radius=4)
        elif last_price < r_low:
            _rounded_rect(draw, (bar_start, bar_y, bar_start+6, bar_y+8), RED, radius=4)

        draw.text((bar_start + bar_w + 10, y + 6), f"{r_high:.1f}",
                  fill=TEXT_MUTED, font=FONT_SMALL)
        y += 36

    y += 8 + SECTION_GAP // 2

    # Support / Resistance
    box_w = (INNER - 8) // 2
    s_text = f"LKR {support:.2f}" if support else "N/A"
    s_color = GREEN if support and last_price > support else TEXT_PRIMARY
    _draw_metric(draw, PAD, y, box_w, BOX_H, "SUPPORT (MTD LOW)", s_text, s_color)

    r_text = f"LKR {resistance:.2f}" if resistance else "N/A"
    r_color = RED if resistance and last_price < resistance else TEXT_PRIMARY
    _draw_metric(draw, PAD+box_w+8, y, box_w, BOX_H, "RESISTANCE (MTD HIGH)", r_text, r_color)
    y += BOX_H + SECTION_GAP

    # Beta + volume metrics
    metrics = []
    if beta_aspi is not None:
        metrics.append(("BETA (ASPI)", f"{beta_aspi:.2f}",
                       GREEN if beta_aspi < 1 else AMBER if beta_aspi < 1.5 else RED))
    if beta_spsl is not None:
        metrics.append(("BETA (S&P SL20)", f"{beta_spsl:.2f}", TEXT_PRIMARY))
    metrics.append(("VOLUME", _format_num(volume), TEXT_PRIMARY))
    if avg_daily_volume_mtd:
        metrics.append(("AVG DAILY (MTD)", _format_num(avg_daily_volume_mtd), TEXT_PRIMARY))
    if spread_pct is not None:
        metrics.append(("SPREAD", f"{spread_pct:.1f}%", TEXT_PRIMARY))

    visible = metrics[:4]
    if visible:
        m_gap = 8
        m_box_w = (INNER - m_gap * (len(visible) - 1)) // len(visible)
        for i, (m_lbl, m_val, m_clr) in enumerate(visible):
            _draw_metric(draw, PAD + i*(m_box_w+m_gap), y, m_box_w, BOX_H, m_lbl, m_val, m_clr)
    y += BOX_H

    # 52W position bar
    if price_position_52w is not None:
        y += SECTION_GAP
        draw.text((PAD, y), "52-WEEK POSITION", fill=TEXT_MUTED, font=FONT_LABEL)
        draw.text((WIDTH-PAD, y), f"{price_position_52w:.0f}%",
                  fill=TEXT_SECONDARY, font=FONT_LABEL, anchor="rt")
        y += 22
        _rounded_rect(draw, (PAD, y, PAD+INNER, y+10), BG_ACCENT, radius=5)
        fill_w = max(8, int(INNER * price_position_52w / 100))
        bar_c = GREEN if price_position_52w > 50 else AMBER if price_position_52w > 25 else RED
        _rounded_rect(draw, (PAD, y, PAD+fill_w, y+10), bar_c, radius=5)
        y += 18

    # Footer
    y += SECTION_GAP // 2
    _draw_footer(draw, y, WIDTH, PAD)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ==========================================================================
# Annual report card
# ==========================================================================

def _fmt_lkr(val: float | int) -> str:
    """Format a LKR value with B/M suffix."""
    if val >= 1e9:
        return f"LKR {val/1e9:.1f}B"
    elif val >= 1e6:
        return f"LKR {val/1e6:.0f}M"
    return f"LKR {val:,.0f}"


def _yoy_pill(draw, x, y, change: float | None):
    """Draw a small YoY change pill. Returns width consumed."""
    if change is None:
        return 0
    sign = "+" if change >= 0 else ""
    text = f"{sign}{change:.1f}% YoY"
    color = GREEN if change >= 0 else RED
    bg = GREEN_DIM if change >= 0 else RED_DIM
    tw = draw.textlength(text, font=FONT_TINY)
    _rounded_rect(draw, (x, y, x + tw + 12, y + 18), bg, radius=5)
    draw.text((x + 6, y + 1), text, fill=color, font=FONT_TINY)
    return int(tw + 16)


def generate_report_card(
    ticker: str,
    report: dict,
    news_matches: list[dict] | None = None,
    benchmarks: dict | None = None,
) -> BytesIO:
    """Generate an annual report summary card."""
    WIDTH = 800
    PAD = 30
    INNER = WIDTH - 2 * PAD
    SECTION_GAP = 18
    BOX_H = 62

    company = report.get("company", "")
    year = report.get("year", "")
    fin = report.get("financials", {})
    plans = report.get("management_plans", [])
    risks = report.get("key_risks", [])
    outlook = report.get("chairman_outlook", "")
    updated = report.get("updated", "")
    sector = report.get("sector", "")

    # Calculate height
    h = 24 + 50 + SECTION_GAP  # header
    h += BOX_H + 10 + BOX_H + SECTION_GAP  # financials 2x2
    h += BOX_H + SECTION_GAP  # ratios row
    if benchmarks and benchmarks.get("metrics"):
        h += 24  # benchmark annotation row
    if plans:
        h += 22 + len(plans[:4]) * 24 + SECTION_GAP
    if outlook:
        wrapped_outlook = _wrap_text(outlook, FONT_SMALL, INNER - 28)
        h += 22 + len(wrapped_outlook) * 20 + SECTION_GAP
    if risks:
        h += 22 + len(risks[:3]) * 24 + SECTION_GAP
    if news_matches:
        h += 22 + len(news_matches[:3]) * 48 + SECTION_GAP
    h += 40  # footer

    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    # Header
    draw.rectangle([(0, 0), (WIDTH, 4)], fill=PURPLE)
    draw.text((PAD, y), f"{ticker} ANNUAL REPORT", fill=TEXT_DIM, font=FONT_BRAND)
    period_text = f"FY {year}" if year else ""
    if updated:
        period_text += f"  |  Updated {updated}"
    draw.text((WIDTH - PAD, y + 1), period_text, fill=TEXT_DIM, font=FONT_TINY, anchor="rt")
    y += 26
    draw.text((PAD, y), company, fill=TEXT_PRIMARY, font=FONT_COMPANY)
    y += 28 + SECTION_GAP

    # Financials — row 1: Revenue + Net Profit
    box_w = (INNER - 8) // 2
    rev = fin.get("revenue", {})
    rev_val = rev.get("value") if isinstance(rev, dict) else None
    rev_yoy = rev.get("yoy_change") if isinstance(rev, dict) else None
    _rounded_rect(draw, (PAD, y, PAD + box_w, y + BOX_H), BG_SURFACE, radius=8)
    draw.text((PAD + 14, y + 10), "REVENUE", fill=TEXT_MUTED, font=FONT_LABEL)
    draw.text((PAD + 14, y + 32), _fmt_lkr(rev_val) if rev_val else "N/A",
              fill=TEXT_PRIMARY, font=FONT_VALUE)
    if rev_yoy is not None:
        vw = draw.textlength(_fmt_lkr(rev_val) if rev_val else "N/A", font=FONT_VALUE)
        _yoy_pill(draw, PAD + 14 + vw + 10, y + 34, rev_yoy)

    np_data = fin.get("net_profit", {})
    np_val = np_data.get("value") if isinstance(np_data, dict) else None
    np_yoy = np_data.get("yoy_change") if isinstance(np_data, dict) else None
    _rounded_rect(draw, (PAD + box_w + 8, y, PAD + box_w * 2 + 8, y + BOX_H), BG_SURFACE, radius=8)
    draw.text((PAD + box_w + 22, y + 10), "NET PROFIT", fill=TEXT_MUTED, font=FONT_LABEL)
    draw.text((PAD + box_w + 22, y + 32), _fmt_lkr(np_val) if np_val else "N/A",
              fill=TEXT_PRIMARY, font=FONT_VALUE)
    if np_yoy is not None:
        vw = draw.textlength(_fmt_lkr(np_val) if np_val else "N/A", font=FONT_VALUE)
        _yoy_pill(draw, PAD + box_w + 22 + vw + 10, y + 34, np_yoy)
    y += BOX_H + 10

    # Row 2: EPS + NAV
    eps = fin.get("eps")
    nav = fin.get("nav")
    _draw_metric(draw, PAD, y, box_w, BOX_H, "EPS",
                 f"LKR {eps:.2f}" if eps else "N/A")
    _draw_metric(draw, PAD + box_w + 8, y, box_w, BOX_H, "NAV / SHARE",
                 f"LKR {nav:.2f}" if nav else "N/A")
    y += BOX_H + SECTION_GAP

    # Row 3: DPS, ROE, D/E
    box_w3 = (INNER - 16) // 3
    dps = fin.get("dividend_per_share")
    roe = fin.get("roe")
    dte = fin.get("debt_to_equity")
    _draw_metric(draw, PAD, y, box_w3, BOX_H, "DPS",
                 f"LKR {dps:.2f}" if dps else "N/A",
                 GREEN if dps and dps > 0 else TEXT_PRIMARY)
    _draw_metric(draw, PAD + box_w3 + 8, y, box_w3, BOX_H, "ROE",
                 f"{roe:.1f}%" if roe else "N/A",
                 GREEN if roe and roe > 10 else AMBER if roe and roe > 5 else TEXT_PRIMARY)
    dte_color = TEXT_PRIMARY
    if dte is not None:
        dte_color = GREEN if dte < 0.5 else AMBER if dte < 1 else RED
    _draw_metric(draw, PAD + 2 * (box_w3 + 8), y, box_w3, BOX_H, "DEBT/EQUITY",
                 f"{dte:.2f}x" if dte is not None else "N/A", dte_color)
    y += BOX_H + 6

    # Benchmark annotations below Row 3
    if benchmarks and benchmarks.get("metrics"):
        bm = benchmarks["metrics"]
        sector_label = f"{sector} avg" if sector else "Sector avg"
        anno_items = [
            ("roe", roe, PAD, box_w3),
            ("dividend_per_share", dps, PAD + box_w3 + 8, box_w3),
            ("debt_to_equity", dte, PAD + 2 * (box_w3 + 8), box_w3),
        ]
        for metric_key, val, ax, aw in anno_items:
            m = bm.get(metric_key)
            if m and m.get("avg") is not None and m.get("count", 0) >= 2:
                avg = m["avg"]
                if metric_key == "roe":
                    avg_text = f"{sector_label}: {avg:.1f}%"
                elif metric_key == "debt_to_equity":
                    avg_text = f"{sector_label}: {avg:.2f}x"
                else:
                    avg_text = f"{sector_label}: {avg:.2f}"
                draw.text((ax + 14, y), avg_text, fill=TEXT_DIM, font=FONT_TINY)
                if val is not None:
                    higher_better = metric_key != "debt_to_equity"
                    is_good = (val > avg) == higher_better
                    icon = "+" if is_good else "-"
                    icon_color = GREEN if is_good else RED
                    tw = draw.textlength(avg_text, font=FONT_TINY)
                    draw.text((ax + 14 + tw + 6, y), icon, fill=icon_color, font=FONT_TINY)
        y += 18

    y += SECTION_GAP - 6

    # Management plans
    if plans:
        _draw_divider(draw, PAD, y, INNER)
        y += 10
        draw.text((PAD, y), "MANAGEMENT TARGETS", fill=TEXT_MUTED, font=FONT_LABEL)
        y += 22
        for plan in plans[:4]:
            draw.ellipse((PAD + 8, y + 6, PAD + 14, y + 12), fill=PURPLE)
            display = plan
            max_w = INNER - 30
            while draw.textlength(display, font=FONT_SMALL) > max_w and len(display) > 10:
                display = display[:-4] + "..."
            draw.text((PAD + 22, y), display, fill=TEXT_SECONDARY, font=FONT_SMALL)
            y += 24
        y += SECTION_GAP - 8

    # Chairman's outlook
    if outlook:
        _draw_divider(draw, PAD, y, INNER)
        y += 10
        draw.text((PAD, y), "CHAIRMAN'S OUTLOOK", fill=TEXT_MUTED, font=FONT_LABEL)
        y += 22
        wrapped = _wrap_text(outlook, FONT_SMALL, INNER - 28)
        for line in wrapped:
            draw.text((PAD + 14, y), line, fill=TEXT_MUTED, font=FONT_SMALL)
            y += 20
        y += SECTION_GAP - 8

    # Key risks
    if risks:
        _draw_divider(draw, PAD, y, INNER)
        y += 10
        draw.text((PAD, y), "KEY RISKS", fill=TEXT_MUTED, font=FONT_LABEL)
        y += 22
        for risk in risks[:3]:
            draw.ellipse((PAD + 8, y + 6, PAD + 14, y + 12), fill=RED)
            display = risk
            max_w = INNER - 30
            while draw.textlength(display, font=FONT_SMALL) > max_w and len(display) > 10:
                display = display[:-4] + "..."
            draw.text((PAD + 22, y), display, fill=TEXT_SECONDARY, font=FONT_SMALL)
            y += 24
        y += SECTION_GAP - 8

    # News cross-references
    if news_matches:
        _draw_divider(draw, PAD, y, INNER)
        y += 10
        draw.text((PAD, y), "NEWS vs MANAGEMENT PLANS", fill=AMBER, font=FONT_LABEL)
        y += 22
        for match in news_matches[:3]:
            plan_short = match["plan"]
            if len(plan_short) > 60:
                plan_short = plan_short[:57] + "..."
            draw.text((PAD + 8, y), f"Plan: {plan_short}", fill=PURPLE, font=FONT_TINY)
            y += 18
            src = match.get("source", "")
            stw = draw.textlength(src, font=FONT_TINY)
            _rounded_rect(draw, (PAD + 8, y, PAD + 8 + stw + 10, y + 18), BG_ACCENT, radius=4)
            draw.text((PAD + 13, y + 1), src, fill=BLUE, font=FONT_TINY)
            hl = match.get("headline", "")
            if len(hl) > 70:
                hl = hl[:67] + "..."
            draw.text((PAD + 22 + stw, y + 1), hl, fill=TEXT_SECONDARY, font=FONT_TINY)
            y += 22
            y += 8

    # Footer
    y += 4
    _draw_footer(draw, y, WIDTH, PAD)
    actual_h = y + 34
    img = img.crop((0, 0, WIDTH, actual_h))

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ==========================================================================
# Compare card
# ==========================================================================

def _get_fin_value(fin: dict, key: str) -> float | None:
    """Extract value from a financials entry that may be a dict or scalar."""
    v = fin.get(key)
    if isinstance(v, dict):
        return v.get("value")
    return v


def _get_fin_yoy(fin: dict, key: str) -> float | None:
    """Extract YoY change from a financials entry."""
    v = fin.get(key)
    if isinstance(v, dict):
        return v.get("yoy_change")
    return None


def _fmt_compare_val(val, is_lkr: bool, label: str) -> str:
    """Format a comparison value."""
    if val is None:
        return "N/A"
    if is_lkr:
        return _fmt_lkr(val)
    if label in ("ROE",):
        return f"{val:.1f}%"
    if label in ("D/E RATIO",):
        return f"{val:.2f}x"
    if label in ("EPS", "NAV", "DPS"):
        return f"LKR {val:.2f}"
    return f"{val}"


def generate_compare_card(
    ticker1: str, report1: dict,
    ticker2: str, report2: dict,
) -> BytesIO:
    """Generate a side-by-side comparison card for two stocks."""
    WIDTH = 800
    PAD = 30
    INNER = WIDTH - 2 * PAD
    SECTION_GAP = 16

    fin1 = report1.get("financials", {})
    fin2 = report2.get("financials", {})

    metrics = [
        ("REVENUE", _get_fin_value(fin1, "revenue"), _get_fin_value(fin2, "revenue"),
         _get_fin_yoy(fin1, "revenue"), _get_fin_yoy(fin2, "revenue"), True),
        ("NET PROFIT", _get_fin_value(fin1, "net_profit"), _get_fin_value(fin2, "net_profit"),
         _get_fin_yoy(fin1, "net_profit"), _get_fin_yoy(fin2, "net_profit"), True),
        ("EPS", fin1.get("eps"), fin2.get("eps"), None, None, False),
        ("NAV", fin1.get("nav"), fin2.get("nav"), None, None, False),
        ("DPS", fin1.get("dividend_per_share"), fin2.get("dividend_per_share"), None, None, False),
        ("ROE", fin1.get("roe"), fin2.get("roe"), None, None, False),
        ("D/E RATIO", fin1.get("debt_to_equity"), fin2.get("debt_to_equity"), None, None, False),
    ]

    ROW_H = 44
    h = 24 + 50 + SECTION_GAP  # header
    h += 30  # column headers
    h += len(metrics) * ROW_H
    h += SECTION_GAP + 40  # footer

    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    # Header
    draw.rectangle([(0, 0), (WIDTH, 4)], fill=PURPLE)
    draw.text((PAD, y), "ANNUAL REPORT COMPARISON", fill=TEXT_DIM, font=FONT_BRAND)
    y += 26

    col_left = PAD + 160
    col_right = PAD + 160 + (INNER - 160) // 2
    draw.text((col_left, y), ticker1, fill=TEXT_PRIMARY, font=FONT_TICKER)
    draw.text((col_right, y), ticker2, fill=TEXT_PRIMARY, font=FONT_TICKER)

    y += 36
    name1 = report1.get("company", "")
    name2 = report2.get("company", "")
    if len(name1) > 25:
        name1 = name1[:22] + "..."
    if len(name2) > 25:
        name2 = name2[:22] + "..."
    draw.text((col_left, y), name1, fill=TEXT_MUTED, font=FONT_TINY)
    draw.text((col_right, y), name2, fill=TEXT_MUTED, font=FONT_TINY)
    y += 20 + SECTION_GAP

    # Column headers
    draw.text((PAD, y + 4), "METRIC", fill=TEXT_DIM, font=FONT_LABEL)
    _draw_divider(draw, PAD, y + 24, INNER)
    y += 30

    for label, v1, v2, yoy1, yoy2, is_lkr in metrics:
        _rounded_rect(draw, (PAD, y, WIDTH - PAD, y + ROW_H - 4), BG_SURFACE, radius=6)
        draw.text((PAD + 14, y + 12), label, fill=TEXT_MUTED, font=FONT_LABEL)

        s1 = _fmt_compare_val(v1, is_lkr, label)
        s2 = _fmt_compare_val(v2, is_lkr, label)

        c1, c2 = TEXT_PRIMARY, TEXT_PRIMARY
        if v1 is not None and v2 is not None:
            if label == "D/E RATIO":
                if v1 < v2:
                    c1 = GREEN
                elif v2 < v1:
                    c2 = GREEN
            else:
                if v1 > v2:
                    c1 = GREEN
                elif v2 > v1:
                    c2 = GREEN

        draw.text((col_left, y + 10), s1, fill=c1, font=FONT_VALUE)
        draw.text((col_right, y + 10), s2, fill=c2, font=FONT_VALUE)

        if yoy1 is not None:
            vw = draw.textlength(s1, font=FONT_VALUE)
            _yoy_pill(draw, col_left + vw + 8, y + 14, yoy1)
        if yoy2 is not None:
            vw = draw.textlength(s2, font=FONT_VALUE)
            _yoy_pill(draw, col_right + vw + 8, y + 14, yoy2)

        y += ROW_H

    y += SECTION_GAP // 2
    _draw_footer(draw, y, WIDTH, PAD)
    actual_h = y + 34
    img = img.crop((0, 0, WIDTH, actual_h))

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ==========================================================================
# Sector card
# ==========================================================================

def generate_sector_card(
    sector: str,
    companies: dict,  # {ticker: report_data}
    benchmarks: dict,  # sector benchmark data
) -> BytesIO:
    """Generate a sector analysis card with benchmarks and company comparison."""
    WIDTH = 800
    PAD = 30
    INNER = WIDTH - 2 * PAD
    SECTION_GAP = 16
    ROW_H = 36

    bm = benchmarks.get("metrics", {})
    n = benchmarks.get("company_count", len(companies))
    tickers = list(companies.keys())

    # Height calculation
    h = 24 + 50 + SECTION_GAP  # header
    h += 62 + 10 + 62 + SECTION_GAP  # benchmark summary (2 rows of 3 boxes)
    h += 26  # table header
    h += len(tickers) * ROW_H + SECTION_GAP  # company rows
    h += 100  # best/worst section
    h += 40  # footer

    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    # Header
    draw.rectangle([(0, 0), (WIDTH, 4)], fill=PURPLE)
    draw.text((PAD, y), "SECTOR ANALYSIS", fill=TEXT_DIM, font=FONT_BRAND)
    draw.text((WIDTH - PAD, y + 1), f"{n} companies", fill=TEXT_DIM, font=FONT_TINY, anchor="rt")
    y += 26
    draw.text((PAD, y), sector, fill=TEXT_PRIMARY, font=FONT_TICKER)
    y += 32 + SECTION_GAP

    # Benchmark boxes -- row 1: ROE, Revenue Growth, Profit Margin
    box_w3 = (INNER - 16) // 3
    BOX_H = 62
    row1 = [
        ("ROE", bm.get("roe"), "%"),
        ("REVENUE GROWTH", bm.get("revenue_growth"), "%"),
        ("PROFIT MARGIN", bm.get("profit_margin"), "%"),
    ]
    for i, (label, m, unit) in enumerate(row1):
        x = PAD + i * (box_w3 + 8)
        _rounded_rect(draw, (x, y, x + box_w3, y + BOX_H), BG_SURFACE, radius=8)
        draw.text((x + 14, y + 8), f"AVG {label}", fill=TEXT_MUTED, font=FONT_LABEL)
        if m and m.get("avg") is not None:
            draw.text((x + 14, y + 30), f"{m['avg']:.1f}{unit}", fill=TEXT_PRIMARY, font=FONT_VALUE)
            range_text = f"Range: {m['min']:.1f} to {m['max']:.1f}"
            draw.text((x + 14, y + 48), range_text, fill=TEXT_DIM, font=FONT_TINY)
        else:
            draw.text((x + 14, y + 30), "N/A", fill=TEXT_MUTED, font=FONT_VALUE)
    y += BOX_H + 10

    # Row 2: EPS, D/E, DPS
    row2 = [
        ("EPS", bm.get("eps"), ""),
        ("DEBT/EQUITY", bm.get("debt_to_equity"), "x"),
        ("DPS", bm.get("dividend_per_share"), ""),
    ]
    for i, (label, m, unit) in enumerate(row2):
        x = PAD + i * (box_w3 + 8)
        _rounded_rect(draw, (x, y, x + box_w3, y + BOX_H), BG_SURFACE, radius=8)
        draw.text((x + 14, y + 8), f"AVG {label}", fill=TEXT_MUTED, font=FONT_LABEL)
        if m and m.get("avg") is not None:
            fmt = f"{m['avg']:.2f}{unit}" if unit else f"LKR {m['avg']:.2f}"
            draw.text((x + 14, y + 30), fmt, fill=TEXT_PRIMARY, font=FONT_VALUE)
            if m.get("min") is not None:
                range_text = f"Range: {m['min']:.2f} to {m['max']:.2f}"
                draw.text((x + 14, y + 48), range_text, fill=TEXT_DIM, font=FONT_TINY)
        else:
            draw.text((x + 14, y + 30), "N/A", fill=TEXT_MUTED, font=FONT_VALUE)
    y += BOX_H + SECTION_GAP

    # Company comparison table
    _draw_divider(draw, PAD, y, INNER)
    y += 10

    # Column positions
    col_ticker = PAD + 10
    col_name = PAD + 70
    col_roe = PAD + INNER - 320
    col_rev = PAD + INNER - 200
    col_eps = PAD + INNER - 80

    draw.text((col_ticker, y), "TICKER", fill=TEXT_DIM, font=FONT_LABEL)
    draw.text((col_roe, y), "ROE", fill=TEXT_DIM, font=FONT_LABEL)
    draw.text((col_rev, y), "REV GROWTH", fill=TEXT_DIM, font=FONT_LABEL)
    draw.text((col_eps, y), "EPS", fill=TEXT_DIM, font=FONT_LABEL)
    y += 26

    roe_avg = bm.get("roe", {}).get("avg")

    for ticker in tickers:
        data = companies[ticker]
        fin = data.get("financials", {})

        _rounded_rect(draw, (PAD, y, WIDTH - PAD, y + ROW_H - 2), BG_SURFACE, radius=4)

        draw.text((col_ticker, y + 8), ticker, fill=TEXT_PRIMARY, font=FONT_SECTION)

        # Company name (truncated)
        name = data.get("company", "")
        if len(name) > 22:
            name = name[:19] + "..."
        draw.text((col_name, y + 9), name, fill=TEXT_MUTED, font=FONT_TINY)

        # ROE with color
        roe = fin.get("roe")
        if roe is not None:
            roe_color = TEXT_PRIMARY
            if roe_avg is not None:
                roe_color = GREEN if roe > roe_avg else RED if roe < roe_avg * 0.7 else AMBER
            draw.text((col_roe, y + 8), f"{roe:.1f}%", fill=roe_color, font=FONT_SECTION)
        else:
            draw.text((col_roe, y + 8), "N/A", fill=TEXT_DIM, font=FONT_SECTION)

        # Revenue growth
        rev = fin.get("revenue", {})
        rev_yoy = rev.get("yoy_change") if isinstance(rev, dict) else None
        if rev_yoy is not None:
            sign = "+" if rev_yoy >= 0 else ""
            color = GREEN if rev_yoy > 0 else RED
            draw.text((col_rev, y + 8), f"{sign}{rev_yoy:.1f}%", fill=color, font=FONT_SECTION)
        else:
            draw.text((col_rev, y + 8), "N/A", fill=TEXT_DIM, font=FONT_SECTION)

        # EPS
        eps = fin.get("eps")
        if eps is not None:
            draw.text((col_eps, y + 8), f"{eps:.2f}", fill=TEXT_PRIMARY, font=FONT_SECTION)
        else:
            draw.text((col_eps, y + 8), "N/A", fill=TEXT_DIM, font=FONT_SECTION)

        y += ROW_H

    y += SECTION_GAP

    # Best/worst performers
    _draw_divider(draw, PAD, y, INNER)
    y += 10
    draw.text((PAD, y), "STANDOUT PERFORMERS", fill=TEXT_MUTED, font=FONT_LABEL)
    y += 22

    for metric_label, metric_key, fmt_fn, higher_is_better in [
        ("ROE", "roe", lambda v: f"{v:.1f}%", True),
        ("Rev Growth", "revenue_growth", lambda v: f"{v:+.1f}%", True),
        ("EPS", "eps", lambda v: f"LKR {v:.2f}", True),
    ]:
        values = []
        for t in tickers:
            fin = companies[t].get("financials", {})
            if metric_key == "revenue_growth":
                rev = fin.get("revenue", {})
                val = rev.get("yoy_change") if isinstance(rev, dict) else None
            else:
                val = fin.get(metric_key)
            if val is not None:
                values.append((t, val))
        if len(values) >= 2:
            best = max(values, key=lambda x: x[1]) if higher_is_better else min(values, key=lambda x: x[1])
            worst = min(values, key=lambda x: x[1]) if higher_is_better else max(values, key=lambda x: x[1])
            if best[0] != worst[0]:
                draw.text((PAD + 8, y), f"Best {metric_label}:", fill=TEXT_MUTED, font=FONT_TINY)
                draw.text((PAD + 130, y), f"{best[0]} ({fmt_fn(best[1])})", fill=GREEN, font=FONT_TINY)
                draw.text((PAD + INNER // 2, y), f"Worst:", fill=TEXT_MUTED, font=FONT_TINY)
                draw.text((PAD + INNER // 2 + 60, y), f"{worst[0]} ({fmt_fn(worst[1])})", fill=RED, font=FONT_TINY)
                y += 22

    # Footer
    y += 8
    _draw_footer(draw, y, WIDTH, PAD)
    actual_h = y + 34
    img = img.crop((0, 0, WIDTH, actual_h))

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ==========================================================================
# Sector stocks listing card
# ==========================================================================

def generate_sector_stocks_card(
    sector: str,
    stocks: list[dict],
) -> BytesIO:
    """Generate a card listing all stocks in a sector with live prices.
    stocks: [{ticker, company_name, last_price, change, change_pct, market_cap}, ...]
    """
    WIDTH = 800
    PAD = 30
    INNER = WIDTH - 2 * PAD
    ROW_H = 34

    stocks = sorted(stocks, key=lambda s: s.get("market_cap") or 0, reverse=True)

    h = 24 + 50 + 12 + 24 + len(stocks) * ROW_H + 12 + 40
    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    # Header
    draw.rectangle([(0, 0), (WIDTH, 4)], fill=BLUE)
    draw.text((PAD, y), "SECTOR STOCKS", fill=TEXT_DIM, font=FONT_BRAND)
    draw.text((WIDTH - PAD, y + 1), f"{len(stocks)} stocks", fill=TEXT_DIM, font=FONT_TINY, anchor="rt")
    y += 26
    draw.text((PAD, y), sector, fill=TEXT_PRIMARY, font=FONT_TICKER)
    y += 32 + 12

    # Column headers
    col_ticker = PAD + 10
    col_name = PAD + 80
    col_price = PAD + INNER - 290
    col_change = PAD + INNER - 170
    col_mcap = PAD + INNER - 60

    draw.text((col_ticker, y), "TICKER", fill=TEXT_DIM, font=FONT_LABEL)
    draw.text((col_price, y), "PRICE", fill=TEXT_DIM, font=FONT_LABEL)
    draw.text((col_change, y), "CHANGE", fill=TEXT_DIM, font=FONT_LABEL)
    draw.text((col_mcap, y), "MCAP", fill=TEXT_DIM, font=FONT_LABEL)
    y += 24

    for s in stocks:
        _rounded_rect(draw, (PAD, y, WIDTH - PAD, y + ROW_H - 2), BG_SURFACE, radius=4)
        draw.text((col_ticker, y + 7), s["ticker"], fill=TEXT_PRIMARY, font=FONT_SECTION)

        name = s.get("company_name") or ""
        if len(name) > 20:
            name = name[:17] + "..."
        draw.text((col_name, y + 8), name, fill=TEXT_MUTED, font=FONT_TINY)

        price = s.get("last_price")
        if price:
            draw.text((col_price, y + 7), f"{price:,.2f}", fill=TEXT_PRIMARY, font=FONT_SECTION)
        else:
            draw.text((col_price, y + 7), "N/A", fill=TEXT_DIM, font=FONT_SECTION)

        chg_pct = s.get("change_pct")
        if chg_pct is not None:
            sign = "+" if chg_pct >= 0 else ""
            color = GREEN if chg_pct >= 0 else RED
            draw.text((col_change, y + 7), f"{sign}{chg_pct:.1f}%", fill=color, font=FONT_SECTION)
        else:
            draw.text((col_change, y + 7), "N/A", fill=TEXT_DIM, font=FONT_SECTION)

        draw.text((col_mcap, y + 7), _format_num(s.get("market_cap")), fill=TEXT_SECONDARY, font=FONT_TINY)
        y += ROW_H

    y += 8
    _draw_footer(draw, y, WIDTH, PAD)
    img = img.crop((0, 0, WIDTH, y + 34))

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ==========================================================================
# Group / conglomerate card
# ==========================================================================

def generate_group_card(
    group_name: str,
    parent_ticker: str,
    stocks: list[dict],
) -> BytesIO:
    """Generate a card listing all companies in a business group with live prices.
    stocks: [{ticker, company_name, last_price, change, change_pct, market_cap}, ...]
    """
    WIDTH = 800
    PAD = 30
    INNER = WIDTH - 2 * PAD
    ROW_H = 34

    stocks = sorted(stocks, key=lambda s: (
        0 if s["ticker"] == parent_ticker else 1,
        -(s.get("market_cap") or 0),
    ))

    h = 24 + 50 + 12 + 24 + len(stocks) * ROW_H + 12 + 60
    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 24

    # Header
    draw.rectangle([(0, 0), (WIDTH, 4)], fill=PURPLE)
    draw.text((PAD, y), "BUSINESS GROUP", fill=TEXT_DIM, font=FONT_BRAND)
    draw.text((WIDTH - PAD, y + 1), f"{len(stocks)} listed companies", fill=TEXT_DIM, font=FONT_TINY, anchor="rt")
    y += 26
    draw.text((PAD, y), group_name, fill=TEXT_PRIMARY, font=FONT_TICKER)
    y += 32 + 12

    col_ticker = PAD + 10
    col_name = PAD + 80
    col_price = PAD + INNER - 310
    col_change = PAD + INNER - 190
    col_mcap = PAD + INNER - 80

    draw.text((col_ticker, y), "TICKER", fill=TEXT_DIM, font=FONT_LABEL)
    draw.text((col_price, y), "PRICE", fill=TEXT_DIM, font=FONT_LABEL)
    draw.text((col_change, y), "CHANGE", fill=TEXT_DIM, font=FONT_LABEL)
    draw.text((col_mcap, y), "MCAP", fill=TEXT_DIM, font=FONT_LABEL)
    y += 24

    for s in stocks:
        is_parent = s["ticker"] == parent_ticker
        bg = BG_ACCENT if is_parent else BG_SURFACE
        _rounded_rect(draw, (PAD, y, WIDTH - PAD, y + ROW_H - 2), bg, radius=4)

        label = s["ticker"] + (" *" if is_parent else "")
        draw.text((col_ticker, y + 7), label, fill=TEXT_PRIMARY, font=FONT_SECTION)

        name = s.get("company_name") or ""
        if len(name) > 22:
            name = name[:19] + "..."
        draw.text((col_name, y + 8), name, fill=TEXT_MUTED, font=FONT_TINY)

        price = s.get("last_price")
        if price:
            draw.text((col_price, y + 7), f"LKR {price:,.2f}", fill=TEXT_PRIMARY, font=FONT_SECTION)
        else:
            draw.text((col_price, y + 7), "N/A", fill=TEXT_DIM, font=FONT_SECTION)

        chg_pct = s.get("change_pct")
        if chg_pct is not None:
            sign = "+" if chg_pct >= 0 else ""
            color = GREEN if chg_pct >= 0 else RED
            draw.text((col_change, y + 7), f"{sign}{chg_pct:.1f}%", fill=color, font=FONT_SECTION)
        else:
            draw.text((col_change, y + 7), "N/A", fill=TEXT_DIM, font=FONT_SECTION)

        draw.text((col_mcap, y + 7), _format_num(s.get("market_cap")), fill=TEXT_SECONDARY, font=FONT_TINY)
        y += ROW_H

    y += 4
    draw.text((PAD + 10, y), "* Parent / holding company", fill=TEXT_DIM, font=FONT_TINY)
    y += 20
    _draw_footer(draw, y, WIDTH, PAD)
    img = img.crop((0, 0, WIDTH, y + 34))

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf
