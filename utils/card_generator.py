"""
CeylonVest Pulse Card Generator
Premium fintech-style ticker cards with Inter font family.
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


# Typography scale
FONT_BRAND    = _font("Inter-Bold.ttf", 11)
FONT_TICKER   = _font("InterDisplay-Bold.ttf", 26)
FONT_COMPANY  = _font("Inter-Regular.ttf", 13)
FONT_PRICE    = _font("InterDisplay-Bold.ttf", 34)
FONT_CHANGE   = _font("Inter-SemiBold.ttf", 15)
FONT_LABEL    = _font("Inter-Medium.ttf", 11)
FONT_VALUE    = _font("Inter-SemiBold.ttf", 15)
FONT_SECTION  = _font("Inter-SemiBold.ttf", 12)
FONT_SMALL    = _font("Inter-Regular.ttf", 11)
FONT_TINY     = _font("Inter-Regular.ttf", 10)
FONT_ALERT    = _font("Inter-SemiBold.ttf", 12)


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

def _rounded_rect(draw, xy, fill, radius=8, outline=None):
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
    _rounded_rect(draw, (x, y, x+w, y+h), BG_SURFACE, radius=6)
    draw.text((x + 10, y + 8), label, fill=TEXT_MUTED, font=FONT_LABEL)
    draw.text((x + 10, y + 24), value, fill=value_color, font=FONT_VALUE)


def _draw_sparkline(draw, x, y, w, h, points, color):
    if not points or len(points) < 2:
        return
    _rounded_rect(draw, (x, y, x+w, y+h), BG_ACCENT, radius=4)
    values = [(lo + hi) / 2 for lo, hi in points if lo and hi]
    if len(values) < 2:
        return
    v_min = min(values) * 0.998
    v_max = max(values) * 1.002
    v_range = v_max - v_min if v_max > v_min else 1
    pad_x, pad_y = 6, 6
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
    draw.ellipse((ex-3, ey-3, ex+3, ey+3), fill=color)
    draw.ellipse((ex-5, ey-5, ex+5, ey+5), outline=color, width=1)


def _draw_divider(draw, x, y, w, style="line"):
    if style == "line":
        draw.line([(x, y), (x + w, y)], fill=BORDER, width=1)
    elif style == "dots":
        for dx in range(0, w, 8):
            draw.ellipse((x+dx, y, x+dx+2, y+2), fill=BORDER)


def _draw_footer(draw, y, width, pad):
    inner = width - 2 * pad
    _draw_divider(draw, pad, y, inner, style="dots")
    y += 8
    draw.text((pad, y), "ceylonvest.com", fill=TEXT_DIM, font=FONT_TINY)
    draw.text((width - pad, y), "AI-powered market intelligence",
              fill=TEXT_DIM, font=FONT_TINY, anchor="rt")


def _draw_header(draw, y, width, pad, ticker, section_name, company_name=None):
    """Draw the standard card header: brand accent bar + section title."""
    draw.rectangle([(0, 0), (width, 3)], fill=BRAND_ACCENT)
    draw.text((pad, y), f"{ticker} {section_name}", fill=TEXT_DIM, font=FONT_BRAND)
    if company_name:
        hw = draw.textlength(f"{ticker} {section_name}  ", font=FONT_BRAND)
        draw.text((pad + hw, y), company_name, fill=TEXT_DIM, font=FONT_TINY)


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
    WIDTH = 520
    PAD = 20
    INNER = WIDTH - 2 * PAD
    has_pe = pe_ratio is not None
    has_sparkline = sparkline_points and len(sparkline_points) >= 2

    # Calculate height
    h = 18 + 20 + 8 + 34 + 8 + 44 + 14 + 54  # header through metrics
    if has_sparkline:
        h += 12 + 70
    h += 14
    if price_position_52w is not None:
        h += 34 + 10
    h += 1 + 12 + 68  # divider + sentiment
    if is_pump_alert:
        h += 10 + 42
    h += 12 + 16 + 14  # footer

    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 18

    # Brand bar
    draw.rectangle([(0, 0), (WIDTH, 3)], fill=BRAND_ACCENT)
    draw.text((PAD, y), "CEYLONVEST PULSE", fill=TEXT_DIM, font=FONT_BRAND)
    sector_text = sector.upper()
    stw = draw.textlength(sector_text, font=FONT_TINY)
    pill_x = WIDTH - PAD - stw - 16
    _rounded_rect(draw, (pill_x, y-2, WIDTH-PAD, y+15), BG_SURFACE, radius=8, outline=BORDER)
    draw.text((pill_x + 8, y), sector_text, fill=TEXT_SECONDARY, font=FONT_TINY)
    y += 24

    # Ticker + company
    draw.text((PAD, y), ticker, fill=TEXT_PRIMARY, font=FONT_TICKER)
    tw = draw.textlength(ticker, font=FONT_TICKER)
    draw.text((PAD + tw + 10, y + 10), company_name, fill=TEXT_MUTED, font=FONT_COMPANY)
    y += 38

    # Price + change pill
    price_str = f"LKR {last_price:,.2f}"
    draw.text((PAD, y), price_str, fill=TEXT_PRIMARY, font=FONT_PRICE)
    pw = draw.textlength(price_str, font=FONT_PRICE)
    sign = "+" if change >= 0 else ""
    pill_text = f"{sign}{change:.2f}  {sign}{change_pct:.2f}%"
    ptw = draw.textlength(pill_text, font=FONT_CHANGE)
    cpx = PAD + pw + 14
    _rounded_rect(draw, (cpx, y+8, cpx+ptw+16, y+30), _change_bg(change), radius=6)
    draw.text((cpx + 8, y + 10), pill_text, fill=_change_color(change), font=FONT_CHANGE)
    y += 48

    # Metric boxes
    if has_pe:
        box_w = (INNER - 18) // 4
        metrics = [("MKT CAP", _format_num(market_cap)), ("VOLUME", _format_num(volume)),
                   ("P/E", f"{pe_ratio:.1f}x"), ("SPREAD", f"{spread_pct:.1f}%" if spread_pct else "N/A")]
    else:
        box_w = (INNER - 12) // 3
        metrics = [("MKT CAP", _format_num(market_cap)), ("VOLUME", _format_num(volume)),
                   ("SPREAD", f"{spread_pct:.1f}%" if spread_pct else "N/A")]
    for i, (lbl, val) in enumerate(metrics):
        _draw_metric(draw, PAD + i*(box_w+6), y, box_w, 48, lbl, val)
    y += 58

    # Sparkline
    if has_sparkline:
        draw.text((PAD, y-2), "PRICE TREND", fill=TEXT_MUTED, font=FONT_LABEL)
        draw.text((WIDTH-PAD, y-2), f"Today: {low:.1f} – {high:.1f}",
                  fill=TEXT_MUTED, font=FONT_TINY, anchor="rt")
        y += 14
        _draw_sparkline(draw, PAD, y, INNER, 60, sparkline_points,
                       GREEN if change >= 0 else RED)
        y += 66

    # 52-week range
    if price_position_52w is not None:
        draw.text((PAD, y), "52-WEEK RANGE", fill=TEXT_MUTED, font=FONT_LABEL)
        draw.text((WIDTH-PAD, y), f"{price_position_52w:.0f}%",
                  fill=TEXT_SECONDARY, font=FONT_LABEL, anchor="rt")
        y += 16
        _rounded_rect(draw, (PAD, y, WIDTH-PAD, y+6), BG_ACCENT, radius=3)
        fill_w = max(6, int(INNER * price_position_52w / 100))
        bar_c = GREEN if price_position_52w > 50 else AMBER if price_position_52w > 25 else RED
        _rounded_rect(draw, (PAD, y, PAD+fill_w, y+6), bar_c, radius=3)
        y += 9
        draw.text((PAD, y), f"{low_52w:.1f}", fill=TEXT_DIM, font=FONT_TINY)
        draw.text((WIDTH-PAD, y), f"{high_52w:.1f}", fill=TEXT_DIM, font=FONT_TINY, anchor="rt")
        y += 14

    # Divider
    _draw_divider(draw, PAD, y, INNER)
    y += 14

    # Sentiment
    draw.text((PAD, y), "PULSE SENTIMENT", fill=TEXT_MUTED, font=FONT_LABEL)
    if sentiment_score is not None:
        sc = GREEN if sentiment_score > 0.1 else RED if sentiment_score < -0.1 else AMBER
        score_str = f"{sentiment_score:+.2f}"
        stw = draw.textlength(score_str, font=FONT_VALUE)
        sx = WIDTH - PAD - stw - 12
        sbg = GREEN_DIM if sentiment_score > 0.1 else RED_DIM if sentiment_score < -0.1 else BG_SURFACE
        _rounded_rect(draw, (sx, y-2, WIDTH-PAD, y+16), sbg, radius=6)
        draw.text((sx + 6, y), score_str, fill=sc, font=FONT_VALUE)
    y += 22
    bar_w = INNER
    _rounded_rect(draw, (PAD, y, PAD+bar_w, y+4), BG_ACCENT, radius=2)
    if sentiment_score is not None:
        fill_pct = (sentiment_score + 1) / 2
        fill_w = max(4, int(bar_w * fill_pct))
        sc = GREEN if sentiment_score > 0.1 else RED if sentiment_score < -0.1 else AMBER
        _rounded_rect(draw, (PAD, y, PAD+fill_w, y+4), sc, radius=2)
    y += 12

    mc_str = str(mention_count_24h)
    draw.text((PAD, y), mc_str, fill=TEXT_PRIMARY, font=FONT_VALUE)
    mcw = draw.textlength(mc_str, font=FONT_VALUE)
    draw.text((PAD+mcw+4, y+3), "mentions 24h", fill=TEXT_MUTED, font=FONT_TINY)
    vel_str = f"{mention_velocity:.1f}x"
    vel_c = AMBER if mention_velocity >= 3 else TEXT_PRIMARY
    mid = PAD + INNER // 2
    draw.text((mid, y), vel_str, fill=vel_c, font=FONT_VALUE)
    vw = draw.textlength(vel_str, font=FONT_VALUE)
    draw.text((mid+vw+4, y+3), "vs avg", fill=TEXT_MUTED, font=FONT_TINY)
    draw.text((WIDTH-PAD, y+3), f"prev {prev_close:.2f}", fill=TEXT_DIM,
              font=FONT_TINY, anchor="rt")
    y += 24

    # Pump alert
    if is_pump_alert:
        y += 4
        _rounded_rect(draw, (PAD, y, WIDTH-PAD, y+36), ALERT_BG, radius=6, outline=RED)
        draw.ellipse((PAD+12, y+14, PAD+18, y+20), fill=RED)
        draw.text((PAD+24, y+10), "PUMP ALERT", fill=RED, font=FONT_ALERT)
        atw = draw.textlength("PUMP ALERT  ", font=FONT_ALERT)
        draw.text((PAD+24+atw, y+11),
                  pump_alert_text or "High velocity, concentrated sources",
                  fill=TEXT_SECONDARY, font=FONT_SMALL)
        y += 42

    # Footer
    y += 4
    _draw_footer(draw, y, WIDTH, PAD)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ==========================================================================
# Fundamentals card
# ==========================================================================

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
    WIDTH = 520
    PAD = 20
    INNER = WIDTH - 2 * PAD

    has_data = any(v is not None for v in [eps, book_value, nav, pb_ratio,
                                            div_yield, foreign_pct])
    if not has_data:
        return _generate_coming_soon_card(ticker, "FUNDAMENTALS",
            "Fundamentals data coming soon\n\n"
            "We're building the data source for EPS,\n"
            "book value, NAV, P/B, and dividend yield.\n\n"
            "This will be available once we connect\n"
            "to CSE quarterly filings.")

    HEIGHT = 340
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    y = 18

    _draw_header(draw, y, WIDTH, PAD, ticker, "FUNDAMENTALS")
    y += 28

    # 2x2 grid
    box_w = (INNER - 6) // 2
    _draw_metric(draw, PAD, y, box_w, 48, "EPS (TTM)",
                 f"LKR {eps:.2f}" if eps else "N/A")
    _draw_metric(draw, PAD+box_w+6, y, box_w, 48, "BOOK VALUE",
                 f"LKR {book_value:.2f}" if book_value else "N/A")
    y += 56
    _draw_metric(draw, PAD, y, box_w, 48, "NAV / SHARE",
                 f"LKR {nav:.2f}" if nav else "N/A")
    _draw_metric(draw, PAD+box_w+6, y, box_w, 48, "P/B RATIO",
                 f"{pb_ratio:.2f}x" if pb_ratio else "N/A",
                 GREEN if pb_ratio and pb_ratio < 1 else TEXT_PRIMARY)
    y += 56

    # Dividend row
    _rounded_rect(draw, (PAD, y, WIDTH-PAD, y+48), BG_SURFACE, radius=6)
    draw.text((PAD+10, y+8), "DIV YIELD", fill=TEXT_MUTED, font=FONT_LABEL)
    draw.text((PAD+10, y+24), f"{div_yield:.1f}%" if div_yield else "N/A",
              fill=GREEN if div_yield and div_yield > 2 else TEXT_PRIMARY, font=FONT_VALUE)
    draw.text((WIDTH-PAD-10, y+8), "NEXT EX-DATE", fill=TEXT_MUTED,
              font=FONT_LABEL, anchor="rt")
    draw.text((WIDTH-PAD-10, y+24), div_ex_date or "N/A",
              fill=TEXT_PRIMARY, font=FONT_VALUE, anchor="rt")
    y += 56

    # Foreign/local bar
    _rounded_rect(draw, (PAD, y, WIDTH-PAD, y+56), BG_SURFACE, radius=6)
    draw.text((PAD+10, y+8), "FOREIGN / LOCAL RATIO", fill=TEXT_MUTED, font=FONT_LABEL)
    bar_y = y + 26
    bar_w = INNER - 100
    _rounded_rect(draw, (PAD+10, bar_y, PAD+10+bar_w, bar_y+6), BG_ACCENT, radius=3)
    if foreign_pct:
        f_w = int(bar_w * foreign_pct / 100)
        _rounded_rect(draw, (PAD+10, bar_y, PAD+10+f_w, bar_y+6), BLUE, radius=3)
        _rounded_rect(draw, (PAD+10+f_w, bar_y, PAD+10+bar_w, bar_y+6), GREEN, radius=3)
    if foreign_pct and local_pct:
        ratio_text = f"{foreign_pct:.0f}% / {local_pct:.0f}%"
    elif foreign_pct:
        ratio_text = f"{foreign_pct:.0f}% foreign"
    else:
        ratio_text = "N/A"
    draw.text((WIDTH-PAD-10, bar_y), ratio_text, fill=TEXT_MUTED, font=FONT_SMALL, anchor="rt")
    if foreign_net:
        draw.text((PAD+10, bar_y+14), foreign_net, fill=TEXT_MUTED, font=FONT_TINY)
    y += 64

    # Footer
    _draw_footer(draw, y, WIDTH, PAD)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


def _generate_coming_soon_card(ticker: str, section: str, message: str) -> BytesIO:
    WIDTH = 520
    PAD = 20
    HEIGHT = 200

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    y = 18

    _draw_header(draw, y, WIDTH, PAD, ticker, section)
    y += 36

    _rounded_rect(draw, (PAD, y, WIDTH-PAD, HEIGHT-32), BG_SURFACE, radius=8)
    for i, line in enumerate(message.split("\n")):
        color = TEXT_SECONDARY if i == 0 else TEXT_MUTED
        font = FONT_SECTION if i == 0 else FONT_SMALL
        draw.text((PAD + 16, y + 12 + i * 20), line, fill=color, font=font)

    _draw_footer(draw, HEIGHT - 26, WIDTH, PAD)

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
    WIDTH = 520
    PAD = 20
    INNER = WIDTH - 2 * PAD

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
    h = 18          # top pad
    h += 22         # header
    h += 44         # price
    h += 6
    h += 16         # "PRICE RANGES" label
    h += len(valid_ranges) * 28 + 8
    h += 56         # support/resistance
    h += 8
    h += 56         # metrics row
    if price_position_52w is not None:
        h += 8 + 34
    h += 12 + 16 + 14  # footer

    img = Image.new("RGB", (WIDTH, h), BG)
    draw = ImageDraw.Draw(img)
    y = 18

    # Header
    _draw_header(draw, y, WIDTH, PAD, ticker, "TECHNICALS", company_name)
    y += 26

    # Price + change pill
    price_str = f"LKR {last_price:,.2f}"
    draw.text((PAD, y), price_str, fill=TEXT_PRIMARY, font=FONT_PRICE)
    pw = draw.textlength(price_str, font=FONT_PRICE)
    sign = "+" if change >= 0 else ""
    pill_text = f"{sign}{change:.2f}  {sign}{change_pct:.2f}%"
    ptw = draw.textlength(pill_text, font=FONT_CHANGE)
    cpx = PAD + pw + 14
    _rounded_rect(draw, (cpx, y+8, cpx+ptw+16, y+30), _change_bg(change), radius=6)
    draw.text((cpx + 8, y + 10), pill_text, fill=_change_color(change), font=FONT_CHANGE)
    y += 48

    # Range rows
    draw.text((PAD, y), "PRICE RANGES", fill=TEXT_MUTED, font=FONT_LABEL)
    y += 18

    label_w = 40
    bar_start = PAD + label_w + 8
    bar_end = WIDTH - PAD - 70
    bar_w = bar_end - bar_start

    for label, r_low, r_high in valid_ranges:
        draw.text((PAD, y + 4), label, fill=TEXT_MUTED, font=FONT_SMALL)
        draw.text((bar_start - 4, y + 4), f"{r_low:.1f}",
                  fill=TEXT_MUTED, font=FONT_SMALL, anchor="rt")

        bar_y = y + 8
        _rounded_rect(draw, (bar_start, bar_y, bar_start+bar_w, bar_y+6), BG_ACCENT, radius=3)

        bar_color = GREEN if change >= 0 else RED
        if r_high > r_low and r_low <= last_price <= r_high:
            pos = (last_price - r_low) / (r_high - r_low)
            fill_w = max(4, int(bar_w * pos))
            _rounded_rect(draw, (bar_start, bar_y, bar_start+fill_w, bar_y+6), bar_color, radius=3)
            dot_x = bar_start + fill_w
            draw.ellipse((dot_x-3, bar_y-1, dot_x+3, bar_y+7), fill=TEXT_PRIMARY)
        elif last_price > r_high:
            _rounded_rect(draw, (bar_start, bar_y, bar_start+bar_w, bar_y+6), GREEN, radius=3)
        elif last_price < r_low:
            _rounded_rect(draw, (bar_start, bar_y, bar_start+4, bar_y+6), RED, radius=3)

        draw.text((bar_start + bar_w + 6, y + 4), f"{r_high:.1f}",
                  fill=TEXT_MUTED, font=FONT_SMALL)
        y += 28

    y += 4

    # Support / Resistance
    box_w = (INNER - 6) // 2
    s_text = f"LKR {support:.2f}" if support else "N/A"
    s_color = GREEN if support and last_price > support else TEXT_PRIMARY
    _draw_metric(draw, PAD, y, box_w, 48, "SUPPORT (MTD LOW)", s_text, s_color)

    r_text = f"LKR {resistance:.2f}" if resistance else "N/A"
    r_color = RED if resistance and last_price < resistance else TEXT_PRIMARY
    _draw_metric(draw, PAD+box_w+6, y, box_w, 48, "RESISTANCE (MTD HIGH)", r_text, r_color)
    y += 56

    # Beta + volume metrics
    y += 4
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
        m_box_w = (INNER - 6 * (len(visible) - 1)) // len(visible)
        for i, (m_lbl, m_val, m_clr) in enumerate(visible):
            _draw_metric(draw, PAD + i*(m_box_w+6), y, m_box_w, 48, m_lbl, m_val, m_clr)
    y += 56

    # 52W position bar
    if price_position_52w is not None:
        draw.text((PAD, y), "52-WEEK POSITION", fill=TEXT_MUTED, font=FONT_LABEL)
        draw.text((WIDTH-PAD, y), f"{price_position_52w:.0f}%",
                  fill=TEXT_SECONDARY, font=FONT_LABEL, anchor="rt")
        y += 16
        _rounded_rect(draw, (PAD, y, PAD+INNER, y+8), BG_ACCENT, radius=4)
        fill_w = max(6, int(INNER * price_position_52w / 100))
        bar_c = GREEN if price_position_52w > 50 else AMBER if price_position_52w > 25 else RED
        _rounded_rect(draw, (PAD, y, PAD+fill_w, y+8), bar_c, radius=4)
        y += 16

    # Footer
    y += 4
    _draw_footer(draw, y, WIDTH, PAD)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf
