"""yfinance provider: which failures are TEMPORARY (ProviderUnavailable) and which are plain "not found" (None / no quote).

Run:  .venv/bin/python -m pytest tests/data/market_transient_test.py -v
No network: yf.Ticker is faked.

Why: the cache retries and falls back to old data only for temporary trouble (rate limit, network). A ticker that does
not exist must come back as "not found" at once, never be retried, and never be reported as "Yahoo is down".

Contract
  rate limit (YFRateLimitError), network errors (OSError family, incl. curl_cffi), timeouts  -> ProviderUnavailable
  unknown symbol, missing data, any other error                                              -> None / no quote
  quotes(): one symbol failing temporarily does not hide the others; if no quote came back and one failed
            temporarily, ProviderUnavailable is raised
"""
import pandas as pd
import pytest
from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError
from yfinance.exceptions import YFPricesMissingError, YFRateLimitError, YFTickerMissingError

from src.data.market import yfinance_provider as yfp
from src.data.market.base import ProviderUnavailable
from src.data.market.models import Instrument
from src.data.market.yfinance_provider import YFinanceProvider

pytestmark = pytest.mark.asyncio

TCS, INFY, NOPE = Instrument(symbol="TCS"), Instrument(symbol="INFY"), Instrument(symbol="NOPE")
GOOD = {"last_price": 3500.0, "previous_close": 3400.0, "currency": "INR"}
TABLE = pd.DataFrame({"Close": [100.0, 101.0]}, index=pd.bdate_range("2026-08-03", periods=2))


class FakeTicker:
    info: dict = {}

    def __init__(self, symbol):
        self._v = FakeTicker.info.get(symbol)

    @property
    def fast_info(self):
        if isinstance(self._v, Exception):
            raise self._v
        if self._v is None:
            raise KeyError("unknown symbol")
        return self._v

    def history(self, **kwargs):
        if isinstance(self._v, Exception):
            raise self._v
        return TABLE if self._v is not None else pd.DataFrame({"Close": []})


@pytest.fixture
def fake_yf(monkeypatch):
    FakeTicker.info = {"TCS.NS": GOOD, "INFY.NS": GOOD}
    monkeypatch.setattr(yfp.yf, "Ticker", FakeTicker)
    return FakeTicker


TRANSIENT = [
    YFRateLimitError(),
    ConnectionError("connection reset"),
    TimeoutError("timed out"),
    OSError("network is unreachable"),
    CurlConnectionError("could not connect"),
]
IDS = ["rate-limit", "connection-error", "timeout", "os-error", "curl-connection-error"]


# ---------------------------------------------------------------- quotes
@pytest.mark.parametrize("error", TRANSIENT, ids=IDS)
async def test_a_temporary_failure_for_the_only_symbol_is_raised(fake_yf, error):
    fake_yf.info = {"TCS.NS": error}
    with pytest.raises(ProviderUnavailable):
        await YFinanceProvider().quotes([TCS])


@pytest.mark.parametrize("error", TRANSIENT, ids=IDS)
async def test_one_temporary_failure_does_not_hide_the_other_quotes(fake_yf, error):
    fake_yf.info = {"TCS.NS": error, "INFY.NS": GOOD}
    got = await YFinanceProvider().quotes([TCS, INFY])
    assert [q.instrument.symbol for q in got] == ["INFY"]


async def test_the_original_error_is_kept_as_the_cause(fake_yf):
    fake_yf.info = {"TCS.NS": YFRateLimitError()}
    with pytest.raises(ProviderUnavailable) as info:
        await YFinanceProvider().quotes([TCS])
    assert isinstance(info.value.__cause__, YFRateLimitError)


@pytest.mark.parametrize("error", [KeyError("x"), YFTickerMissingError("NOPE", "delisted"), RuntimeError("weird"), ValueError("bad")],
                         ids=["key-error", "ticker-missing", "runtime-error", "value-error"])
async def test_anything_else_is_just_not_found(fake_yf, error):
    fake_yf.info = {"NOPE.NS": error}
    assert await YFinanceProvider().quotes([NOPE]) == []


async def test_an_unknown_symbol_is_not_found_not_an_outage(fake_yf):
    assert await YFinanceProvider().quotes([NOPE]) == []


async def test_not_found_next_to_a_temporary_failure_still_raises(fake_yf):
    fake_yf.info = {"TCS.NS": YFRateLimitError()}              # NOPE is simply unknown
    with pytest.raises(ProviderUnavailable):
        await YFinanceProvider().quotes([TCS, NOPE])


async def test_not_found_next_to_a_good_quote_is_a_partial_answer(fake_yf):
    got = await YFinanceProvider().quotes([TCS, NOPE])
    assert [q.instrument.symbol for q in got] == ["TCS"]


# ---------------------------------------------------------------- history
@pytest.mark.parametrize("error", TRANSIENT, ids=IDS)
async def test_history_raises_for_a_temporary_failure(fake_yf, error):
    fake_yf.info = {"TCS.NS": error}
    with pytest.raises(ProviderUnavailable):
        await YFinanceProvider().history(TCS, "3m")


@pytest.mark.parametrize("error", [YFTickerMissingError("NOPE", "delisted"), YFPricesMissingError("NOPE", "no prices"), RuntimeError("weird")],
                         ids=["ticker-missing", "prices-missing", "runtime-error"])
async def test_history_not_found_is_none(fake_yf, error):
    fake_yf.info = {"NOPE.NS": error}
    assert await YFinanceProvider().history(NOPE, "3m") is None


async def test_history_for_an_unknown_symbol_is_none(fake_yf):
    assert await YFinanceProvider().history(NOPE, "3m") is None


async def test_history_still_works(fake_yf):
    h = await YFinanceProvider().history(TCS, "3m")
    assert [p.close for p in h.points] == [100.0, 101.0] and h.stale is False


async def test_the_unavailable_error_is_an_ordinary_exception():
    assert issubclass(ProviderUnavailable, Exception) and not issubclass(ProviderUnavailable, OSError)
