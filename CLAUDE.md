# CeylonVest Pulse

## What this is
CeylonVest Pulse is an AI-powered market intelligence Telegram bot for the Colombo Stock Exchange (CSE). Users paste a ticker (like "KPHL" or "kapruka") and instantly receive a BonkBot-style image card with live stock data, sentiment analysis, mention velocity, and pump detection alerts.

## Owner
Harinda — a founder and CSE investor based in Canada. He has no formal coding background but has built multiple Python bots (X/Twitter content bots with Claude API, Pillow image generation, Telegram review workflows). He learns by doing with step-by-step guidance.

## Critical rules

1. **All times must be Sri Lanka Time (GMT+5:30).** Never use UTC or local system time in any display or logic. Store timestamps in UTC internally but always convert to SLT for display.
2. **Never display fabricated, estimated, or AI-generated data as if it were real market data.** If a data point is unavailable from the CSE API, show "N/A" — never guess or fill in numbers. All prices, volumes, and financial metrics must come directly from the CSE API.
3. **Clearly label any AI-generated content** (like sentiment scores or news connections) as AI-derived, separate from hard market data.

## Architecture

```
ceylonvest-pulse/
├── bot/
│   └── main.py              # Telegram bot — handles messages, generates cards
├── services/
│   ├── cse_api.py            # CSE stock data from public API endpoints (cached)
│   ├── pulse_db.py           # SQLite — mentions, sentiment, velocity tracking
│   ├── news_scraper.py       # [TODO] RSS scraper for Daily FT, EconomyNext
│   ├── twitter_scraper.py    # [TODO] X/Twitter monitor for CSE keywords
│   ├── fb_scraper.py         # [TODO] Facebook group scraper via Apify
│   └── sentiment_scorer.py   # [TODO] Claude API batch sentiment scoring
├── utils/
│   ├── ticker_map.py         # Ticker alias map — "kapruka" → "KPHL"
│   ├── card_generator.py     # Pillow image generation for TG cards
│   └── stock_connections.py  # Stock-to-keyword mapping for news connections
├── data/
│   └── pulse.db              # SQLite database (auto-created)
├── .env                      # API keys (never commit)
├── .env.example              # Template for .env
├── requirements.txt          # Python dependencies
└── CLAUDE.md                 # This file
```

## Tech stack
- Python 3.11+
- python-telegram-bot 21.x (async)
- Pillow (image generation for cards)
- requests (CSE API calls)
- feedparser (RSS news scraping)
- anthropic SDK (sentiment scoring)
- SQLite (data storage)
- APScheduler (cron jobs for scrapers)
- Deployed on Railway (or any VPS)

## Key design decisions

### The ticker card system
When a user pastes a ticker, the bot responds with a Pillow-generated PNG image card (dark theme, ~520px wide) showing:
- Main card: price, change, market cap, volume, P/E, spread, 7d/30d/90d returns, sentiment score, mention count, velocity, pump alert
- Detail cards (via inline buttons): Fundamentals, Technicals, Insiders, Sentiment

### CSE API
The CSE has no official API. We use reverse-engineered endpoints from cse.lk:
- `POST /api/companyInfoSummery` with `{"symbol": "KPHL.N0000"}` — **primary stock data endpoint, working**
- `POST /api/companyProfile` with `{"symbol": "KPHL.N0000"}` — **directors, business summary, auditors**
- `POST /api/tradeSummary` — **lists all ~289 securities, working** (used by update_tickers.py)
- `POST /api/aspiData` — **ASPI index value, change, percentage** (no body needed)
- `POST /api/snpData` — **S&P SL20 index value, change, percentage** (no body needed)
- `POST /api/dailyMarketSummery` — **turnover, volume, trades, market cap** (no body needed)
- `POST /api/marketStatus` — **open/closed status** (no body needed)
- `POST /api/allSectors` — **all 22 sector indices** (no body needed)
- `POST /api/priceHistory` — **dead (404) as of March 2026**
These endpoints require specific headers (see cse_api.py). No fundamentals (EPS, PE, NAV) are available from any CSE API endpoint.

