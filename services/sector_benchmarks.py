"""
Sector Benchmarks Service
Auto-calculates sector averages from annual report data.
Recalculates when annual_reports.json changes (mtime-based).
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("pulse.sector_benchmarks")

_REPORTS_PATH = Path(__file__).parent.parent / "data" / "annual_reports.json"
_BENCHMARKS_PATH = Path(__file__).parent.parent / "data" / "sector_benchmarks.json"

_cache: dict | None = None
_source_mtime: float = 0.0

# Sector aliases for user-friendly lookups
SECTOR_ALIASES = {
    "BANKING": "Banks",
    "BANKS": "Banks",
    "BANK": "Banks",
    "RETAIL": "Retailing",
    "RETAILING": "Retailing",
    "INSURANCE": "Insurance",
    "FOOD": "Food Beverage & Tobacco",
    "BEVERAGE": "Food Beverage & Tobacco",
    "ENERGY": "Energy",
    "CAPITAL GOODS": "Capital Goods",
    "MANUFACTURING": "Capital Goods",
    "TELECOM": "Telecommunication Services",
    "TELCO": "Telecommunication Services",
    "FINANCE": "Diversified Financials",
    "FINANCIALS": "Diversified Financials",
    "DIVERSIFIED FINANCIALS": "Diversified Financials",
    "REAL ESTATE": "Real Estate Management & Development",
    "PROPERTY": "Real Estate Management & Development",
    "CONSUMER": "Consumer Services",
    "HOTELS": "Consumer Services",
    "TOURISM": "Consumer Services",
    "APPAREL": "Consumer Durables & Apparel",
    "MATERIALS": "Materials",
    "PLANTATIONS": "Materials",
    "PLANTATION": "Materials",
    "HEALTH": "Consumer Services",
    "HEALTHCARE": "Consumer Services",
    "CONSTRUCTION": "Capital Goods",
    "AUTO": "Capital Goods",
    "AUTOMOTIVE": "Capital Goods",
    "DIVERSIFIED": "Diversified Financials",
}

# Metrics where higher = better (True) vs lower = better (False)
_HIGHER_IS_BETTER = {
    "roe": True,
    "eps": True,
    "nav": True,
    "revenue_growth": True,
    "profit_margin": True,
    "dividend_per_share": True,
    "debt_to_equity": False,
}


def _load_reports() -> dict:
    """Load annual_reports.json."""
    try:
        with open(_REPORTS_PATH) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load annual_reports.json: {e}")
        return {}


def calculate_benchmarks() -> dict:
    """Calculate sector benchmarks from annual report data."""
    reports = _load_reports()
    if not reports:
        return {}

    # Group companies by sector
    sectors: dict[str, list] = {}
    for ticker, data in reports.items():
        sector = data.get("sector", "Other")
        if not sector:
            sector = "Other"
        sectors.setdefault(sector, []).append((ticker, data))

    benchmarks = {}
    for sector, companies in sectors.items():
        metric_values = {
            "roe": [],
            "eps": [],
            "nav": [],
            "dividend_per_share": [],
            "debt_to_equity": [],
            "revenue_growth": [],
            "profit_margin": [],
        }

        tickers = []
        for ticker, data in companies:
            tickers.append(ticker)
            fin = data.get("financials", {})

            # Direct metrics
            for key in ("roe", "eps", "nav", "dividend_per_share", "debt_to_equity"):
                val = fin.get(key)
                if val is not None:
                    metric_values[key].append(val)

            # Revenue growth (from yoy_change)
            rev = fin.get("revenue", {})
            if isinstance(rev, dict) and rev.get("yoy_change") is not None:
                metric_values["revenue_growth"].append(rev["yoy_change"])

            # Profit margin = net_profit / revenue * 100
            rev_val = rev.get("value") if isinstance(rev, dict) else None
            np_data = fin.get("net_profit", {})
            np_val = np_data.get("value") if isinstance(np_data, dict) else None
            if rev_val and np_val and rev_val != 0:
                metric_values["profit_margin"].append(np_val / rev_val * 100)

        # Calculate stats for each metric
        metrics = {}
        for name, values in metric_values.items():
            if values:
                sorted_vals = sorted(values)
                avg = sum(values) / len(values)
                # Use median for robustness against outliers
                mid = len(sorted_vals) // 2
                median = sorted_vals[mid] if len(sorted_vals) % 2 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
                metrics[name] = {
                    "avg": round(avg, 2),
                    "median": round(median, 2),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "count": len(values),
                }
            else:
                metrics[name] = {
                    "avg": None, "median": None,
                    "min": None, "max": None, "count": 0,
                }

        benchmarks[sector] = {
            "company_count": len(companies),
            "tickers": tickers,
            "metrics": metrics,
        }

    return benchmarks


def recalculate_and_save() -> dict:
    """Recalculate benchmarks and save to JSON file."""
    benchmarks = calculate_benchmarks()
    try:
        with open(_BENCHMARKS_PATH, "w", encoding="utf-8") as f:
            json.dump(benchmarks, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved sector benchmarks: {len(benchmarks)} sectors")
    except Exception as e:
        logger.error(f"Failed to save sector_benchmarks.json: {e}")
    return benchmarks


def get_benchmarks() -> dict:
    """Get benchmarks, recalculating if source data changed."""
    global _cache, _source_mtime
    try:
        current_mtime = os.path.getmtime(_REPORTS_PATH)
    except OSError:
        return _cache or {}
    if _cache is None or current_mtime != _source_mtime:
        _cache = recalculate_and_save()
        _source_mtime = current_mtime
    return _cache


def get_sector_benchmark(sector: str) -> dict | None:
    """Get benchmark for a specific sector."""
    benchmarks = get_benchmarks()
    return benchmarks.get(sector)


def resolve_sector(name: str) -> str | None:
    """Resolve a user-friendly sector name to the canonical name."""
    upper = name.upper().strip()
    if upper in SECTOR_ALIASES:
        return SECTOR_ALIASES[upper]
    # Try direct match against known sectors
    benchmarks = get_benchmarks()
    for sector_name in benchmarks:
        if sector_name.upper() == upper:
            return sector_name
    # Partial match
    for sector_name in benchmarks:
        if upper in sector_name.upper():
            return sector_name
    return None


def get_all_sectors() -> list[str]:
    """Get all sector names."""
    return list(get_benchmarks().keys())


def evaluate_metric(metric_name: str, value: float, sector: str) -> dict | None:
    """Evaluate a metric against sector benchmark.
    Returns {"status": "above"|"below"|"at", "sector_avg": float, "is_good": bool}
    or None if benchmark not available.
    """
    bench = get_sector_benchmark(sector)
    if not bench:
        return None
    m = bench.get("metrics", {}).get(metric_name)
    if not m or m.get("avg") is None or m.get("count", 0) < 2:
        return None

    avg = m["avg"]
    higher_better = _HIGHER_IS_BETTER.get(metric_name, True)

    if abs(value - avg) < 0.01 * abs(avg) if avg != 0 else abs(value) < 0.01:
        status = "at"
        is_good = True
    elif value > avg:
        status = "above"
        is_good = higher_better
    else:
        status = "below"
        is_good = not higher_better

    return {
        "status": status,
        "sector_avg": avg,
        "is_good": is_good,
        "count": m["count"],
    }
