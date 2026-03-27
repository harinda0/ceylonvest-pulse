"""
X/Twitter Scraper
Monitors CSE-related tweets using Apify's Tweet Scraper (apidojo/tweet-scraper).
Extracts ticker mentions, stores them in pulse_db.
Runs every 30 minutes via APScheduler.

Requires APIFY_API_TOKEN in .env.
"""

import os
import re
import logging

from services.pulse_db import add_mention, url_already_scraped, mark_url_scraped
from utils.ticker_map import resolve_ticker, TICKER_TO_CSE

logger = logging.getLogger("pulse.twitter")

# --- Search queries ---
SEARCH_QUERIES = [
    "#CSE OR #ColomboStockExchange",
    "#ASPI OR #SriLankaStocks",
    "Colombo Stock Exchange",
]

# Key accounts to monitor (CSE-focused analysts/commentators)
MONITOR_ACCOUNTS = [
    "CSaboredotcom",
    "ColomboStockEx",
    "EconomyNext",
]

# Apify actor ID for Twitter scraping
APIFY_ACTOR_ID = "apidojo/tweet-scraper"

# Max tweets to fetch per scrape cycle (controls Apify cost)
MAX_TWEETS = 100

# Minimum engagement to store a tweet (likes + retweets + replies)
MIN_ENGAGEMENT = 0


def _tweet_url(username: str, tweet_id: str) -> str:
    """Construct a tweet URL."""
    return f"https://x.com/{username}/status/{tweet_id}"


def _extract_tickers_from_tweet(text: str) -> list[str]:
    """
    Extract CSE ticker mentions from tweet text.
    Checks cashtags ($KPHL), hashtags (#JKH), and plain ticker words.
    """
    found = set()

    # 1. Cashtags: $KPHL, $JKH
    cashtags = re.findall(r"\$([A-Za-z]{2,5})\b", text)
    for tag in cashtags:
        upper = tag.upper()
        if upper in TICKER_TO_CSE:
            found.add(upper)

    # 2. Hashtags that match tickers: #JKH, #KPHL
    hashtags = re.findall(r"#([A-Za-z]{2,5})\b", text)
    for tag in hashtags:
        upper = tag.upper()
        if upper in TICKER_TO_CSE:
            found.add(upper)

    # 3. Uppercase words that are known tickers (skip common English words)
    _SKIP = {
        "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
        "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "HAS", "HIS",
        "HOW", "MAN", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO",
        "BOY", "DID", "GET", "LET", "SAY", "SHE", "TOO", "USE",
        "CEO", "IPO", "AGM", "EPS", "GDP", "IMF", "LKR", "USD",
        "NET", "PER", "BUY", "TOP", "SET", "RUN", "CUT", "BIG",
        "AAF", "AINS", "CARS", "GRAN", "REEF", "TILE", "NEST",
        "DIST", "SPEN", "SINS", "CCS",
    }
    words = re.findall(r"\b([A-Z]{2,5})\b", text)
    for w in words:
        if w in TICKER_TO_CSE and w not in _SKIP:
            found.add(w)

    # 4. Try resolving known company names
    lower = text.lower()
    for alias_check in ["john keells", "commercial bank", "hatton national", "sampath bank",
                         "dialog axiata", "sri lanka telecom", "ceylon tobacco",
                         "aitken spence", "hayleys", "cargills", "lanka orix"]:
        if alias_check in lower:
            ticker = resolve_ticker(alias_check)
            if ticker:
                found.add(ticker)

    return list(found)


def _get_engagement(tweet: dict) -> int:
    """Calculate total engagement from an Apify tweet result dict."""
    try:
        likes = tweet.get("likeCount", 0) or 0
        retweets = tweet.get("retweetCount", 0) or 0
        replies = tweet.get("replyCount", 0) or 0
        return likes + retweets + replies
    except Exception:
        return 0


