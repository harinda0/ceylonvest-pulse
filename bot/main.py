"""
CeylonVest Pulse — Telegram Bot
Paste a ticker, get instant market intelligence.
"""

import os
import time
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)

from utils.ticker_map import resolve_ticker, resolve_input, check_delisted, get_cse_symbol, get_sector, get_company_name, TICKER_TO_CSE
from services.cse_api import get_stock_data, compute_support_resistance, clear_cache
from services.pulse_db import (
    get_mention_velocity,
    get_avg_sentiment,
    get_sentiment_trend_7d,
    get_most_bullish_bearish,
    add_watchlist,
    remove_watchlist,
    get_watchlist,
)
from utils.card_generator import generate_main_card, generate_company_info_card, generate_technicals_card, generate_report_card, generate_compare_card

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pulse")

# --- Rate limiting: max 5 requests per user per 60 seconds ---
_user_timestamps: dict[int, list[float]] = {}
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 60  # seconds


def _get_admin_id() -> int | None:
    """Get the admin Telegram user ID from env."""
    val = os.getenv("ADMIN_TELEGRAM_ID")
    return int(val) if val else None


def _is_rate_limited(user_id: int) -> bool:
    """Check if a user has exceeded the rate limit. Returns True if blocked."""
    now = time.time()
    timestamps = _user_timestamps.get(user_id, [])
    # Prune old timestamps outside the window
    timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(timestamps) >= RATE_LIMIT_MAX:
        _user_timestamps[user_id] = timestamps
        return True
    timestamps.append(now)
    _user_timestamps[user_id] = timestamps
    return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome = (
        "Welcome to CeylonVest Pulse\n\n"
        "Paste any CSE ticker or company name to get instant market intelligence.\n\n"
        "Examples:\n"
        "  KPHL\n"
        "  kapruka\n"
        "  john keells\n"
        "  combank\n\n"
        "Commands:\n"
        "/p TICKER — Look up any stock or director (works in groups)\n"
        "/report TICKER — Annual report summary\n"
        "/compare TICKER1 TICKER2 — Side-by-side comparison\n"
        "/market — Today's market summary\n"
        "/watchlist — View your watchlist\n"
        "/addwatch TICKER — Add to watchlist\n"
        "/removewatch TICKER — Remove from watchlist\n"
        "/help — Show this message"
    )
    await update.message.reply_text(welcome)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await start_command(update, context)


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /market — show overall market summary."""
    from services.cse_api import fetch_market_summary

    await update.message.reply_text("Fetching market data...")

    data = fetch_market_summary()
    if not data:
        await update.message.reply_text("Could not fetch market data. Try again shortly.")
        return

    text = "CSE Market Summary\n\n"

    # ASPI
    aspi = data.get("aspi")
    if aspi:
        val = float(aspi.get("value", aspi.get("indexValue", 0)))
        chg = float(aspi.get("change", 0))
        pct = float(aspi.get("percentage", aspi.get("changePercentage", 0)))
        sign = "+" if chg >= 0 else ""
        text += f"ASPI: {val:,.2f} ({sign}{chg:,.2f} / {sign}{pct:.2f}%)\n"

    # S&P SL20
    snp = data.get("snp")
    if snp:
        val = float(snp.get("value", snp.get("indexValue", 0)))
        chg = float(snp.get("change", 0))
        pct = float(snp.get("percentage", snp.get("changePercentage", 0)))
        sign = "+" if chg >= 0 else ""
        text += f"S&P SL20: {val:,.2f} ({sign}{chg:,.2f} / {sign}{pct:.2f}%)\n"

    # Trade summary (dailyMarketSummery returns list of lists)
    trade_raw = data.get("trade")
    if trade_raw and isinstance(trade_raw, list) and trade_raw and isinstance(trade_raw[0], list) and trade_raw[0]:
        t = trade_raw[0][0]  # First entry of first list
        turnover = float(t.get("marketTurnover", 0))
        volume = float(t.get("volumeOfTurnOverNumber", 0))
        trades = int(t.get("marketTrades", 0))
        text += "\n"
        if turnover:
            if turnover >= 1e9:
                text += f"Turnover: LKR {turnover/1e9:.1f}B\n"
            elif turnover >= 1e6:
                text += f"Turnover: LKR {turnover/1e6:.1f}M\n"
            else:
                text += f"Turnover: LKR {turnover:,.0f}\n"
        if volume:
            if volume >= 1e6:
                text += f"Volume: {volume/1e6:.1f}M shares\n"
            else:
                text += f"Volume: {volume:,.0f} shares\n"
        if trades:
            text += f"Trades: {trades:,}\n"

    # Market status
    status = data.get("status")
    if status:
        status_text = status.get("status", "")
        if status_text:
            text += f"\nMarket Status: {status_text}\n"

    await update.message.reply_text(text)


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /watchlist — show user's watchlist."""
    user_id = update.effective_user.id
    tickers = get_watchlist(user_id)

    if not tickers:
        await update.message.reply_text(
            "Your watchlist is empty.\n"
            "Use /addwatch TICKER to add stocks."
        )
        return

    text = "Your Watchlist\n\n"
    for t in tickers:
        text += f"  {t} — {get_company_name(t)}\n"
    text += "\nTap any ticker name to view its Pulse card."

    await update.message.reply_text(text)


