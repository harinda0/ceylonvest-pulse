"""
CSE API Service
Fetches stock data from the Colombo Stock Exchange public API endpoints.
These are reverse-engineered endpoints used by cse.lk — no API key needed.
"""

import requests
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
import threading
import time as _time
import logging

logger = logging.getLogger("pulse.cse_api")

BASE_URL = "https://www.cse.lk/api/"

# Sri Lanka timezone offset (GMT+5:30)
SLT = timezone(timedelta(hours=5, minutes=30))

# --- Stock data cache ---
# Key: cse_symbol, Value: (StockData, timestamp)
_cache: dict[str, tuple] = {}
_cache_lock = threading.Lock()

CACHE_TTL_MARKET_OPEN = 15  # seconds during trading hours


def _now_slt() -> datetime:
    """Current time in Sri Lanka timezone."""
    return datetime.now(SLT)


def is_market_open() -> bool:
    """Check if CSE is currently in trading hours (Mon-Fri 9:30-14:30 SLT)."""
    now = _now_slt()
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=14, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def _is_cache_valid(cached_time: float) -> bool:
    """Check if a cached entry is still valid."""
    if is_market_open():
        return (_time.time() - cached_time) < CACHE_TTL_MARKET_OPEN
    # Outside market hours, cache is valid indefinitely (cleared at 9:15 AM SLT)
    return True


def clear_cache() -> None:
    """Clear the entire stock data cache. Called daily at 9:15 AM SLT."""
    with _cache_lock:
        count = len(_cache)
        _cache.clear()
    logger.info(f"Cache cleared ({count} entries removed)")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "Origin": "https://www.cse.lk",
    "Referer": "https://www.cse.lk/",
}


@dataclass
class StockData:
    """Complete stock data snapshot."""
    ticker: str
    name: str
    sector: str
    last_price: float
    change: float
    change_pct: float
    market_cap: float
    volume: int
    turnover: float
    high: float
    low: float
    prev_close: float
    high_52w: float
    low_52w: float
    # Period highs/lows from CSE
    high_wtd: float | None
    low_wtd: float | None
    high_mtd: float | None
    low_mtd: float | None
    high_ytd: float | None
    low_ytd: float | None
    # Period volumes
    volume_wtd: int | None
    volume_mtd: int | None
    volume_ytd: int | None
    volume_52w: int | None
    # Period turnovers
    turnover_wtd: float | None
    turnover_mtd: float | None
    turnover_ytd: float | None
    # Shares info
    shares_outstanding: int | None
    par_value: float | None
    foreign_pct: float | None
    # Beta values
    beta_aspi: float | None
    beta_spsl: float | None
    # Fundamentals (not currently in API response, reserved for future)
    pe_ratio: float | None
    eps: float | None
    book_value: float | None
    nav: float | None
    div_yield: float | None
    fetched_at: str

    @property
    def spread_pct(self) -> float | None:
        """Approximate bid-ask spread as % of price."""
        if self.last_price and self.last_price > 0:
            # CSE tick sizes vary; approximate from price
            if self.last_price < 25:
                tick = 0.10
            elif self.last_price < 100:
                tick = 0.20
            elif self.last_price < 500:
                tick = 0.50
            else:
                tick = 1.00
            return round((tick / self.last_price) * 100, 2)
        return None

    @property
    def pb_ratio(self) -> float | None:
        """Price to book ratio."""
        if self.book_value and self.book_value > 0:
            return round(self.last_price / self.book_value, 2)
        return None

    @property
    def price_position_52w(self) -> float | None:
        """Where current price sits in 52-week range (0-100%)."""
        if self.high_52w and self.low_52w and self.high_52w > self.low_52w:
            return round(
                (self.last_price - self.low_52w) / (self.high_52w - self.low_52w) * 100,
                1,
            )
        return None

    @property
    def avg_daily_volume_mtd(self) -> int | None:
        """Average daily volume this month (from MTD volume / trading days)."""
        if self.volume_mtd and self.volume_mtd > 0:
            # Rough estimate: ~22 trading days per month
            from datetime import datetime
            day_of_month = min(datetime.now().day, 22)
            trading_days = max(int(day_of_month * 5 / 7), 1)
            return int(self.volume_mtd / trading_days)
        return None


