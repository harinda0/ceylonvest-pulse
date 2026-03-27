Create a new Pillow image card for: $ARGUMENTS

Follow the v2 design system in `utils/card_generator.py`:

1. Add a new `generate_{card_name}_card(...)` function in `utils/card_generator.py`:
   - Use the existing color constants (BG, SURFACE, TEXT_PRIMARY, etc.)
   - Use the existing font constants (FONT_TICKER, FONT_LABEL, FONT_VALUE, etc.)
   - Use existing helpers: `_draw_header()`, `_draw_metric()`, `_draw_divider()`, `_draw_footer()`
   - Card width: 520px (match existing cards)
   - Start with `_draw_header()` for the ticker/company header
   - Use y-coordinate accumulator pattern: `y = start_y` then `y += row_height`
   - End with `_draw_footer()`
   - Handle ALL optional params as `| None` with graceful fallback to "N/A"
   - Return `BytesIO` with PNG data

2. Wire into the bot (`bot/main.py`):
   - Import the new function
   - Create `async def send_{card_name}_card(query, ticker)` handler
   - Add inline keyboard button in `handle_ticker_message()`
   - Add `elif action == "prefix":` in `handle_callback()`

3. Test the card renders without errors:
   ```python
   PYTHONPATH=. python -c "from utils.card_generator import generate_{card_name}_card; buf = generate_{card_name}_card(...); print(f'OK: {len(buf.getvalue())} bytes')"
   ```

4. Save test output to verify visual quality:
   ```python
   from PIL import Image; Image.open(buf).save('data/test_{card_name}.png')
   ```
