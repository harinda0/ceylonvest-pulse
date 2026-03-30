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
        with open(_JSON_PATH, "r", encoding="utf-8") as f:
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
    Uses keyword overlap between management plans and recent headlines,
    with strict filtering to avoid false positives from generic words.

    Returns: [{"plan": str, "headline": str, "source": str, "score": float|None}, ...]
    """
    report = get_report(ticker)
    if not report or not report.get("management_plans"):
        return []

    headlines = get_recent_headlines(hours=hours, limit=30)
    matches = []
    seen = set()

    # Words that are too generic to be meaningful matches — they appear
    # in both financial plans AND unrelated news articles.
    skip = {
        "the", "and", "for", "from", "with", "over", "into", "below",
        "through", "within", "target", "focus", "current", "expected",
        "years", "year", "growth", "sector", "segment", "key", "reduce",
        "expand", "invest", "launch", "build", "first", "second", "third",
        "will", "plan", "plans", "also", "including", "based", "position",
        "operations", "operation", "terminal", "service", "services",
        "market", "company", "business", "development", "completion",
        "achieve", "full", "half", "area", "areas", "open", "opening",
        "close", "total", "major", "international", "national", "global",
        "further", "phase", "stage", "level", "part", "project",
    }

    for plan in report["management_plans"]:
        # Extract keywords: must be 5+ chars and not in skip set
        words = [w.lower().strip(".,;:()") for w in plan.split() if len(w) >= 5]
        keywords = [w for w in words if w not in skip]

        if len(keywords) < 2:
            continue

        for h in headlines:
            content = (h.get("content") or "").lower()
            if not content:
                continue

            # Require 3+ keyword matches, with at least one being 7+ chars
            matched_words = [kw for kw in keywords if kw in content]
            has_specific = any(len(w) >= 7 for w in matched_words)
            if len(matched_words) >= 3 and has_specific:
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
