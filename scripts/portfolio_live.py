import asyncio
from src.data.market.base import PROVIDERS
import src.data.market.yfinance_provider            # registers "yfinance"
from src.data.portfolio.metrics import compute_portfolio_metrics
from src.data.portfolio.pricing import price_holdings
from src.data.portfolio.store import ConnectionStore
import src.data.portfolio.sample                    # registers "sample"

async def main():
    store = ConnectionStore()
    print([n for n, _ in store.options()])
    print((await store.connect("demo", "sample")).message)
    priced = await price_holdings(await store.holdings("demo"), PROVIDERS["yfinance"]())
    print("as_of:", priced.as_of, "| sources:", priced.sources, "| unquoted:", priced.unquoted)
    m = compute_portfolio_metrics(priced.holdings)
    print(f"total ₹{m.total_value:,.2f} | diversification {m.diversification_score} | risk {m.risk_assessment}")
    for h in m.holdings:
        print(f"  {h.symbol:<11}{h.allocation_pct:>6}%  ₹{h.value:>10,.2f}  pnl {h.pnl_pct}")
    print(m.by_asset_class)

asyncio.run(main())
