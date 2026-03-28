"""
Pulse Database
Storage for ticker mentions, sentiment scores, and baselines.
Uses PostgreSQL when DATABASE_URL is set (Railway), falls back to SQLite for local dev.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

_USE_PG = bool(os.getenv("DATABASE_URL"))

if _USE_PG:
    import psycopg2
    import psycopg2.extras

DB_PATH = Path(__file__).parent.parent / "data" / "pulse.db"


# =========================================================================
# Connection helpers
# =========================================================================

def get_db():
    """Get a database connection. PostgreSQL if DATABASE_URL set, else SQLite."""
    if _USE_PG:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn


def _execute(conn, query, params=None):
    """Execute a query, adapting placeholder syntax for the active backend."""
    if _USE_PG:
        # Convert SQLite ? placeholders to PostgreSQL %s
        query = query.replace("?", "%s")
    cur = conn.cursor()
    cur.execute(query, params or ())
    return cur


def _fetchone(conn, query, params=None):
    """Execute and fetch one row as a dict."""
    cur = _execute(conn, query, params)
    row = cur.fetchone()
    if row is None:
        return None
    if _USE_PG:
        cols = [desc[0] for desc in cur.description]
        return dict(zip(cols, row))
    else:
        return dict(row)


def _fetchall(conn, query, params=None):
    """Execute and fetch all rows as dicts."""
    cur = _execute(conn, query, params)
    rows = cur.fetchall()
    if _USE_PG:
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in rows]
    else:
        return [dict(r) for r in rows]


# =========================================================================
# Schema
# =========================================================================

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS mentions (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    source TEXT NOT NULL,
    source_name TEXT,
    content TEXT,
    sentiment_score DOUBLE PRECISION,
    url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mentions_ticker ON mentions(ticker);
CREATE INDEX IF NOT EXISTS idx_mentions_created ON mentions(created_at);
CREATE INDEX IF NOT EXISTS idx_mentions_ticker_created ON mentions(ticker, created_at);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_watchlists (
    user_id BIGINT NOT NULL,
    ticker TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS scraped_urls (
    url TEXT PRIMARY KEY,
    source_name TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    source TEXT NOT NULL,
    source_name TEXT,
    content TEXT,
    sentiment_score REAL,
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mentions_ticker ON mentions(ticker);
CREATE INDEX IF NOT EXISTS idx_mentions_created ON mentions(created_at);
CREATE INDEX IF NOT EXISTS idx_mentions_ticker_created ON mentions(ticker, created_at);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT,
    data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_watchlists (
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS scraped_urls (
    url TEXT PRIMARY KEY,
    source_name TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    try:
        if _USE_PG:
            cur = conn.cursor()
            cur.execute(_PG_SCHEMA)
            conn.commit()
        else:
            conn.executescript(_SQLITE_SCHEMA)
            conn.commit()
    finally:
        conn.close()


# =========================================================================
# Mentions
# =========================================================================

def add_mention(ticker: str, source: str, source_name: str = None,
                content: str = None, sentiment_score: float = None, url: str = None):
    """Record a ticker mention from any source."""
    content = content[:2000] if content else None
    source_name = source_name[:200] if source_name else None
    url = url[:500] if url else None
    conn = get_db()
    try:
        _execute(conn,
            "INSERT INTO mentions (ticker, source, source_name, content, sentiment_score, url) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ticker, source, source_name, content, sentiment_score, url),
        )
        conn.commit()
    finally:
        conn.close()


def get_total_mentions() -> int:
    """Count all mentions in the database."""
    conn = get_db()
    try:
        row = _fetchone(conn, "SELECT COUNT(*) as cnt FROM mentions")
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_mention_count(ticker: str, hours: int = 24) -> int:
    """Count mentions of a ticker in the last N hours."""
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        row = _fetchone(conn,
            "SELECT COUNT(*) as cnt FROM mentions WHERE ticker = ? AND created_at > ?",
            (ticker, cutoff),
        )
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_avg_mentions_30d(ticker: str) -> float:
    """Get the average daily mention count over the last 30 days."""
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
        row = _fetchone(conn,
            "SELECT COUNT(*) as cnt FROM mentions WHERE ticker = ? AND created_at > ?",
            (ticker, cutoff),
        )
        total = row["cnt"] if row else 0
        return total / 30.0
    finally:
        conn.close()


def get_mention_velocity(ticker: str) -> dict:
    """
    Calculate mention velocity: current 24h count vs 30d daily average.
    Returns: {
        "count_24h": int,
        "avg_daily_30d": float,
        "velocity": float (multiplier),
        "is_spike": bool (>3x),
        "is_pump_alert": bool (>3x AND concentrated)
    }
    """
    count_24h = get_mention_count(ticker, hours=24)
    avg_30d = get_avg_mentions_30d(ticker)

    velocity = (count_24h / avg_30d) if avg_30d > 0 else 0
    concentration = get_source_concentration(ticker, hours=24)

    return {
        "count_24h": count_24h,
        "avg_daily_30d": round(avg_30d, 1),
        "velocity": round(velocity, 1),
        "is_spike": velocity >= 3.0,
        "is_pump_alert": velocity >= 3.0 and concentration.get("max_pct", 0) >= 60,
        "concentration": concentration,
    }


def get_source_concentration(ticker: str, hours: int = 24) -> dict:
    """
    How concentrated are mentions across sources?
    High concentration from few sources = manipulation signal.
    """
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        rows = _fetchall(conn,
            "SELECT source, source_name, COUNT(*) as cnt "
            "FROM mentions WHERE ticker = ? AND created_at > ? "
            "GROUP BY source, source_name ORDER BY cnt DESC",
            (ticker, cutoff),
        )
    finally:
        conn.close()

    if not rows:
        return {"sources": [], "max_pct": 0, "top_source": None}

    total = sum(r["cnt"] for r in rows)
    sources = [
        {
            "source": r["source"],
            "source_name": r["source_name"],
            "count": r["cnt"],
            "pct": round(r["cnt"] / total * 100, 1),
        }
        for r in rows
    ]

    return {
        "sources": sources,
        "max_pct": sources[0]["pct"] if sources else 0,
        "top_source": sources[0]["source_name"] or sources[0]["source"] if sources else None,
    }


def get_avg_sentiment(ticker: str, hours: int = 24) -> float | None:
    """Get average sentiment score for a ticker over the last N hours."""
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        row = _fetchone(conn,
            "SELECT AVG(sentiment_score) as avg_score FROM mentions "
            "WHERE ticker = ? AND created_at > ? AND sentiment_score IS NOT NULL",
            (ticker, cutoff),
        )
        return round(row["avg_score"], 2) if row and row["avg_score"] is not None else None
    finally:
        conn.close()


def get_sentiment_trend_7d(ticker: str) -> list:
    """
    Get daily average sentiment for the last 7 days.
    Returns: [{"date": str, "score": float, "count": int}, ...]
    """
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        if _USE_PG:
            query = (
                "SELECT created_at::date as day, AVG(sentiment_score) as avg_score, COUNT(*) as cnt "
                "FROM mentions WHERE ticker = ? AND created_at > ? AND sentiment_score IS NOT NULL "
                "GROUP BY created_at::date ORDER BY day"
            )
        else:
            query = (
                "SELECT DATE(created_at) as day, AVG(sentiment_score) as avg_score, COUNT(*) as cnt "
                "FROM mentions WHERE ticker = ? AND created_at > ? AND sentiment_score IS NOT NULL "
                "GROUP BY DATE(created_at) ORDER BY day"
            )
        rows = _fetchall(conn, query, (ticker, cutoff))
        return [{"date": str(r["day"]), "score": round(r["avg_score"], 2), "count": r["cnt"]} for r in rows]
    finally:
        conn.close()


def get_most_bullish_bearish(ticker: str, hours: int = 24) -> dict:
    """Find the most bullish and bearish sources for a ticker."""
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        bullish = _fetchone(conn,
            "SELECT source, source_name, AVG(sentiment_score) as avg_score, COUNT(*) as cnt "
            "FROM mentions WHERE ticker = ? AND created_at > ? AND sentiment_score IS NOT NULL "
            "GROUP BY source, source_name HAVING COUNT(*) >= 2 ORDER BY AVG(sentiment_score) DESC LIMIT 1",
            (ticker, cutoff),
        )

        bearish = _fetchone(conn,
            "SELECT source, source_name, AVG(sentiment_score) as avg_score, COUNT(*) as cnt "
            "FROM mentions WHERE ticker = ? AND created_at > ? AND sentiment_score IS NOT NULL "
            "GROUP BY source, source_name HAVING COUNT(*) >= 2 ORDER BY AVG(sentiment_score) ASC LIMIT 1",
            (ticker, cutoff),
        )

        return {
            "bullish": (bullish["source_name"] or bullish["source"]) if bullish else None,
            "bearish": (bearish["source_name"] or bearish["source"]) if bearish else None,
        }
    finally:
        conn.close()


# =========================================================================
# Watchlists
# =========================================================================

def add_watchlist(user_id: int, ticker: str):
    """Add a ticker to a user's watchlist."""
    conn = get_db()
    try:
        if _USE_PG:
            _execute(conn,
                "INSERT INTO user_watchlists (user_id, ticker) VALUES (?, ?) "
                "ON CONFLICT (user_id, ticker) DO NOTHING",
                (user_id, ticker),
            )
        else:
            _execute(conn,
                "INSERT OR IGNORE INTO user_watchlists (user_id, ticker) VALUES (?, ?)",
                (user_id, ticker),
            )
        conn.commit()
    finally:
        conn.close()


