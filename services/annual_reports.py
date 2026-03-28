"""
Annual Report Data Service
Loads structured annual report data and cross-references with recent news.
"""

import json
import logging
from pathlib import Path

from services.pulse_db import get_recent_headlines

logger = logging.getLogger("pulse.annual_reports")

_JSON_PATH = Path(__file__).parent.parent / "data" / "annual_reports.json"
_cache: dict | None = None


def _load() -> dict:
    """Load annual_reports.json with in-memory cache."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(_JSON_PATH, "r") as f:
            _cache = json.load(f)
        return _cache
    except Exception as e:
        logger.error(f"Failed to load annual_reports.json: {e}")
        return {}


def get_report(ticker: str) -> dict | None:
    """Get annual report data for a ticker. Returns None if not available."""
    return _load().get(ticker)


def get_all_tickers() -> list[str]:
    """Get all tickers that have annual report data."""
    return list(_load().keys())


def get_companies_by_sector(sector: str) -> dict[str, dict]:
    """Get all companies in a given sector. Returns {ticker: report_data}."""
    data = _load()
    return {t: d for t, d in data.items() if d.get("sector") == sector}


def cross_reference_news(ticker: str, hours: int = 72) -> list[dict]:
    """
    Find recent news headlines that relate to management plans.
    Checks if any keywords from management_plans appear in recent headlines.

    Returns: [{"plan": str, "headline": str, "source": str, "score": float|None}, ...]
    """
    report = get_report(ticker)
    if not report or not report.get("management_plans"):
        return []

    headlines = get_recent_headlines(hours=hours, limit=30)
    # Also check headlines for related tickers (e.g., sector news)
    matches = []
    seen = set()

    for plan in report["management_plans"]:
        # Extract meaningful keywords from the plan (3+ char words, skip common ones)
        skip = {"the", "and", "for", "from", "with", "over", "into", "below",
                "through", "within", "target", "focus", "current", "expected",
                "years", "year", "growth", "sector", "segment", "key", "reduce",
                "expand", "invest", "launch", "build"}
        words = [w.lower().strip(".,") for w in plan.split() if len(w) >= 4]
        keywords = [w for w in words if w not in skip]

        for h in headlines:
            content = (h.get("content") or "").lower()
            if not content:
                continue

            # Check if any keywords from this plan appear in the headline
            matched_words = [kw for kw in keywords if kw in content]
            if len(matched_words) >= 2:
                key = (plan[:50], content[:50])
                if key not in seen:
                    seen.add(key)
                    headline_text = (h.get("content") or "").split(" \u2014 ")[0][:120]
                    matches.append({
                        "plan": plan,
                        "headline": headline_text,
                        "source": h.get("source_name") or "Unknown",
                        "score": h.get("sentiment_score"),
                        "matched_keywords": matched_words[:3],
                    })

    return matches
