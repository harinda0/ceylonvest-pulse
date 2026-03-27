# bot/ — Telegram Bot Handlers

## Conventions
- All handlers are async functions using `python-telegram-bot` 21.x
- Handler signature: `async def handler_name(update: Update, context: ContextTypes.DEFAULT_TYPE)`
- Callback handlers receive `query` (from `update.callback_query`), not `update`

## Error handling
- Never let exceptions crash the bot — wrap external calls (CSE API, DB) in try/except
- If data fetch fails, reply with a user-friendly message, never a stack trace
- Log errors with `logger.error()`, never `print()`

## Rate limiting
- All user-facing handlers must check `_is_rate_limited(user_id)` before doing work
- Current limit: 5 requests per user per 60 seconds
- Rate-limited users get a polite message, not silence

## Callback data validation
- Always validate `ticker` from callback data against `TICKER_TO_CSE` before use
- Never trust callback data — Telegram clients can send arbitrary strings

## Card generation flow
1. Fetch stock data via `get_stock_data()`
2. Generate card image via `generate_*_card()` functions
3. Send as `reply_photo()` with inline keyboard for detail cards
4. Detail cards (fundamentals, technicals) are sent via callback handlers

## Adding a new command
1. Create `async def new_command(update, context)` function
2. Register with `app.add_handler(CommandHandler("name", new_command))` in `main()`
3. Add to the help text in `start_command()`

## Adding a new detail card button
1. Add button to the `InlineKeyboardMarkup` in `handle_ticker_message()`
2. Add `elif action == "prefix":` branch in `handle_callback()`
3. Create `async def send_new_card(query, ticker)` function