### Caching
Stock data from companyInfoSummery is cached in-memory:
- **During market hours** (Mon-Fri 9:30-14:30 SLT): 15-second TTL
- **Outside market hours**: cached indefinitely (prices don't change)
- **Daily at 9:15 AM SLT**: entire cache cleared before market open

### Ticker resolution
Users can type "KPHL", "kapruka", "Kapruka Holdings", or even misspellings. The ticker_map.py handles alias resolution. Currently covers ~50 popular stocks. Needs expansion to all ~300 CSE-listed stocks.

### Sentiment pipeline (partially built)
1. Scrapers (RSS, X, FB) collect mentions every 30 minutes
2. Ticker extractor identifies stock references using regex + alias map
3. Claude API scores each mention -1.0 (bearish) to +1.0 (bullish)
4. SQLite stores: ticker, source, source_name, content, sentiment_score, timestamp
5. Velocity engine computes 24h count vs 30-day daily average
6. Pump detection fires when velocity ≥ 3x AND source concentration ≥ 60%

### Pump detection logic
The killer feature. When a stock's mention count spikes well above its historical baseline, AND most of those mentions come from a small number of sources (like 2 FB groups), AND there's no corresponding CSE filing or news catalyst — that's flagged as a pump alert. This protects retail investors from WhatsApp/FB group manipulation.

### Smart News Connections
When displaying a ticker card, include a "Related news" section showing recent news articles connected to that stock. The connection engine (utils/stock_connections.py) maps each ticker to keywords, sectors, commodities, and macro themes.

**Connection types:**
- **Direct:** LIOC ↔ fuel prices, oil deals, energy policy
- **Sector:** banking stocks ↔ interest rate changes, monetary policy
- **Supply chain:** DIPD ↔ rubber prices, WATA ↔ tea auctions
- **Macro:** tourism headlines ↔ hotel stocks (TJL, AHPL, REEF)
- **Infrastructure:** port/road/airport news ↔ AAF, JKH, construction stocks
- **Policy:** tax changes ↔ affected sectors, import/export policy ↔ EXPO

**Reverse lookup (news → stocks):** When a major news event is detected (e.g., "Iran tensions escalate"), list all CSE stocks that could be affected and why. Triggered via `/news` command or included in the morning brief.

Claude API scores the relevance of news articles to specific stocks. All news connections are labeled as AI-derived per Critical Rule #3.

## What's built (working)
- [x] Telegram bot with ticker lookup
- [x] CSE API integration (live price via companyInfoSummery)
- [x] Ticker alias map (~50 stocks)
- [x] Main card image generator (Pillow)
- [x] Fundamentals card generator
- [x] SQLite database with mention tracking
- [x] Velocity and pump detection engine
- [x] Watchlist per user
- [x] Support/resistance calculations (MTD-based)
- [x] Smart caching (15s market hours, indefinite off-hours, daily clear at 9:15 AM SLT)
- [x] Stock-to-keyword connection map (utils/stock_connections.py)

## What needs building (in priority order)
1. **News RSS scraper** — Daily FT (dailyft.lk/rss), EconomyNext, LankaBIZ. Extract headlines + body, find ticker mentions, score sentiment, store in DB. Run every 30 minutes.
2. **Smart news connection engine** — Use stock_connections.py keyword map + Claude API to match news articles to affected tickers. Show "Related news" on ticker cards. Build `/news` command for reverse lookup (news event → affected stocks).
3. **X/Twitter scraper** — Monitor hashtags (#CSE, #ColomboStockExchange) and ticker-related keywords. Use ntscraper or Twitter API free tier. Run every 30 minutes.
4. **Claude sentiment scorer** — Batch scoring service. Takes raw mention text, returns -1.0 to +1.0 score. System prompt should distinguish genuine analysis from pump language. Use anthropic SDK.
5. **Facebook group scraper** — Use Apify's Facebook Groups Scraper to monitor top 5-8 public CSE groups. Extract posts + comments, ticker mentions, store mentions. Run every 30 minutes.
6. **Broker research scraper** — Scrape public research pages from CT CLSA (ctclsa.lk), NDB Securities (ndbs.lk), First Capital. Extract target prices, ratings, research dates. Store as lookup table.
7. **Morning brief generator** — Daily 8:30 AM SLT automated post to free TG channel: top 5 sentiment movers, overnight announcements, market outlook. Include news → stocks reverse lookup for overnight events.
8. **Real-time alert system** — Push to premium TG channel when: ticker velocity spikes >3x, sentiment shifts significantly, new CSE filing detected on watched stock.
9. **Expand ticker map** — Add all ~300 CSE-listed stocks with aliases.
10. **Technicals card image** — Pillow card for S/R levels, vs ASPI, spread data.
11. **Insiders card** — Scrape CSE disclosure announcements for director dealings, top 20 changes.

## Phase 2 features

### Annual Report RAG System
Build a retrieval-augmented generation (RAG) system over CSE annual reports:
1. **Download** all ~289 CSE listed company annual reports (PDFs from cse.lk)
2. **Extract text**, chunk into sections (chairman's statement, outlook, strategy, financials, risk factors)
3. **Embed** using an embedding model and store in a vector DB (ChromaDB or similar)
4. **Query** — when a ticker is looked up, search relevant chunks for management commentary, future plans, risk factors
5. **Cross-reference** news against management statements (e.g., rising material costs vs announced construction plans)
6. **"Management said" section** on the ticker card showing relevant quotes from the latest annual report (clearly labeled as sourced from annual report per Critical Rule #3)
7. **Update annually** when new reports are published (CSE fiscal year ends vary — track per company)

This is Phase 2. Phase 1 priorities remain: deploy to Railway, build scrapers (RSS, X, FB), sentiment scoring, morning brief, and real-time alerts.

## Context management
Between major features, use /clear to reset context. When working on scraper code, focus only on services/. When working on cards, focus only on utils/card_generator.py. Don't try to hold the entire project in context at once. Each subdirectory has its own CLAUDE.md with conventions specific to that area.

## Git workflow
- All new features should be built on feature branches, not main
- Branch naming: `feat/description`, `fix/description`, `chore/description`
- Pre-commit hook runs `py_compile` on all changed .py files
- Never commit .env, API keys, database files, or test images
- Merge to main only when feature is tested and working

## Testing
- Tests are in `tests/` — run with `PYTHONPATH=. python -m pytest tests/ -v`
- CSE API tests use mocks (never hit live API in tests)
- Card tests verify generation doesn't crash with missing/None data
- All ticker map aliases must point to valid tickers (tested automatically)

## Custom commands
- `/new-scraper <source>` — scaffold a new data source scraper
- `/new-card <name>` — scaffold a new Pillow card type
- `/test-ticker <ticker>` — fetch live data and generate all cards
- `/deploy` — commit, push, and verify Railway deployment

## Coding conventions
- Python 3.11+ with type hints
- Async where possible (the TG bot is fully async)
- All scrapers should be fault-tolerant — wrap external calls in try/except, log errors, never crash the bot
- Use `logger.error()` for errors, never `print()` — bare prints bypass log level control
- Use `try/finally` for database connections to prevent leaks
- Validate external API responses (check types, Content-Type header) before using
- Rate limit all user-facing handlers (current: 5 req/user/60s)
- Use the existing patterns in pulse_db.py for database operations
- Card images use the dark theme palette defined in card_generator.py
- Environment variables for all secrets (never hardcode)
- Commit messages should be descriptive: "feat: add RSS scraper for Daily FT" not "update"

## Monetization context
- Free TG channel: daily morning brief, delayed signals
- Premium TG channel (LKR 3,000-5,000/month): real-time alerts, pump warnings, full detail cards
- Payment via PayHere (Sri Lankan payment gateway)
- This is a standalone product under the CeylonVest brand, separate from Stock Wise Analytics (SWA)

## Important notes
- CSE trading hours: Mon-Fri 9:30 AM - 2:30 PM Sri Lanka Time (GMT+5:30)
- CSE API endpoints may change without notice — they're unofficial
- Sri Lanka SEC regulations: frame everything as "market intelligence" not "investment advice". Include disclaimers.
- The bot should work in both private chats and group chats
- Card images should be clean and readable on mobile (most TG users are on phones)
