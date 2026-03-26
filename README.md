# CeylonVest Pulse

AI-powered CSE market intelligence bot for Telegram.
Paste a ticker → get instant stock data, sentiment analysis, and pump detection.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python -m bot.main
```

## Environment Variables

- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `ANTHROPIC_API_KEY` — for sentiment scoring
- `PULSE_FREE_CHANNEL_ID` — TG channel ID for free morning briefs
- `PULSE_PREMIUM_CHANNEL_ID` — TG channel ID for premium alerts

## Architecture

```
bot/            — Telegram bot handlers
services/       — CSE API, sentiment scoring, scraping
utils/          — Ticker map, card generator, helpers
data/           — SQLite DB, baseline data
assets/fonts/   — Fonts for card image generation
```
