"""Price history: provider (yfinance faked), symbol resolution, and the summary numbers the chart shows.

Run:  .venv/bin/python -m pytest tests/data/market_history_test.py -v
No network: yf.Ticker is replaced by a fake that returns a pandas table.

Contract
  provider.history(instrument, range) -> PriceHistory | None      range is one of "1m", "3m", "6m", "1y"
  * None means "no usable data" (unknown symbol, empty table, any failure): never an exception for one bad symbol
  * points are oldest first, one per trading day, closes rounded to 2 decimals, bad rows (NaN, zero) dropped
  * the blocking yfinance call runs in a worker thread
  resolve_instrument(text) -> Instrument | None                   "nifty" / "^NSEI" -> the index, "tcs" -> TCS, junk -> None
  summarize(history) -> dict                                      latest, high, low and the change over the range, in code
"""
import threading
from datetime import date, datetime, timezone

import pandas as pd
import pytest
from pydantic import ValidationError

from src.data.market import yfinance_provider as yfp
from src.data.market.history import HISTORY_RANGES, display_name, summarize
from src.data.market.models import Instrument, PriceHistory, PricePoint
from src.data.market.symbols import resolve_instrument
from src.data.market.yfinance_provider import YFinanceProvider

pytestmark = pytest.mark.asyncio

NIFTY = Instrument(symbol="NIFTY50", exchange="INDEX")
TCS = Instrument(symbol="TCS")


def table(closes, start="2026-08-03", tz=None):
    index = pd.bdate_range(start, periods=len(closes), tz=tz)
    return pd.DataFrame({"Close": closes}, index=index)


class FakeTicker:
    tables: dict = {}
    calls: list = []                 # (yahoo symbol, kwargs, thread id)
    currencies: dict = {}

    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, **kwargs):
        FakeTicker.calls.append((self.symbol, kwargs, threading.get_ident()))
        value = FakeTicker.tables.get(self.symbol)
        if isinstance(value, Exception):
            raise value
        return value if value is not None else pd.DataFrame({"Close": []})

    @property
    def fast_info(self):
        value = FakeTicker.currencies.get(self.symbol)
        if value is None:
            raise KeyError("no info")
        return {"currency": value}


@pytest.fixture
def fake_yf(monkeypatch):
    FakeTicker.tables = {"^NSEI": table([24000.123, 24100.5, 24050.0]), "TCS.NS": table([3500.0, 3510.456])}
    FakeTicker.calls = []
    FakeTicker.currencies = {}
    monkeypatch.setattr(yfp.yf, "Ticker", FakeTicker)
    return FakeTicker


# ---------------------------------------------------------------- the model
async def test_the_four_ranges_are_fixed():
    assert HISTORY_RANGES == ("1m", "3m", "6m", "1y")


async def test_price_point_needs_a_date_and_a_number():
    p = PricePoint(date=date(2026, 8, 3), close=100.5)
    assert p.date == date(2026, 8, 3) and p.close == 100.5
    with pytest.raises(ValidationError):
        PricePoint(date="not a date", close=1)
    with pytest.raises(ValidationError):
        PricePoint(date=date(2026, 8, 3), close="abc")


# ---------------------------------------------------------------- the provider
async def test_returns_points_oldest_first_rounded_to_two_decimals(fake_yf):
    h = await YFinanceProvider().history(NIFTY, "3m")
    assert isinstance(h, PriceHistory)
    assert [p.close for p in h.points] == [24000.12, 24100.5, 24050.0]
    assert [p.date for p in h.points] == [date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5)]
    assert h.instrument == NIFTY and h.range == "3m" and h.source == "yfinance"


async def test_the_symbol_is_mapped_to_yahoo(fake_yf):
    await YFinanceProvider().history(NIFTY, "1m")
    await YFinanceProvider().history(TCS, "1m")
    assert [c[0] for c in fake_yf.calls] == ["^NSEI", "TCS.NS"]


@pytest.mark.parametrize("ours, yahoo", [("1m", "1mo"), ("3m", "3mo"), ("6m", "6mo"), ("1y", "1y")])
async def test_each_range_asks_yahoo_for_its_period_with_daily_bars(fake_yf, ours, yahoo):
    await YFinanceProvider().history(TCS, ours)
    kwargs = fake_yf.calls[0][1]
    assert kwargs["period"] == yahoo and kwargs["interval"] == "1d"


async def test_prices_are_adjusted_for_splits_and_dividends(fake_yf):
    await YFinanceProvider().history(TCS, "3m")
    assert fake_yf.calls[0][1]["auto_adjust"] is True


async def test_an_unknown_range_is_a_programming_error(fake_yf):
    with pytest.raises(ValueError):
        await YFinanceProvider().history(TCS, "10y")
    assert fake_yf.calls == []


async def test_the_blocking_call_runs_off_the_event_loop(fake_yf):
    await YFinanceProvider().history(TCS, "3m")
    assert fake_yf.calls[0][2] != threading.get_ident()


async def test_as_of_is_a_timezone_aware_now(fake_yf):
    before = datetime.now(timezone.utc)
    h = await YFinanceProvider().history(TCS, "3m")
    assert h.as_of.tzinfo is not None and before <= h.as_of <= datetime.now(timezone.utc)


async def test_currency_comes_from_yahoo_and_defaults_to_rupees(fake_yf):
    fake_yf.currencies = {"TCS.NS": "USD"}
    assert (await YFinanceProvider().history(TCS, "3m")).currency == "USD"
    assert (await YFinanceProvider().history(NIFTY, "3m")).currency == "INR"      # fast_info raises -> default


