"""
RSS News Scraper
Fetches headlines from Sri Lankan financial news feeds, extracts ticker
mentions and keyword matches, and stores them as mentions in pulse_db.

Feeds: Daily FT, EconomyNext, Ada Derana Biz, NewsWire
Runs every 30 minutes via APScheduler.
"""

import logging
import re
import feedparser
from html import unescape

from services.pulse_db import add_mention, url_already_scraped, mark_url_scraped
from utils.ticker_map import resolve_ticker, TICKER_TO_CSE, ALIASES
from utils.stock_connections import find_stocks_for_keywords

logger = logging.getLogger("pulse.news_scraper")


# --- Feed configuration ---

FEEDS = [
    # Daily FT RSS (https://www.ft.lk/rss) is dead as of March 2026 —
    # returns HTML instead of XML. Re-add if they restore it.
    {
        "name": "EconomyNext",
        "url": "https://economynext.com/feed",
    },
    {
        "name": "Ada Derana Biz",
        "url": "http://bizenglish.adaderana.lk/feed/",
    },
    {
        "name": "NewsWire",
        "url": "https://www.newswire.lk/feed",
    },
]


# --- Text cleaning ---

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_html(raw: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = unescape(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


# --- Ticker extraction ---

  # Tickers that are common English/news abbreviations — only match these
# via company name alias or keyword map, never via raw uppercase scan.
_TICKER_SKIP_UPPERCASE = {
    "AAF", "AINS", "CARS", "GRAN", "REEF", "TILE", "NEST",
    "DIST", "SPEN", "SINS", "CCS",
}


def _extract_tickers(text: str) -> dict[str, list[str]]:
    """
    Find all CSE tickers mentioned in text.
    Returns {ticker: [match_method, ...]} where match_method is
    "direct" (ticker/alias match) or "keyword" (keyword map match).
    """
    found: dict[str, list[str]] = {}

    # 1. Scan for direct ticker mentions (uppercase 2-5 letter words)
    #    Skip tickers that are common English abbreviations.
    words = re.findall(r"\b([A-Z]{2,5})\b", text)
    for word in words:
        if word in TICKER_TO_CSE and word not in _TICKER_SKIP_UPPERCASE:
            found.setdefault(word, []).append("direct")

    # 2. Check for known company name aliases in the text
    #    Only match against the explicit ALIASES dict to avoid false positives.
    lower = text.lower()
    for alias, ticker in ALIASES.items():
        # Only match multi-word aliases (single words are too noisy)
        if " " in alias and alias in lower:
            found.setdefault(ticker, []).append("direct")

    # 3. Keyword matching via stock_connections
    keyword_hits = find_stocks_for_keywords(text)
    for hit in keyword_hits:
        # Only include if there's a direct company name match (not just macro keywords)
        if "direct" in hit["connection_types"] and hit["score"] >= 6:
            found.setdefault(hit["ticker"], []).append("keyword")

    return found


# --- Feed processing ---

def _process_feed(feed_config: dict) -> dict:
    """
    Fetch and process a single RSS feed.
    Returns {"name": str, "articles": int, "mentions": int, "errors": int}.
    """
    name = feed_config["name"]
    url = feed_config["url"]
    stats = {"name": name, "articles": 0, "mentions": 0, "errors": 0}

    try:
        feed = feedparser.parse(url)

        # Retry once if bozo with no entries (intermittent XML parse failures)
        if feed.bozo and not feed.entries:
            import time
            time.sleep(2)
            feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            logger.warning(f"[{name}] Feed parse error: {feed.bozo_exception}")
            stats["errors"] = 1
            return stats

        for entry in feed.entries:
            try:
                article_url = entry.get("link", "")
                if not article_url:
                    continue

                # Dedup — skip if we already processed this URL
                if url_already_scraped(article_url):
                    continue

                stats["articles"] += 1

                # Extract text
                title = _clean_html(entry.get("title", ""))
                summary = _clean_html(
                    entry.get("summary", "")
                    or entry.get("description", "")
                )
                # Some feeds have full content
                content_parts = entry.get("content", [])
                body = ""
                if content_parts and isinstance(content_parts, list):
                    body = _clean_html(content_parts[0].get("value", ""))

                full_text = f"{title} {summary} {body}".strip()
                if not full_text:
                    continue

                # Extract tickers
                tickers = _extract_tickers(full_text)

                if tickers:
                    # Content to store: headline + first 500 chars of summary
                    mention_content = title
                    if summary:
                        mention_content += f" — {summary[:500]}"

                    for ticker, methods in tickers.items():
                        add_mention(
                            ticker=ticker,
                            source="rss",
                            source_name=name,
                            content=mention_content,
                            url=article_url,
                        )
                        stats["mentions"] += 1

                # Mark URL as processed (even if no tickers found)
                mark_url_scraped(article_url, name)

            except Exception as e:
                logger.error(f"[{name}] Error processing entry: {e}")
                stats["errors"] += 1
                continue

    except Exception as e:
        logger.error(f"[{name}] Error fetching feed {url}: {e}")
        stats["errors"] += 1

    return stats


# --- Main scrape function ---

def scrape() -> list[dict]:
    """
    Run the RSS scraper across all configured feeds.
    Returns list of per-feed stats dicts.
    Called by APScheduler every 30 minutes.
    """
    logger.info("RSS scraper starting...")
    all_stats = []

    for feed_config in FEEDS:
        try:
            stats = _process_feed(feed_config)
            all_stats.append(stats)
            logger.info(
                f"[{stats['name']}] "
                f"{stats['articles']} new articles, "
                f"{stats['mentions']} mentions, "
                f"{stats['errors']} errors"
            )
        except Exception as e:
            logger.error(f"[{feed_config['name']}] Unexpected error: {e}")
            all_stats.append({
                "name": feed_config["name"],
                "articles": 0,
                "mentions": 0,
                "errors": 1,
            })

    total_articles = sum(s["articles"] for s in all_stats)
    total_mentions = sum(s["mentions"] for s in all_stats)
    total_errors = sum(s["errors"] for s in all_stats)
    logger.info(
        f"RSS scraper done: {total_articles} articles, "
        f"{total_mentions} mentions, {total_errors} errors"
    )

    return all_stats


if __name__ == "__main__":
    # Manual test run
    logging.basicConfig(level=logging.INFO)
    results = scrape()
    print("\n=== RSS Scraper Results ===")
    for r in results:
        print(f"  {r['name']:20s}  articles={r['articles']}  mentions={r['mentions']}  errors={r['errors']}")
    print()
