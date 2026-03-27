"""
Claude Sentiment Scorer
Scores ticker mentions from -1.0 (bearish) to +1.0 (bullish) using Claude API.
Processes mentions in batches of 10 to minimize API calls.
Rate limited to max 5 API calls per minute.
"""

import os
import json
import time
import logging
from anthropic import Anthropic

from services.pulse_db import get_unscored_mentions, update_mention_sentiment

logger = logging.getLogger("pulse.sentiment")

BATCH_SIZE = 10
MAX_CALLS_PER_MINUTE = 5

SYSTEM_PROMPT = """You are a financial sentiment scorer for the Colombo Stock Exchange (CSE) in Sri Lanka.

Your task: Score each mention from -1.0 (extremely bearish) to +1.0 (extremely bullish).

Scoring guide:
- +0.8 to +1.0: Strong positive — earnings beat, major contract win, upgrade, expansion
- +0.4 to +0.7: Moderate positive — steady growth, new product, sector tailwind
- +0.1 to +0.3: Slight positive — neutral-positive tone, minor good news
- -0.1 to +0.1: Neutral — factual reporting, no clear direction
- -0.1 to -0.3: Slight negative — minor concerns, cautious tone
- -0.4 to -0.7: Moderate negative — earnings miss, downgrade, regulatory risk
- -0.8 to -1.0: Strong negative — major loss, fraud, crisis, delisting risk

Critical distinctions:
1. PUMP LANGUAGE vs GENUINE ANALYSIS:
   - Pump: "This stock will moon!", "100% guaranteed returns", "Buy before it's too late!"
     → Score these NEUTRAL (0.0) — hype is not real sentiment
   - Genuine: "Q3 margins improved 200bps on better product mix" → Score on merit

2. Sri Lankan market context:
   - CBSL rate cuts → bullish for banks/finance
   - Rupee depreciation → bullish for exporters, bearish for importers
   - Tourist arrivals up → bullish for hotels
   - IMF program progress → bullish for sovereign/banking confidence
   - Government budget/tax changes → sector-specific impact

3. Source reliability:
   - RSS news articles (Daily FT, EconomyNext) = professional journalism, score on content
   - Social media mentions = may contain pump language, be skeptical

You will receive a JSON array of mentions. For each, return a JSON array of objects:
[{"id": <mention_id>, "score": <float>, "pump": <boolean>}]

Where:
- id: the mention ID from input
- score: sentiment score from -1.0 to +1.0
- pump: true if the language is promotional/pump-style rather than genuine analysis

Return ONLY the JSON array, no other text."""


def _build_batch_prompt(mentions: list[dict]) -> str:
    """Format a batch of mentions for the Claude API."""
    items = []
    for m in mentions:
        content = m["content"][:500] if m["content"] else ""
        items.append({
            "id": m["id"],
            "ticker": m["ticker"],
            "source": m["source_name"] or m["source"],
            "text": content,
        })
    return json.dumps(items, indent=2)


def _parse_response(response_text: str) -> list[dict]:
    """Parse Claude's JSON response into score objects."""
    # Strip markdown code fences if present
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        results = json.loads(text)
        if not isinstance(results, list):
            logger.error(f"Expected JSON array, got {type(results)}")
            return []
        return results
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response: {e}")
        logger.debug(f"Raw response: {response_text[:200]}")
        return []


def score_batch(mentions: list[dict], client: Anthropic) -> int:
    """
    Score a batch of mentions using Claude API.
    Returns number of mentions successfully scored.
    """
    if not mentions:
        return 0

    prompt = _build_batch_prompt(mentions)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text
        results = _parse_response(response_text)

        scored = 0
        for result in results:
            mention_id = result.get("id")
            score = result.get("score")

            if mention_id is None or score is None:
                continue

            # Clamp score to [-1.0, 1.0]
            score = max(-1.0, min(1.0, float(score)))

            # If pump language detected, flatten score toward neutral
            if result.get("pump", False):
                score = score * 0.3  # Dampen pump scores

            update_mention_sentiment(mention_id, score)
            scored += 1

        return scored

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return 0


def score_pending(max_batches: int = 10) -> dict:
    """
    Score all pending (unscored) mentions in batches.
    Rate limited to MAX_CALLS_PER_MINUTE API calls per minute.

    Args:
        max_batches: Maximum number of API calls to make in one run.

    Returns:
        {"total": int, "scored": int, "batches": int, "errors": int}
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping sentiment scoring")
        return {"total": 0, "scored": 0, "batches": 0, "errors": 0}

    client = Anthropic(api_key=api_key)

    unscored = get_unscored_mentions(limit=max_batches * BATCH_SIZE)
    if not unscored:
        logger.info("No unscored mentions to process")
        return {"total": 0, "scored": 0, "batches": 0, "errors": 0}

    logger.info(f"Scoring {len(unscored)} unscored mentions...")

    total_scored = 0
    batches_run = 0
    errors = 0
    call_times: list[float] = []

    # Process in batches
    for i in range(0, len(unscored), BATCH_SIZE):
        if batches_run >= max_batches:
            break

        batch = unscored[i:i+BATCH_SIZE]

        # Rate limiting: ensure max 5 calls per 60 seconds
        now = time.time()
        call_times = [t for t in call_times if now - t < 60]
        if len(call_times) >= MAX_CALLS_PER_MINUTE:
            wait = 60 - (now - call_times[0]) + 1
            logger.info(f"Rate limit: waiting {wait:.0f}s")
            time.sleep(wait)

        call_times.append(time.time())
        scored = score_batch(batch, client)

        if scored > 0:
            total_scored += scored
            batches_run += 1
            logger.info(f"Batch {batches_run}: scored {scored}/{len(batch)} mentions")
        else:
            errors += 1
            logger.warning(f"Batch {batches_run+1}: failed to score")

    logger.info(
        f"Sentiment scoring done: {total_scored}/{len(unscored)} scored "
        f"in {batches_run} batches, {errors} errors"
    )

    return {
        "total": len(unscored),
        "scored": total_scored,
        "batches": batches_run,
        "errors": errors,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")
    from dotenv import load_dotenv
    load_dotenv()

    result = score_pending()
    print(f"\nResult: {result}")

    # Show scored mentions
    from services.pulse_db import get_db
    conn = get_db()
    rows = conn.execute(
        "SELECT ticker, source_name, sentiment_score, substr(content, 1, 70) as headline "
        "FROM mentions WHERE sentiment_score IS NOT NULL "
        "ORDER BY sentiment_score DESC"
    ).fetchall()
    conn.close()

    if rows:
        print(f"\n{'TICKER':6s} {'SCORE':>6s}  {'SOURCE':15s}  HEADLINE")
        print("-" * 100)
        for r in rows:
            h = r["headline"].encode("ascii", "replace").decode()
            print(f"{r['ticker']:6s} {r['sentiment_score']:+6.2f}  {r['source_name']:15s}  {h}")
