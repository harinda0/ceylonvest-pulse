"""
Pulse Database
SQLite storage for ticker mentions, sentiment scores, and baselines.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "pulse.db"


def get_db():
    """Get a database connection with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
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
    """)
    conn.commit()
    conn.close()


def add_mention(ticker: str, source: str, source_name: str = None,
                content: str = None, sentiment_score: float = None, url: str = None):
    """Record a ticker mention from any source."""
    conn = get_db()
    conn.execute(
        "INSERT INTO mentions (ticker, source, source_name, content, sentiment_score, url) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ticker, source, source_name, content, sentiment_score, url),
    )
    conn.commit()
    conn.close()


def get_mention_count(ticker: str, hours: int = 24) -> int:
    """Count mentions of a ticker in the last N hours."""
    conn = get_db()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM mentions WHERE ticker = ? AND created_at > ?",
        (ticker, cutoff),
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def get_avg_mentions_30d(ticker: str) -> float:
    """Get the average daily mention count over the last 30 days."""
    conn = get_db()
    cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM mentions WHERE ticker = ? AND created_at > ?",
        (ticker, cutoff),
    ).fetchone()
    conn.close()
    total = row["cnt"] if row else 0
    return total / 30.0


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
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        "SELECT source, source_name, COUNT(*) as cnt "
        "FROM mentions WHERE ticker = ? AND created_at > ? "
        "GROUP BY source, source_name ORDER BY cnt DESC",
        (ticker, cutoff),
    ).fetchall()
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
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    row = conn.execute(
        "SELECT AVG(sentiment_score) as avg_score FROM mentions "
        "WHERE ticker = ? AND created_at > ? AND sentiment_score IS NOT NULL",
        (ticker, cutoff),
    ).fetchone()
    conn.close()
    return round(row["avg_score"], 2) if row and row["avg_score"] is not None else None


def get_sentiment_trend_7d(ticker: str) -> list:
    """
    Get daily average sentiment for the last 7 days.
    Returns: [{"date": str, "score": float, "count": int}, ...]
    """
    conn = get_db()
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    rows = conn.execute(
        "SELECT DATE(created_at) as day, AVG(sentiment_score) as avg_score, COUNT(*) as cnt "
        "FROM mentions WHERE ticker = ? AND created_at > ? AND sentiment_score IS NOT NULL "
        "GROUP BY DATE(created_at) ORDER BY day",
        (ticker, cutoff),
    ).fetchall()
    conn.close()
    return [{"date": r["day"], "score": round(r["avg_score"], 2), "count": r["cnt"]} for r in rows]


def get_most_bullish_bearish(ticker: str, hours: int = 24) -> dict:
    """Find the most bullish and bearish sources for a ticker."""
    conn = get_db()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    bullish = conn.execute(
        "SELECT source, source_name, AVG(sentiment_score) as avg_score, COUNT(*) as cnt "
        "FROM mentions WHERE ticker = ? AND created_at > ? AND sentiment_score IS NOT NULL "
        "GROUP BY source, source_name HAVING cnt >= 2 ORDER BY avg_score DESC LIMIT 1",
        (ticker, cutoff),
    ).fetchone()

    bearish = conn.execute(
        "SELECT source, source_name, AVG(sentiment_score) as avg_score, COUNT(*) as cnt "
        "FROM mentions WHERE ticker = ? AND created_at > ? AND sentiment_score IS NOT NULL "
        "GROUP BY source, source_name HAVING cnt >= 2 ORDER BY avg_score ASC LIMIT 1",
        (ticker, cutoff),
    ).fetchone()

    conn.close()
    return {
        "bullish": (bullish["source_name"] or bullish["source"]) if bullish else None,
        "bearish": (bearish["source_name"] or bearish["source"]) if bearish else None,
    }


def add_watchlist(user_id: int, ticker: str):
    """Add a ticker to a user's watchlist."""
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO user_watchlists (user_id, ticker) VALUES (?, ?)",
        (user_id, ticker),
    )
    conn.commit()
    conn.close()


def remove_watchlist(user_id: int, ticker: str):
    """Remove a ticker from a user's watchlist."""
    conn = get_db()
    conn.execute(
        "DELETE FROM user_watchlists WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )
    conn.commit()
    conn.close()


def get_watchlist(user_id: int) -> list[str]:
    """Get a user's watchlist tickers."""
    conn = get_db()
    rows = conn.execute(
        "SELECT ticker FROM user_watchlists WHERE user_id = ? ORDER BY created_at",
        (user_id,),
    ).fetchall()
    conn.close()
    return [r["ticker"] for r in rows]


# Initialize on import
init_db()