def remove_watchlist(user_id: int, ticker: str):
    """Remove a ticker from a user's watchlist."""
    conn = get_db()
    try:
        _execute(conn,
            "DELETE FROM user_watchlists WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        conn.commit()
    finally:
        conn.close()


def get_watchlist(user_id: int) -> list[str]:
    """Get a user's watchlist tickers."""
    conn = get_db()
    try:
        rows = _fetchall(conn,
            "SELECT ticker FROM user_watchlists WHERE user_id = ? ORDER BY created_at",
            (user_id,),
        )
        return [r["ticker"] for r in rows]
    finally:
        conn.close()


# =========================================================================
# Sentiment scoring
# =========================================================================

def get_unscored_mentions(limit: int = 50) -> list[dict]:
    """Get mentions that haven't been sentiment-scored yet."""
    conn = get_db()
    try:
        rows = _fetchall(conn,
            "SELECT id, ticker, source, source_name, content "
            "FROM mentions WHERE sentiment_score IS NULL AND content IS NOT NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return rows
    finally:
        conn.close()


def update_mention_sentiment(mention_id: int, sentiment_score: float):
    """Update the sentiment score for a specific mention."""
    conn = get_db()
    try:
        _execute(conn,
            "UPDATE mentions SET sentiment_score = ? WHERE id = ?",
            (sentiment_score, mention_id),
        )
        conn.commit()
    finally:
        conn.close()


# =========================================================================
# Scraper dedup
# =========================================================================

def url_already_scraped(url: str) -> bool:
    """Check if a URL has already been processed by a scraper."""
    conn = get_db()
    try:
        row = _fetchone(conn,
            "SELECT 1 as found FROM scraped_urls WHERE url = ?", (url,)
        )
        return row is not None
    finally:
        conn.close()


def mark_url_scraped(url: str, source_name: str = None):
    """Mark a URL as processed so it won't be scraped again."""
    url = url[:500] if url else ""
    source_name = source_name[:200] if source_name else None
    conn = get_db()
    try:
        if _USE_PG:
            _execute(conn,
                "INSERT INTO scraped_urls (url, source_name) VALUES (?, ?) "
                "ON CONFLICT (url) DO NOTHING",
                (url, source_name),
            )
        else:
            _execute(conn,
                "INSERT OR IGNORE INTO scraped_urls (url, source_name) VALUES (?, ?)",
                (url, source_name),
            )
        conn.commit()
    finally:
        conn.close()


# =========================================================================
# Morning brief helpers
# =========================================================================

def get_top_sentiment_movers(hours: int = 24, limit: int = 5) -> list[dict]:
    """
    Get tickers with the strongest sentiment (positive and negative) over the last N hours.
    Returns: [{"ticker": str, "avg_score": float, "count": int}, ...]
    sorted by absolute score descending — strongest signals first.
    """
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        rows = _fetchall(conn,
            "SELECT ticker, AVG(sentiment_score) as avg_score, COUNT(*) as cnt "
            "FROM mentions WHERE created_at > ? AND sentiment_score IS NOT NULL "
            "GROUP BY ticker HAVING COUNT(*) >= 2 "
            "ORDER BY ABS(AVG(sentiment_score)) DESC LIMIT ?",
            (cutoff, limit),
        )
        return [{"ticker": r["ticker"], "avg_score": round(r["avg_score"], 2), "count": r["cnt"]} for r in rows]
    finally:
        conn.close()


def get_most_mentioned(hours: int = 24, limit: int = 5) -> list[dict]:
    """
    Get the most mentioned tickers over the last N hours.
    Returns: [{"ticker": str, "count": int}, ...] sorted by count descending.
    """
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        rows = _fetchall(conn,
            "SELECT ticker, COUNT(*) as cnt "
            "FROM mentions WHERE created_at > ? "
            "GROUP BY ticker ORDER BY cnt DESC LIMIT ?",
            (cutoff, limit),
        )
        return [{"ticker": r["ticker"], "count": r["cnt"]} for r in rows]
    finally:
        conn.close()


def get_recent_headlines(hours: int = 24, limit: int = 10) -> list[dict]:
    """
    Get recent RSS headlines with their sentiment scores.
    Returns: [{"ticker": str, "source_name": str, "content": str, "sentiment_score": float|None}, ...]
    """
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        rows = _fetchall(conn,
            "SELECT ticker, source_name, content, sentiment_score "
            "FROM mentions WHERE source = ? AND created_at > ? "
            "ORDER BY created_at DESC LIMIT ?",
            ("rss", cutoff, limit),
        )
        return rows
    finally:
        conn.close()


# Initialize on import
init_db()
