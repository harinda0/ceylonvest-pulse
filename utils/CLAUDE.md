# utils/ — Card Generator & Mapping Utilities

## Card generator conventions (card_generator.py)
- All cards use the v2 premium design system with Inter font family
- Dark theme palette: `#11111e` base, `#1a1a2e` surface, `#2a2a3e` borders
- Card width: 520px fixed, height: dynamic based on content
- Font fallback chain: Inter -> Segoe UI (Windows) -> DejaVu Sans (Linux)
- All `generate_*_card()` functions return `BytesIO` ready for Telegram
- Handle `None` values gracefully — show "N/A" or hide the section entirely
- Never crash on missing data — every field could be `None`

## Adding a new card type
1. Define `generate_new_card(...)` function in `card_generator.py`
2. Use existing helpers: `_draw_header()`, `_draw_metric()`, `_draw_divider()`, `_draw_footer()`
3. Follow the y-coordinate accumulator pattern for layout
4. Return `BytesIO` with PNG data
5. Wire into `bot/main.py` — add import, create `send_new_card()` handler, add button

## Ticker map maintenance (ticker_map.py)
- `TICKER_TO_CSE`: official ticker -> CSE API symbol (`KPHL` -> `KPHL.N0000`)
- `ALIASES`: lowercase aliases -> official ticker
- `SECTORS`: ticker -> sector string
- When adding a stock, update all three dicts
- Aliases should include: ticker lowercase, full company name, common abbreviations, known misspellings

## Stock connections (stock_connections.py)
- `DIRECTOR_MAP`: director name -> portfolio info (use explicit misspelling aliases, no fuzzy matching)
- `KEYWORD_MAP`: ticker -> categorized keywords (direct, sector, supply_chain, macro, policy)
- `SECTOR_THEMES`: macro theme -> affected tickers with impact explanation
- When adding a director, also add common misspellings to `_DIRECTOR_MISSPELLINGS`
