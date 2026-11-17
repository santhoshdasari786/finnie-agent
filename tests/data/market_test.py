"""Market data layer: symbol mapping, quote building, failure isolation, registry. No network (yf.Ticker is faked).

Run:  .venv/bin/python -m pytest tests/data/market_test.py -v
"""
import threading

import pytest
from pydantic import ValidationError

from src.data.market import base, yfinance_provider as yfp
from src.data.market.models import Instrument, Quote
from src.data.market.yfinance_provider import YFinanceProvider, to_yahoo

pytestmark = pytest.mark.asyncio

NIFTY = Instrument(symbol="NIFTY50", exchange="INDEX")
RELIANCE = Instrument(symbol="RELIANCE")


class FakeTicker:
    """Stands in for yf.Ticker. `table` maps Yahoo symbol -> fast_info dict, or an Exception to raise."""
    table: dict = {}
    seen: list = []                    # (yahoo_symbol, thread_id) per construction

    def __init__(self, symbol):
        FakeTicker.seen.append((symbol, threading.get_ident()))
        self._v = FakeTicker.table.get(symbol)

    @property
    def fast_info(self):
        if isinstance(self._v, Exception):
            raise self._v
        if self._v is None:
            raise KeyError("unknown symbol")
        return self._v


@pytest.fixture
def fake_yf(monkeypatch):
    FakeTicker.table = {
        "^NSEI": {"last_price": 25030.349, "previous_close": 24536.6, "currency": "INR"},
        "RELIANCE.NS": {"last_price": 1320.0, "previous_close": 1313.4, "currency": "INR"},
        "TCS.BO": {"last_price": 2500.0, "previous_close": 0, "currency": "INR"},
    }
    FakeTicker.seen = []
    monkeypatch.setattr(yfp.yf, "Ticker", FakeTicker)
    return FakeTicker


# ---------------------------------------------------------------- symbol mapping
@pytest.mark.parametrize("inst, yahoo", [
    (Instrument(symbol="RELIANCE"), "RELIANCE.NS"),
    (Instrument(symbol="TCS", exchange="BSE"), "TCS.BO"),
    (Instrument(symbol="AAPL", exchange="US"), "AAPL"),
    (Instrument(symbol="NIFTY50", exchange="INDEX"), "^NSEI"),
    (Instrument(symbol="SENSEX", exchange="INDEX"), "^BSESN"),
])
async def test_symbol_mapping(inst, yahoo):
    assert to_yahoo(inst) == yahoo

async def test_unknown_index_raises_in_the_mapper():
    with pytest.raises(KeyError):
        to_yahoo(Instrument(symbol="NOSUCH", exchange="INDEX"))


# ---------------------------------------------------------------- models
async def test_instrument_defaults_to_nse_and_is_hashable():
    assert RELIANCE.exchange == "NSE" and {RELIANCE: 1}[Instrument(symbol="RELIANCE")] == 1

async def test_instrument_rejects_an_unknown_exchange():
    with pytest.raises(ValidationError):
        Instrument(symbol="X", exchange="MARS")


# ---------------------------------------------------------------- quotes
async def test_quote_is_built_from_fast_info(fake_yf):
    [q] = await YFinanceProvider().quotes([RELIANCE])
    assert isinstance(q, Quote)
    assert q.price == 1320.0 and q.currency == "INR" and q.source == "yfinance"
    assert q.change_pct == 0.5 and q.stale is False and q.as_of.tzinfo is not None
    assert q.instrument == RELIANCE

async def test_price_is_rounded_to_two_decimals(fake_yf):
    [q] = await YFinanceProvider().quotes([NIFTY])
    assert q.price == 25030.35 and q.change_pct == 2.01

async def test_zero_previous_close_gives_no_change_not_a_crash(fake_yf):
    [q] = await YFinanceProvider().quotes([Instrument(symbol="TCS", exchange="BSE")])
    assert q.price == 2500.0 and q.change_pct is None

async def test_empty_request_returns_empty_without_calling_yahoo(fake_yf):
    assert await YFinanceProvider().quotes([]) == [] and fake_yf.seen == []

async def test_order_follows_the_request(fake_yf):
    qs = await YFinanceProvider().quotes([RELIANCE, NIFTY])
    assert [q.instrument.symbol for q in qs] == ["RELIANCE", "NIFTY50"]


# ---------------------------------------------------------------- one bad symbol never sinks the batch
async def test_unknown_symbol_is_dropped_others_survive(fake_yf):
    qs = await YFinanceProvider().quotes([RELIANCE, Instrument(symbol="NOPE123"), NIFTY])
    assert [q.instrument.symbol for q in qs] == ["RELIANCE", "NIFTY50"]

async def test_yahoo_error_is_swallowed_per_symbol(fake_yf):
    fake_yf.table["RELIANCE.NS"] = RuntimeError("429 too many requests")
    qs = await YFinanceProvider().quotes([RELIANCE, NIFTY])
    assert [q.instrument.symbol for q in qs] == ["NIFTY50"]

async def test_missing_price_is_dropped(fake_yf):
    fake_yf.table["RELIANCE.NS"] = {"last_price": None, "previous_close": 1.0, "currency": "INR"}
    assert await YFinanceProvider().quotes([RELIANCE]) == []

async def test_zero_price_is_dropped_not_reported_as_a_quote(fake_yf):
    # Yahoo returns 0 for halted/delisted symbols; "RELIANCE is at 0" would be a confident wrong answer
    fake_yf.table["RELIANCE.NS"] = {"last_price": 0, "previous_close": 1313.4, "currency": "INR"}
    assert await YFinanceProvider().quotes([RELIANCE]) == []

async def test_unmapped_index_is_dropped_not_raised(fake_yf):
    assert await YFinanceProvider().quotes([Instrument(symbol="NOSUCH", exchange="INDEX")]) == []


# ---------------------------------------------------------------- blocking I/O stays off the event loop
async def test_yahoo_is_called_in_worker_threads(fake_yf):
    await YFinanceProvider().quotes([RELIANCE, NIFTY])
    assert all(tid != threading.get_ident() for _, tid in fake_yf.seen)


# ---------------------------------------------------------------- registry
async def test_yfinance_is_registered_by_name():
    assert base.PROVIDERS["yfinance"] is YFinanceProvider

async def test_provider_satisfies_the_protocol_shape():
    p = base.PROVIDERS["yfinance"]()
    assert p.name == "yfinance" and callable(p.quotes)

async def test_duplicate_registration_is_rejected(monkeypatch):
    monkeypatch.setattr(base, "PROVIDERS", {"x": object})
    with pytest.raises(ValueError, match="already registered"):
        base.register_provider("x")(type("Other", (), {}))

async def test_a_new_provider_can_be_attached_by_name(monkeypatch):
    monkeypatch.setattr(base, "PROVIDERS", {})
    @base.register_provider("alpha")
    class Alpha:
        name = "alpha"
        async def quotes(self, instruments):
            return []
    assert base.PROVIDERS["alpha"] is Alpha
