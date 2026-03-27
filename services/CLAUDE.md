# services/ — Data Services & Scrapers

## API call conventions
- All HTTP requests must have `timeout=10` (seconds)
- Wrap every external call in `try/except Exception` — return `None` on failure
- Use `logger.error()` for failures, never `print()`
- Validate `Content-Type` header before calling `resp.json()`
- Validate response structure (check types with `isinstance()`) before accessing nested fields

## CSE API specifics
- Only `companyInfoSummery` endpoint is working (as of March 2026)
- `tradeSummery` and `priceHistory` return 404 — documented as dead
- Always use the `HEADERS` dict from `cse_api.py` (User-Agent, Origin, Referer required)
- CSE symbol format: `TICKER.N0000` (e.g., `KPHL.N0000`)

## Caching rules
- Cache is in-memory with thread-safe `_cache_lock`
- 15s TTL during market hours (Mon-Fri 9:30-14:30 SLT)
- Indefinite cache outside market hours
- Full clear at 9:15 AM SLT via APScheduler cron job

## Database conventions (pulse_db.py)
- Always use `try/finally` to ensure `conn.close()` is called
- All queries use parameterized `?` placeholders — never format SQL with f-strings
- Truncate external input before DB insert: content=2000 chars, source_name=200 chars, url=500 chars
- `init_db()` is called on import — tables are created automatically

## Writing a new scraper
1. Create `services/new_scraper.py`
2. Wrap all external calls in try/except
3. Deduplicate by checking URL or content hash before `add_mention()`
4. Use `add_mention()` from `pulse_db.py` to store results
5. Register a cron job in `bot/main.py` via APScheduler
6. Run every 30 minutes (standard scraper interval)
7. Log start/end/error of each scraping cycle
