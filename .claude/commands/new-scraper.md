Create a new data source scraper for: $ARGUMENTS

Follow these steps:

1. Create `services/{scraper_name}_scraper.py` using this template:
   - Import `logging`, `requests`/`feedparser`, and `add_mention` from `pulse_db`
   - Create a `scrape()` function that:
     a. Fetches data from the source (with timeout=10, wrapped in try/except)
     b. For each item, extracts: content, source_name, url
     c. Deduplicates by checking URL against recent mentions (last 24h)
     d. Calls `add_mention(ticker, source, source_name, content, url=url)` for each new item
     e. Logs how many new mentions were found
   - All external calls must be fault-tolerant (try/except, never crash)
   - Truncate content to 2000 chars, source_name to 200 chars

2. Register a cron job in `bot/main.py`:
   - Import the scraper's `scrape` function
   - Add to the APScheduler block: run every 30 minutes
   - Use CronTrigger or IntervalTrigger as appropriate

3. Add the scraper to CLAUDE.md's "What's built" section

4. Test by running the scrape function directly:
   ```python
   PYTHONPATH=. python -c "from services.{name}_scraper import scrape; scrape()"
   ```