async def addwatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addwatch TICKER."""
    if not context.args:
        await update.message.reply_text("Usage: /addwatch KPHL")
        return

    ticker_input = " ".join(context.args)
    ticker = resolve_ticker(ticker_input)

    if not ticker:
        await update.message.reply_text(f"Unknown ticker: {ticker_input}")
        return

    add_watchlist(update.effective_user.id, ticker)
    await update.message.reply_text(f"Added {ticker} ({get_company_name(ticker)}) to your watchlist.")


async def removewatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removewatch TICKER."""
    if not context.args:
        await update.message.reply_text("Usage: /removewatch KPHL")
        return

    ticker_input = " ".join(context.args)
    ticker = resolve_ticker(ticker_input)

    if not ticker:
        await update.message.reply_text(f"Unknown ticker: {ticker_input}")
        return

    remove_watchlist(update.effective_user.id, ticker)
    await update.message.reply_text(f"Removed {ticker} from your watchlist.")


async def _send_ticker_card(update: Update, ticker: str):
    """
    Shared helper: fetch data and send the main card with inline buttons.
    Used by both the plain text handler and /p command.
    """
    # Show typing indicator
    await update.message.chat.send_action("upload_photo")

    cse_symbol = get_cse_symbol(ticker)
    sector = get_sector(ticker)
    company_name = get_company_name(ticker)

    stock = get_stock_data(ticker, cse_symbol, sector, company_name)
    if not stock:
        await update.message.reply_text(
            f"Could not fetch data for {ticker}. CSE may be closed or the ticker is delisted."
        )
        return

    # Get sentiment data
    velocity_data = get_mention_velocity(ticker)
    sentiment = get_avg_sentiment(ticker)

    # Determine pump alert
    is_pump = velocity_data["is_pump_alert"]
    pump_text = ""
    if is_pump:
        conc = velocity_data["concentration"]
        top = conc.get("top_source", "unknown")
        max_pct = conc.get("max_pct", 0)
        pump_text = f"High velocity, {max_pct:.0f}% from {top}, no catalyst"

    # Generate the card image
    card_buf = generate_main_card(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        last_price=stock.last_price,
        change=stock.change,
        change_pct=stock.change_pct,
        market_cap=stock.market_cap,
        volume=stock.volume,
        pe_ratio=stock.pe_ratio,
        spread_pct=stock.spread_pct,
        high=stock.high,
        low=stock.low,
        prev_close=stock.prev_close,
        high_52w=stock.high_52w,
        low_52w=stock.low_52w,
        price_position_52w=stock.price_position_52w,
        sentiment_score=sentiment,
        mention_count_24h=velocity_data["count_24h"],
        mention_velocity=velocity_data["velocity"],
        is_pump_alert=is_pump,
        pump_alert_text=pump_text,
    )

    # Inline keyboard for detail cards + TradingView chart
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Company Info", callback_data=f"fund_{ticker}"),
            InlineKeyboardButton("Technicals", callback_data=f"tech_{ticker}"),
        ],
        [
            InlineKeyboardButton("Insiders", callback_data=f"ins_{ticker}"),
            InlineKeyboardButton("Sentiment", callback_data=f"sent_{ticker}"),
        ],
        [
            InlineKeyboardButton(
                "Chart", url=f"https://www.tradingview.com/chart/?symbol=COSE:{ticker}"
            ),
            InlineKeyboardButton("Add to watchlist", callback_data=f"watch_{ticker}"),
        ],
    ])

    await update.message.reply_photo(
        photo=card_buf,
        reply_markup=keyboard,
    )