def fetch_company_info(cse_symbol: str) -> dict | None:
    """
    Fetch company info summary from CSE API.
    cse_symbol: e.g., "KPHL.N0000"
    """
    try:
        resp = requests.post(
            f"{BASE_URL}companyInfoSummery",
            data={"symbol": cse_symbol},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        if "application/json" not in resp.headers.get("Content-Type", ""):
            logger.warning(f"Non-JSON response from CSE API for {cse_symbol}")
            return None
        return resp.json()
    except Exception as e:
        logger.error(f"Error fetching {cse_symbol}: {e}")
        return None


def fetch_company_profile(cse_symbol: str) -> dict | None:
    """
    Fetch company profile from CSE API.
    Returns directors, business summary, auditors, sector, etc.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}companyProfile",
            data={"symbol": cse_symbol},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        if "application/json" not in resp.headers.get("Content-Type", ""):
            return None
        return resp.json()
    except Exception as e:
        logger.error(f"Error fetching profile {cse_symbol}: {e}")
        return None


def get_fundamentals_json(ticker: str) -> dict | None:
    """
    Load manually-curated fundamental data from data/fundamentals.json.
    Returns dict with eps, nav, pe, pb, div_yield, dps, updated — or None.
    """
    import json
    json_path = Path(__file__).parent.parent / "data" / "fundamentals.json"
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        return data.get(ticker)
    except Exception:
        return None


def fetch_price_history(cse_symbol: str) -> list | None:
    """
    Fetch historical price data for a symbol.
    NOTE: This endpoint returns 404 as of March 2026. Kept for future use
    if CSE restores it. Use companyInfoSummery period fields instead.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}priceHistory",
            data={"symbol": cse_symbol},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("priceHistory", [])
    except Exception as e:
        logger.error(f"Error fetching price history {cse_symbol}: {e}")
        return None


