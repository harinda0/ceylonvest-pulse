Fetch live data for ticker "$ARGUMENTS" and show what each card would display.

Run this test:

```python
PYTHONPATH=. python -c "
from utils.ticker_map import resolve_ticker, get_cse_symbol, get_sector, get_company_name
from services.cse_api import get_stock_data, compute_support_resistance
from utils.card_generator import generate_main_card, generate_fundamentals_card, generate_technicals_card
from services.pulse_db import get_mention_velocity, get_avg_sentiment

ticker = resolve_ticker('$ARGUMENTS')
if not ticker:
    print(f'Ticker not found: $ARGUMENTS')
    exit(1)

cse = get_cse_symbol(ticker)
sector = get_sector(ticker)
name = get_company_name(ticker)
print(f'Ticker: {ticker} | CSE: {cse} | Sector: {sector} | Name: {name}')

stock = get_stock_data(ticker, cse, sector, name)
if not stock:
    print('ERROR: Could not fetch stock data')
    exit(1)

print(f'Price: LKR {stock.last_price:.2f}')
print(f'Change: {stock.change:+.2f} ({stock.change_pct:+.1f}%)')
print(f'Volume: {stock.volume:,}')
print(f'Market Cap: LKR {stock.market_cap/1e9:.1f}B')
print(f'High/Low: {stock.high:.2f} / {stock.low:.2f}')
print(f'Prev Close: {stock.prev_close:.2f}')
print(f'52W: {stock.high_52w:.2f} / {stock.low_52w:.2f}')
print(f'52W Position: {stock.price_position_52w}%')

vel = get_mention_velocity(ticker)
sent = get_avg_sentiment(ticker)
print(f'Sentiment: {sent} | Mentions 24h: {vel[\"count_24h\"]} | Velocity: {vel[\"velocity\"]}x')

# Generate all 3 cards
sr = compute_support_resistance(stock)
buf1 = generate_main_card(ticker=ticker, company_name=name, sector=sector, last_price=stock.last_price, change=stock.change, change_pct=stock.change_pct, market_cap=stock.market_cap, volume=stock.volume, pe_ratio=stock.pe_ratio, spread_pct=stock.spread_pct, high=stock.high, low=stock.low, prev_close=stock.prev_close, high_52w=stock.high_52w, low_52w=stock.low_52w, price_position_52w=stock.price_position_52w, sentiment_score=sent, mention_count_24h=vel['count_24h'], mention_velocity=vel['velocity'])
buf2 = generate_fundamentals_card(ticker=ticker, eps=stock.eps, book_value=stock.book_value, nav=stock.nav, pb_ratio=stock.pb_ratio, div_yield=stock.div_yield, div_ex_date=None, foreign_pct=stock.foreign_pct, local_pct=None, foreign_net=None, broker_coverage=None)
buf3 = generate_technicals_card(ticker=ticker, company_name=name, last_price=stock.last_price, change=stock.change, change_pct=stock.change_pct, high=stock.high, low=stock.low, prev_close=stock.prev_close, high_wtd=stock.high_wtd, low_wtd=stock.low_wtd, high_mtd=stock.high_mtd, low_mtd=stock.low_mtd, high_ytd=stock.high_ytd, low_ytd=stock.low_ytd, high_52w=stock.high_52w, low_52w=stock.low_52w, support=sr.get('support'), resistance=sr.get('resistance'), beta_aspi=stock.beta_aspi, beta_spsl=stock.beta_spsl, volume=stock.volume, avg_daily_volume_mtd=stock.avg_daily_volume_mtd, price_position_52w=stock.price_position_52w, spread_pct=stock.spread_pct)

from PIL import Image
Image.open(buf1).save(f'data/test_{ticker}_main.png')
Image.open(buf2).save(f'data/test_{ticker}_fund.png')
Image.open(buf3).save(f'data/test_{ticker}_tech.png')
print(f'Cards saved: data/test_{ticker}_main.png, _fund.png, _tech.png')
"
```

Then show me the generated card images so I can visually verify them.