def _process_tweet(tweet: dict) -> dict:
    """
    Process a single Apify tweet result.
    Returns {"stored": bool, "tickers": int} or None on error.
    """
    try:
        # Extract fields from Apify output
        tweet_id = tweet.get("id") or tweet.get("tweetId", "")
        tweet_url = tweet.get("url") or tweet.get("twitterUrl", "")
        text = tweet.get("text") or tweet.get("fullText", "")

        author = tweet.get("author", {}) or {}
        username = author.get("userName", "unknown")

        # Build URL if not provided
        if not tweet_url and tweet_id:
            tweet_url = _tweet_url(username, str(tweet_id))

        if not tweet_url:
            return None

        # Dedup
        if url_already_scraped(tweet_url):
            return {"stored": False, "tickers": 0}

        # Check engagement threshold
        engagement = _get_engagement(tweet)
        if engagement < MIN_ENGAGEMENT:
            mark_url_scraped(tweet_url, f"x/@{username}")
            return {"stored": False, "tickers": 0}

        # Extract tickers
        tickers = _extract_tickers_from_tweet(text)

        if tickers:
            content = text[:500]
            if engagement > 10:
                content = f"[{engagement} engagements] {content}"

            source_name = f"x/@{username}"

            for ticker in tickers:
                add_mention(
                    ticker=ticker,
                    source="twitter",
                    source_name=source_name,
                    content=content,
                    url=tweet_url,
                )

        # Mark as scraped even if no tickers
        mark_url_scraped(tweet_url, f"x/@{username}")

        return {"stored": bool(tickers), "tickers": len(tickers)}

    except Exception as e:
        logger.error(f"Error processing tweet: {e}")
        return None


def scrape() -> list[dict]:
    """
    Run the Twitter scraper via Apify's tweet-scraper actor.
    Sends all search queries and monitored accounts in a single actor run.
    Returns list of stats dicts.
    Called by APScheduler every 30 minutes.

    Requires APIFY_API_TOKEN environment variable.
    """
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        logger.warning("APIFY_API_TOKEN not set — skipping Twitter scrape")
        return []

    try:
        from apify_client import ApifyClient
    except ImportError:
        logger.error("apify-client not installed — run: pip install apify-client")
        return []

    logger.info("Twitter scraper starting (Apify)...")

    client = ApifyClient(api_token)

    # Build Apify actor input — single run with all queries + accounts
    run_input = {
        "searchTerms": SEARCH_QUERIES,
        "twitterHandles": MONITOR_ACCOUNTS,
        "maxItems": MAX_TWEETS,
        "sort": "Latest",
        "includeSearchTerms": False,
    }

    stats = {"source": "apify_twitter", "tweets": 0, "mentions": 0, "errors": 0}

    try:
        run = client.actor(APIFY_ACTOR_ID).call(
            run_input=run_input,
            timeout_secs=120,
        )

        # Check if the actor run signals a paid plan requirement
        status_msg = run.get("statusMessage", "")
        if "paid plan" in status_msg.lower() or "cannot use" in status_msg.lower():
            logger.warning(
                "Apify tweet-scraper requires a paid plan — skipping Twitter scrape. "
                "Upgrade at https://apify.com/pricing"
            )
            return [stats]

        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            logger.error("Apify run completed but no dataset returned")
            stats["errors"] = 1
            return [stats]

        # Process results from the dataset
        for tweet in client.dataset(dataset_id).iterate_items():
            result = _process_tweet(tweet)
            if result is None:
                stats["errors"] += 1
            else:
                stats["tweets"] += 1
                stats["mentions"] += result["tickers"]

    except Exception as e:
        logger.error(f"Apify actor run failed: {e}")
        stats["errors"] += 1

    logger.info(
        f"Twitter scraper done: {stats['tweets']} tweets, "
        f"{stats['mentions']} mentions, {stats['errors']} errors"
    )

    return [stats]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")
    from dotenv import load_dotenv
    load_dotenv()

    results = scrape()
    print("\n=== Twitter Scraper Results (Apify) ===")
    for r in results:
        print(f"  tweets={r.get('tweets', 0)}  mentions={r.get('mentions', 0)}  errors={r.get('errors', 0)}")
