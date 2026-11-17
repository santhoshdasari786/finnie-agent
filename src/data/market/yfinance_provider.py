import asyncio
from datetime import datetime, timezone
import yfinance as yf
from src.data.market.base import register_provider
from src.data.market.models import Instrument, PriceHistory, PricePoint, Quote

_INDEXES = {"NIFTY50": "^NSEI", "SENSEX": "^BSESN"}      # canonical name -> Yahoo symbol

def to_yahoo(i: Instrument) -> str:
    if i.exchange == "INDEX":
        return _INDEXES[i.symbol]
    return {"NSE": f"{i.symbol}.NS", "BSE": f"{i.symbol}.BO"}.get(i.exchange, i.symbol)

def _fetch_one(i: Instrument) -> Quote | None:
    """Blocking: runs in a worker thread. None = this symbol failed (never raise for one bad symbol)."""
    try:
        fi = yf.Ticker(to_yahoo(i)).fast_info
        price, prev = fi["last_price"], fi["previous_close"]
        if not price:
            return None
        change = round((price - prev) / prev * 100, 2) if prev else None
        return Quote(instrument=i, price=round(float(price), 2), change_pct=change,
                     currency=fi["currency"], as_of=datetime.now(timezone.utc), source="yfinance")
    except Exception:
        return None

_PERIODS = {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y"}

def _fetch_history(i: Instrument, rng: str) -> PriceHistory | None:
    """Blocking: runs in a worker thread. None = no usable data (never raise for one bad symbol)."""
    try:
        ticker = yf.Ticker(to_yahoo(i))
        table = ticker.history(period=_PERIODS[rng], interval="1d", auto_adjust=True)
        points = [PricePoint(date=idx.date(), close=round(float(c), 2))
                  for idx, c in table["Close"].items() if c > 0]
        if not points:
            return None
        try:
            currency = ticker.fast_info["currency"]
        except Exception:
            currency = "INR"
        return PriceHistory(instrument=i, range=rng, currency=currency, points=points,
                            as_of=datetime.now(timezone.utc), source="yfinance")
    except Exception:
        return None


@register_provider("yfinance")
class YFinanceProvider:
    name = "yfinance"

    async def quotes(self, instruments: list[Instrument]) -> list[Quote]:
        results = await asyncio.gather(*(asyncio.to_thread(_fetch_one, i) for i in instruments))
        return [q for q in results if q is not None]

    async def history(self, instrument: Instrument, range: str) -> PriceHistory | None:
        if range not in _PERIODS:
            raise ValueError(f"unknown range {range!r}")
        return await asyncio.to_thread(_fetch_history, instrument, range)