async def test_empty_table_is_none(fake_yf):
    fake_yf.tables = {"TCS.NS": pd.DataFrame({"Close": []})}
    assert await YFinanceProvider().history(TCS, "3m") is None


async def test_unknown_symbol_is_none(fake_yf):
    assert await YFinanceProvider().history(Instrument(symbol="NOSUCH"), "3m") is None


async def test_a_failure_is_none_not_an_exception(fake_yf):
    fake_yf.tables = {"TCS.NS": RuntimeError("yahoo is down")}
    assert await YFinanceProvider().history(TCS, "3m") is None


async def test_nan_and_zero_closes_are_dropped(fake_yf):
    fake_yf.tables = {"TCS.NS": table([100.0, float("nan"), 0.0, -5.0, 102.0])}
    h = await YFinanceProvider().history(TCS, "3m")
    assert [p.close for p in h.points] == [100.0, 102.0]


async def test_a_table_with_only_bad_rows_is_none(fake_yf):
    fake_yf.tables = {"TCS.NS": table([float("nan"), 0.0])}
    assert await YFinanceProvider().history(TCS, "3m") is None


async def test_dates_use_the_exchange_calendar_day(fake_yf):
    fake_yf.tables = {"TCS.NS": table([100.0, 101.0], start="2026-08-03", tz="Asia/Kolkata")}
    h = await YFinanceProvider().history(TCS, "3m")
    assert [p.date for p in h.points] == [date(2026, 8, 3), date(2026, 8, 4)]


async def test_history_is_registered_on_the_default_provider():
    from src.data.market.base import PROVIDERS
    assert callable(getattr(PROVIDERS["yfinance"](), "history", None))


# ---------------------------------------------------------------- resolve_instrument
@pytest.mark.parametrize("text", ["NIFTY", "nifty", "Nifty50", "NIFTY50", "^NSEI", " nifty "])
async def test_nifty_spellings_resolve_to_the_index(text):
    assert resolve_instrument(text) == NIFTY


@pytest.mark.parametrize("text", ["SENSEX", "sensex", "^BSESN"])
async def test_sensex_spellings_resolve_to_the_index(text):
    assert resolve_instrument(text) == Instrument(symbol="SENSEX", exchange="INDEX")


@pytest.mark.parametrize("text, symbol", [("tcs", "TCS"), (" RELIANCE ", "RELIANCE"), ("M&M", "M&M"), ("BAJAJ-AUTO", "BAJAJ-AUTO")])
async def test_a_plain_ticker_is_an_nse_stock(text, symbol):
    assert resolve_instrument(text) == Instrument(symbol=symbol)


@pytest.mark.parametrize("text", ["", "   ", "^GSPC", "^DJI", "TCS.NS", "TCS; DROP", "<script>", "A" * 21, "NIFTY 50", "a/b"])
async def test_anything_else_is_rejected(text):
    assert resolve_instrument(text) is None


# ---------------------------------------------------------------- names
async def test_indexes_get_their_display_name_and_stocks_keep_the_ticker():
    assert display_name(NIFTY) == "Nifty 50"
    assert display_name(Instrument(symbol="SENSEX", exchange="INDEX")) == "Sensex"
    assert display_name(TCS) == "TCS"


# ---------------------------------------------------------------- summarize
def history(closes, currency="INR", rng="3m"):
    return PriceHistory(
        instrument=TCS, range=rng, currency=currency, source="yfinance",
        as_of=datetime(2026, 11, 17, 5, 30, tzinfo=timezone.utc),
        points=[PricePoint(date=date(2026, 8, 3 + i), close=c) for i, c in enumerate(closes)])


async def test_summary_has_the_fields_the_chart_needs():
    s = summarize(history([100.0, 110.0, 105.0]))
    assert set(s) == {"symbol", "name", "range", "currency", "source", "as_of", "points",
                      "latest", "change_pct", "high", "low"}


async def test_summary_numbers():
    s = summarize(history([100.0, 120.0, 90.0, 110.0]))
    assert s["latest"] == 110.0 and s["high"] == 120.0 and s["low"] == 90.0
    assert s["change_pct"] == 10.0                   # first 100 -> last 110


async def test_change_is_negative_when_the_price_fell_and_rounded_to_two_decimals():
    assert summarize(history([200.0, 150.0]))["change_pct"] == -25.0
    assert summarize(history([3.0, 4.0]))["change_pct"] == 33.33


async def test_change_is_none_when_the_first_price_is_zero_free_of_division():
    # closes are validated > 0 by the provider, but the maths must still never divide by zero
    s = summarize(history([0.0, 5.0]))
    assert s["change_pct"] is None


async def test_summary_points_are_plain_json_values():
    s = summarize(history([100.0, 110.0]))
    assert s["points"] == [{"date": "2026-08-03", "close": 100.0}, {"date": "2026-08-04", "close": 110.0}]
    assert isinstance(s["as_of"], str) and s["as_of"].startswith("2026-11-17T05:30")


async def test_summary_labels_come_from_the_history():
    s = summarize(history([100.0, 110.0], currency="USD", rng="1y"))
    assert (s["symbol"], s["name"], s["range"], s["currency"], s["source"]) == ("TCS", "TCS", "1y", "USD", "yfinance")
    n = PriceHistory(instrument=NIFTY, range="1m", currency="INR", source="yfinance", as_of=datetime.now(timezone.utc),
                     points=[PricePoint(date=date(2026, 8, 3), close=1.0)])
    assert (summarize(n)["symbol"], summarize(n)["name"]) == ("NIFTY50", "Nifty 50")


async def test_a_single_point_has_no_change():
    s = summarize(history([100.0]))
    assert s["latest"] == 100.0 and s["change_pct"] == 0.0