async def pulse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /p and /pulse — command-based ticker lookup for groups."""
    # Support uppercase /P /PULSE — parse args from message text if context.args is None
    args = context.args
    if args is None and update.message and update.message.text:
        parts = update.message.text.split(maxsplit=1)
        args = parts[1].split() if len(parts) > 1 else []

    if not args:
        await update.message.reply_text("Usage: /p KPHL or /p dhammika perera")
        return

    # Rate limiting
    if _is_rate_limited(update.effective_user.id):
        await update.message.reply_text("You're sending requests too fast. Please wait a moment.")
        return

    query = " ".join(args)
    result = resolve_input(query)

    if result["type"] == "director":
        await send_director_summary(update, result["director"])
        return

    if result["type"] == "delisted":
        await update.message.reply_text(
            f"{result['ticker']} ({result['name']}) is no longer traded on the CSE.\n"
            f"{result['note']}"
        )
        return

    ticker = result.get("ticker") if result["type"] == "ticker" else None
    if not ticker:
        await update.message.reply_text(
            f"'{query}' not found.\n"
            "Try a CSE ticker (e.g., /p KPHL) or company name (e.g., /p kapruka)."
        )
        return

    await _send_ticker_card(update, ticker)


async def brief_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /brief — admin-only, generate and send the morning brief here."""
    admin_id = _get_admin_id()
    if not admin_id or update.effective_user.id != admin_id:
        await update.message.reply_text("This command is admin-only.")
        return

    from services.morning_brief import generate_brief
    brief = generate_brief()
    await update.message.reply_text(brief)


