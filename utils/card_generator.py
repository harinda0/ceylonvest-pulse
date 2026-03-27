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
    y += 48 + 12

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
