from src.data.market.models import Instrument, PriceHistory

HISTORY_RANGES = ("1m", "3m", "6m", "1y")
_INDEX_NAMES = {"NIFTY50": "Nifty 50", "SENSEX": "Sensex"}


def display_name(instrument: Instrument) -> str:
    return _INDEX_NAMES.get(instrument.symbol, instrument.symbol) if instrument.exchange == "INDEX" else instrument.symbol


def summarize(h: PriceHistory) -> dict:
    """Everything the chart shows, computed here so the browser never does arithmetic."""
    closes = [p.close for p in h.points]
    first, last = closes[0], closes[-1]
    return {
        "symbol": h.instrument.symbol, "name": display_name(h.instrument), "range": h.range,
        "currency": h.currency, "source": h.source, "as_of": h.as_of.isoformat(),
        "points": [{"date": p.date.isoformat(), "close": p.close} for p in h.points],
        "latest": last, "high": max(closes), "low": min(closes),
        "change_pct": round((last - first) / first * 100, 2) if first else None,
    }