async def handle_ticker_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle any text message — try to resolve it as a ticker or director name.
    This is the core interaction: paste ticker -> get card.
    """
    text = update.message.text.strip()

    # Skip if it looks like a command or is too long
    if text.startswith("/") or len(text) > 50:
        return

    # Rate limiting
    if _is_rate_limited(update.effective_user.id):
        await update.message.reply_text("You're sending requests too fast. Please wait a moment.")
        return

    result = resolve_input(text)

    # Director match — show summary of their holdings
    if result["type"] == "director":
        director = result["director"]
        await send_director_summary(update, director)
        return

    # Delisted stock — show helpful message
    if result["type"] == "delisted":
        await update.message.reply_text(
            f"{result['ticker']} ({result['name']}) is no longer traded on the CSE.\n"
            f"{result['note']}"
        )
        return

    ticker = result.get("ticker") if result["type"] == "ticker" else None
    if not ticker:
        # Don't respond to random messages — only respond if it kinda looks like a ticker
        if len(text) <= 6 and text.isalpha():
            await update.message.reply_text(
                f"Ticker '{text.upper()}' not found.\n"
                "Try the full company name (e.g., 'kapruka') or check the ticker code."
            )
        return

    await _send_ticker_card(update, ticker)


async def send_director_summary(update: Update, director: dict):
    """Send a summary of a director's associated stocks with live prices."""
    name = director["name"]
    title = director["title"]
    tickers = director["tickers"]
    note = director.get("note", "")

    await update.message.chat.send_action("typing")

    text = f"{name}\n{title}\n\n"
    if note:
        text += f"{note}\n\n"
    text += "Associated stocks:\n\n"

    for ticker in tickers:
        cse_symbol = get_cse_symbol(ticker)
        if not cse_symbol:
            text += f"  {ticker} — not in ticker map\n"
            continue

        sector = get_sector(ticker)
        company_name = get_company_name(ticker)
        stock = get_stock_data(ticker, cse_symbol, sector, company_name)

        if stock:
            sign = "+" if stock.change >= 0 else ""
            text += (
                f"  {ticker} ({company_name})\n"
                f"    LKR {stock.last_price:.2f}  "
                f"{sign}{stock.change:.2f} ({sign}{stock.change_pct:.1f}%)\n"
                f"    Vol: {stock.volume:,}  "
                f"MCap: LKR {stock.market_cap/1e9:.1f}B\n\n"
            )
        else:
            text += f"  {ticker} ({company_name}) — data unavailable\n\n"

    text += "Tap any ticker above to get its full Pulse card."

    await update.message.reply_text(text)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses for detail cards."""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split("_", 1)
    action = parts[0]
    ticker = parts[1] if len(parts) > 1 else None

    if not ticker or ticker not in TICKER_TO_CSE:
        await query.answer("Invalid ticker.")
        return

    # Rate limiting on callbacks too
    if _is_rate_limited(query.from_user.id):
        await query.answer("Too many requests. Please wait.")
        return

    if action == "fund":
        await send_fundamentals_card(query, ticker)
    elif action == "tech":
        await send_technicals_card(query, ticker)
    elif action == "ins":
        await send_insiders_text(query, ticker)
    elif action == "sent":
        await send_sentiment_text(query, ticker)
    elif action == "watch":
        user_id = query.from_user.id
        add_watchlist(user_id, ticker)
        await query.message.reply_text(f"Added {ticker} to your watchlist.")


async def send_fundamentals_card(query, ticker: str):
    """Generate and send the company info detail card."""
    from services.cse_api import fetch_company_profile, get_fundamentals_json

    cse_symbol = get_cse_symbol(ticker)
    sector = get_sector(ticker)
    company_name = get_company_name(ticker)

    stock = get_stock_data(ticker, cse_symbol, sector, company_name)
    if not stock:
        await query.message.reply_text("Could not fetch company data.")
        return

    # Fetch company profile (directors, business summary)
    profile = fetch_company_profile(cse_symbol)
    directors = None
    business_summary = None
    auditors = None
    if profile:
        # Extract director names
        raw_dirs = profile.get("infoCompanyDirector", [])
        if raw_dirs:
            directors = []
            for d in raw_dirs:
                first = (d.get("firstName") or "").strip()
                last = (d.get("lastName") or "").strip()
                directors.append(f"{first} {last}".strip())
        # Business summary
        summaries = profile.get("infoCompanyBusinessSummary", [])
        if summaries and summaries[0].get("body"):
            business_summary = summaries[0]["body"].strip()
        # Auditors
        com_info = profile.get("reqComSumInfo", [])
        if com_info:
            auditors = com_info[0].get("auditors")

    # Load manually-curated fundamentals from JSON
    fund = get_fundamentals_json(ticker)

    card_buf = generate_company_info_card(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        market_cap=stock.market_cap,
        shares_outstanding=stock.shares_outstanding,
        par_value=stock.par_value,
        beta_aspi=stock.beta_aspi,
        beta_spsl=stock.beta_spsl,
        high_52w=stock.high_52w,
        low_52w=stock.low_52w,
        price_position_52w=stock.price_position_52w,
        last_price=stock.last_price,
        foreign_pct=stock.foreign_pct,
        directors=directors,
        business_summary=business_summary,
        auditors=auditors,
        eps=fund.get("eps") if fund else None,
        nav=fund.get("nav") if fund else None,
        pe=fund.get("pe") if fund else None,
        pb=fund.get("pb") if fund else None,
        div_yield=fund.get("div_yield") if fund else None,
        dps=fund.get("dps") if fund else None,
        fundamentals_period=fund.get("updated") if fund else None,
    )

    await query.message.reply_photo(photo=card_buf)


async def send_technicals_card(query, ticker: str):
    """Generate and send the technicals detail card."""
    cse_symbol = get_cse_symbol(ticker)
    sector = get_sector(ticker)
    company_name = get_company_name(ticker)
    stock = get_stock_data(ticker, cse_symbol, sector, company_name)

    if not stock:
        await query.message.reply_text(f"Could not fetch data for {ticker}.")
        return

    sr = compute_support_resistance(stock)

    card_buf = generate_technicals_card(
        ticker=ticker,
        company_name=company_name,
        last_price=stock.last_price,
        change=stock.change,
        change_pct=stock.change_pct,
        high=stock.high,
        low=stock.low,
        prev_close=stock.prev_close,
        high_wtd=stock.high_wtd,
        low_wtd=stock.low_wtd,
        high_mtd=stock.high_mtd,
        low_mtd=stock.low_mtd,
        high_ytd=stock.high_ytd,
        low_ytd=stock.low_ytd,
        high_52w=stock.high_52w,
        low_52w=stock.low_52w,
        support=sr.get("support"),
        resistance=sr.get("resistance"),
        beta_aspi=stock.beta_aspi,
        beta_spsl=stock.beta_spsl,
        volume=stock.volume,
        avg_daily_volume_mtd=stock.avg_daily_volume_mtd,
        price_position_52w=stock.price_position_52w,
        spread_pct=stock.spread_pct,
    )

    await query.message.reply_photo(photo=card_buf)


async def send_insiders_text(query, ticker: str):
    """Send insider info as text (MVP — upgrade to card later)."""
    text = (
        f"{ticker} Insider Activity\n\n"
        "Director dealings and top 20 shareholder changes are "
        "sourced from CSE quarterly filings.\n\n"
        "This feature is coming soon — we're building the scraper "
        "for CSE disclosure announcements."
    )
    await query.message.reply_text(text)


async def handle_new_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the bot is added to a new group."""
    if update.my_chat_member is None:
        return

    new_status = update.my_chat_member.new_chat_member.status
    old_status = update.my_chat_member.old_chat_member.status

    # Only fire when transitioning into a group (member/admin) from non-member
    if new_status not in ("member", "administrator"):
        return
    if old_status in ("member", "administrator"):
        return

    welcome = (
        "Hey! I'm CeylonVest Pulse — your AI-powered CSE market intelligence assistant.\n\n"
        "What I can do:\n\n"
        "/p TICKER — Look up any of the 289 CSE-listed stocks\n"
        "Examples: /p JKH  /p COMB  /p LOLC  /p LIOC\n\n"
        "/p COMPANY NAME — Search by name instead of ticker\n"
        "Examples: /p kapruka  /p dialog  /p sampath bank\n\n"
        "/p DIRECTOR — See a director's portfolio\n"
        "Examples: /p dhammika perera  /p dulith herath\n\n"
        "/market — ASPI, S&P SL20 & sector indices\n"
        "/watchlist — Track your favorite stocks\n\n"
        "Try it now — type /p JKH"
    )

    chat_id = update.my_chat_member.chat.id
    try:
        await context.bot.send_message(chat_id=chat_id, text=welcome)
    except Exception as e:
        logger.error(f"Failed to send group welcome to {chat_id}: {e}")