def fetch_market_summary() -> dict | None:
    """
    Fetch overall market summary including ASPI, S&P SL20, and sector indices.
    Uses POST /api/allSectors which returns all 22 indices (20 sectors + ASI + S&P SL20).
    Also fetches trade summary from POST /api/marketSummery for volume/turnover.
    """
    try:
        # Sector indices (includes ASPI and S&P SL20)
        resp = requests.post(
            f"{BASE_URL}allSectors",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        sectors = resp.json()
        if not isinstance(sectors, list):
            logger.warning("Unexpected allSectors response type")
            return None

        # Extract ASPI and S&P SL20 (last two items by convention)
        main_indices = []
        sector_indices = []
        for s in sectors:
            symbol = s.get("symbol", "")
            entry = {
                "indexName": s.get("indexName", s.get("name", "")),
                "indexValue": s.get("indexValue", 0),
                "change": s.get("change", 0),
                "changePercentage": s.get("percentage", 0),
            }
            if symbol in ("ASI", "S&P SL20"):
                main_indices.append(entry)
            else:
                sector_indices.append(entry)

        # Trade summary (volume, turnover)
        trade_data = {}
        try:
            resp2 = requests.post(
                f"{BASE_URL}marketSummery",
                headers=HEADERS,
                timeout=10,
            )
            if resp2.status_code == 200:
                trade_data = resp2.json()
        except Exception:
            pass

        return {
            "marketSummary": main_indices,
            "sectorSummary": sector_indices,
            "tradeVolume": trade_data.get("tradeVolume", 0),
            "shareVolume": trade_data.get("shareVolume", 0),
            "trades": trade_data.get("trades", 0),
        }

    except Exception as e:
        logger.error(f"Error fetching market summary: {e}")
        return None


def get_stock_data(ticker: str, cse_symbol: str, sector: str, company_name: str) -> StockData | None:
    """
    Assemble a complete StockData object from CSE companyInfoSummery API.
    This is the main function the bot calls.

    Caching: 15s during market hours, indefinite outside market hours.
    Cache is cleared daily at 9:15 AM SLT via scheduled job.
    """
    # Check cache
    with _cache_lock:
        if cse_symbol in _cache:
            cached_data, cached_time = _cache[cse_symbol]
            if _is_cache_valid(cached_time):
                logger.debug(f"Cache hit for {cse_symbol}")
                return cached_data

    info = fetch_company_info(cse_symbol)
    if not info:
        return None

    sym = info.get("reqSymbolInfo")
    if not isinstance(sym, dict):
        logger.warning(f"Unexpected reqSymbolInfo type for {cse_symbol}: {type(sym)}")
        return None
    beta = info.get("reqSymbolBetaInfo")
    if not isinstance(beta, dict):
        beta = {}

    stock = StockData(
        ticker=ticker,
        name=company_name,
        sector=sector,
        last_price=float(sym.get("lastTradedPrice", 0)),
        change=float(sym.get("change", 0)),
        change_pct=float(sym.get("changePercentage", 0)),
        market_cap=float(sym.get("marketCap", 0)),
        volume=int(sym.get("tdyShareVolume", 0)),
        turnover=float(sym.get("tdyTurnover", 0)),
        high=float(sym.get("hiTrade", 0)),
        low=float(sym.get("lowTrade", 0)),
        prev_close=float(sym.get("previousClose", 0)),
        high_52w=float(sym.get("p12HiPrice", 0)),
        low_52w=float(sym.get("p12LowPrice", 0)),
        high_wtd=_safe_float(sym.get("wtdHiPrice")),
        low_wtd=_safe_float(sym.get("wtdLowPrice")),
        high_mtd=_safe_float(sym.get("mtdHiPrice")),
        low_mtd=_safe_float(sym.get("mtdLowPrice")),
        high_ytd=_safe_float(sym.get("ytdHiPrice")),
        low_ytd=_safe_float(sym.get("ytdLowPrice")),
        volume_wtd=_safe_int(sym.get("wdyShareVolume")),
        volume_mtd=_safe_int(sym.get("mtdShareVolume")),
        volume_ytd=_safe_int(sym.get("ytdShareVolume")),
        volume_52w=_safe_int(sym.get("p12ShareVolume")),
        turnover_wtd=_safe_float(sym.get("wtdTurnover")),
        turnover_mtd=_safe_float(sym.get("mtdTurnover")),
        turnover_ytd=_safe_float(sym.get("ytdTurnover")),
        shares_outstanding=_safe_int(sym.get("quantityIssued")),
        par_value=_safe_float(sym.get("parValue")),
        foreign_pct=_safe_float(sym.get("foreignPercentage")),
        beta_aspi=_safe_float(beta.get("triASIBetaValue")),
        beta_spsl=_safe_float(beta.get("betaValueSPSL")),
        # Fundamentals not available from companyInfoSummery — reserved for future
        pe_ratio=None,
        eps=None,
        book_value=None,
        nav=None,
        div_yield=None,
        fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    # Store in cache
    with _cache_lock:
        _cache[cse_symbol] = (stock, _time.time())
    logger.debug(f"Cached {cse_symbol}")

    return stock


def compute_support_resistance(stock: StockData) -> dict:
    """
    Approximate support/resistance from available period data.
    Uses MTD low as support and MTD high as resistance.
    Returns: {"support": float, "resistance": float}
    """
    return {
        "support": stock.low_mtd,
        "resistance": stock.high_mtd,
    }


def compute_vs_aspi(cse_symbol: str) -> float | None:
    """
    Compute stock's 30d return minus ASPI 30d return.
    Positive = outperforming, negative = underperforming.
    """
    # This requires both stock history and ASPI history
    # For MVP, we'll return None and add this when we have ASPI data
    return None


def _safe_float(val) -> float | None:
    """Safely convert to float, returning None on failure."""
    if val is None or val == "" or val == "-":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    """Safely convert to int, returning None on failure."""
    if val is None or val == "" or val == "-":
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None
