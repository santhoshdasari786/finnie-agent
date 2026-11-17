from src.data.market.models import Instrument
from src.data.portfolio.base import ConnectInfo, SourceStatus, register_source
from src.data.portfolio.models import Holding

_SAMPLE = [
    # symbol, quantity, avg_price, asset_class
    ("RELIANCE", 10, 2400.0, "equity"),
    ("TCS", 5, 3300.0, "equity"),
    ("INFY", 20, 1450.0, "equity"),
    ("HDFCBANK", 15, 1550.0, "equity"),
    ("NIFTYBEES", 100, 230.0, "equity_fund"),
    ("LIQUIDBEES", 5, 1000.0, "debt_fund"),
    ("GOLDBEES", 200, 55.0, "gold"),
]

@register_source("sample")
class SampleSource:
    name = "sample"
    label = "Sample portfolio (demo data, no login)"

    async def status(self) -> SourceStatus:
        return "available"

    async def connect(self, **params) -> ConnectInfo:
        return ConnectInfo(connected=True, message="Connected the sample portfolio (demo data, not yours).")

    async def holdings(self) -> list[Holding]:
        return [Holding(instrument=Instrument(symbol=s), quantity=q, avg_price=p, asset_class=c)
                for s, q, p, c in _SAMPLE]