async def send_sentiment_text(query, ticker: str):
    """Send sentiment deep dive as text."""
    velocity = get_mention_velocity(ticker)
    trend = get_sentiment_trend_7d(ticker)
    bb = get_most_bullish_bearish(ticker)
    avg = get_avg_sentiment(ticker)

    text = f"{ticker} Sentiment Deep Dive\n\n"
    text += f"Avg sentiment (24h): {avg:+.2f}\n" if avg is not None else "Avg sentiment (24h): No data\n"
    text += f"Mentions (24h): {velocity['count_24h']}\n"
    text += f"Velocity: {velocity['velocity']}x vs 30d avg\n\n"

    if bb.get("bullish"):
        text += f"Most bullish: {bb['bullish']}\n"
    if bb.get("bearish"):
        text += f"Most bearish: {bb['bearish']}\n"

    if trend:
        text += "\n7-day trend:\n"
        for day in trend:
            bar = "+" * max(1, int((day["score"] + 1) * 5)) if day["score"] else "?"
            text += f"  {day['date']}: {day['score']:+.2f} ({day['count']} mentions) {bar}\n"

    conc = velocity.get("concentration", {})
    if conc.get("sources"):
        text += "\nSource breakdown:\n"
        for src in conc["sources"][:5]:
            text += f"  {src['source_name'] or src['source']}: {src['count']} ({src['pct']:.0f}%)\n"

    await query.message.reply_text(text)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report TICKER — show annual report summary."""
    from services.annual_reports import get_report, cross_reference_news

    args = context.args
    if args is None and update.message and update.message.text:
        parts = update.message.text.split(maxsplit=1)
        args = parts[1].split() if len(parts) > 1 else []

    if not args:
        await update.message.reply_text(
            "Usage: /report JKH\n"
            "Shows annual report financials, management targets, and chairman's outlook."
        )
        return

    if _is_rate_limited(update.effective_user.id):
        await update.message.reply_text("You're sending requests too fast. Please wait a moment.")
        return

    ticker_input = args[0].upper()
    ticker = resolve_ticker(ticker_input) or ticker_input

    report = get_report(ticker)
    if not report:
        await update.message.reply_text(
            f"No annual report data for {ticker}.\n"
            "Currently available: JKH, KPHL. More coming soon."
        )
        return

    await update.message.chat.send_action("upload_photo")

    news_matches = cross_reference_news(ticker, hours=72)
    card_buf = generate_report_card(ticker, report, news_matches=news_matches or None)
    await update.message.reply_photo(photo=card_buf)


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /compare TICKER1 TICKER2 — side-by-side financial comparison."""
    from services.annual_reports import get_report

    args = context.args
    if args is None and update.message and update.message.text:
        parts = update.message.text.split(maxsplit=1)
        args = parts[1].split() if len(parts) > 1 else []

    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: /compare JKH KPHL\n"
            "Shows side-by-side financial comparison from annual reports."
        )
        return

    if _is_rate_limited(update.effective_user.id):
        await update.message.reply_text("You're sending requests too fast. Please wait a moment.")
        return

    t1_input = args[0].upper()
    t2_input = args[1].upper()
    ticker1 = resolve_ticker(t1_input) or t1_input
    ticker2 = resolve_ticker(t2_input) or t2_input

    report1 = get_report(ticker1)
    report2 = get_report(ticker2)

    missing = []
    if not report1:
        missing.append(ticker1)
    if not report2:
        missing.append(ticker2)
    if missing:
        await update.message.reply_text(
            f"No annual report data for: {', '.join(missing)}.\n"
            "Currently available: JKH, KPHL. More coming soon."
        )
        return

    await update.message.chat.send_action("upload_photo")

    card_buf = generate_compare_card(ticker1, report1, ticker2, report2)
    await update.message.reply_photo(photo=card_buf)


