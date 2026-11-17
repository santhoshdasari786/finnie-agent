import asyncio
from src.data.market.base import PROVIDERS
import src.data.market.yfinance_provider           # importing it registers "yfinance"
from src.data.market.models import Instrument

async def main():
    p = PROVIDERS["yfinance"]()
    qs = await p.quotes([Instrument(symbol="NIFTY50", exchange="INDEX"),
                         Instrument(symbol="RELIANCE"), Instrument(symbol="NOPE123")])
    for q in qs:
        print(q.instrument.symbol, q.price, f"{q.change_pct}%", q.currency, q.source)

asyncio.run(main())