def main():
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: Set TELEGRAM_BOT_TOKEN in .env")
        return

    app = ApplicationBuilder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("market", market_command))
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(CommandHandler("addwatch", addwatch_command))
    app.add_handler(CommandHandler("removewatch", removewatch_command))
    app.add_handler(CommandHandler(["p", "pulse"], pulse_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("compare", compare_command))
    app.add_handler(CommandHandler("brief", brief_command))

    # Catch uppercase /P and /PULSE (Telegram may not recognize as BOT_COMMAND)
    app.add_handler(MessageHandler(
        filters.Regex(r"^/[Pp](?:[Uu][Ll][Ss][Ee])?\s") & filters.TEXT,
        pulse_command,
    ))

    # Group welcome when bot is added
    app.add_handler(ChatMemberHandler(handle_new_group, ChatMemberHandler.MY_CHAT_MEMBER))

    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Message handler — catch all text, try to resolve as ticker
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ticker_message))

    # Schedule background jobs
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from services.news_scraper import scrape as scrape_news
    from services.twitter_scraper import scrape as scrape_twitter
    from services.sentiment_scorer import score_pending
    from services.morning_brief import send_morning_brief

    def scrape_and_score():
        """Run all scrapers then score any new unscored mentions."""
        scrape_news()
        try:
            scrape_twitter()
        except Exception as e:
            logger.error(f"Twitter scrape failed: {e}")
        score_pending()

    import asyncio

    def _send_brief_sync():
        """Wrapper to run the async morning brief from the sync scheduler."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(send_morning_brief(app.bot))
            else:
                loop.run_until_complete(send_morning_brief(app.bot))
        except RuntimeError:
            asyncio.run(send_morning_brief(app.bot))

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        clear_cache,
        CronTrigger(hour=3, minute=45, timezone="UTC"),  # 9:15 AM SLT = 3:45 AM UTC
        id="daily_cache_clear",
        name="Clear stock data cache before market open",
    )
    scheduler.add_job(
        scrape_and_score,
        IntervalTrigger(minutes=30),
        id="rss_scrape_and_score",
        name="Scrape RSS feeds then score sentiment",
    )
    scheduler.add_job(
        _send_brief_sync,
        CronTrigger(hour=3, minute=0, timezone="UTC"),  # 8:30 AM SLT = 3:00 AM UTC
        id="morning_brief",
        name="Send morning brief to free channel",
    )
    scheduler.start()

    # Run initial scrape + score on startup
    try:
        scrape_and_score()
    except Exception as e:
        logger.error(f"Initial scrape/score failed: {e}")

    logger.info("CeylonVest Pulse bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
