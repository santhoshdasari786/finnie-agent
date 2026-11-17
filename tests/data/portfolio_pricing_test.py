"""price_holdings: fill missing prices from a MarketDataProvider. No network (fake provider).

Run:  .venv/bin/python -m pytest tests/data/portfolio_pricing_test.py -v
Rules pinned here:
  * a holding that already has a price keeps it and is NOT looked up
  * a missing (None or 0) price is filled from the provider; no quote -> stays unpriced (never guessed)
  * ONE provider call for all the instruments that need a price, de-duplicated; none when nothing needs one
  * the inputs are never mutated; the result reports WHEN and FROM WHERE the prices came
"""
from datetime import datetime, timedelta, timezone

import pytest

from src.data.market.models import Instrument, Quote
from src.data.portfolio.metrics import compute_portfolio_metrics
from src.data.portfolio.models import Holding
from src.data.portfolio.pricing import PricingResult, price_holdings
from src.data.portfolio.sample import SampleSource

pytestmark = pytest.mark.asyncio

T0 = datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)


def inst(symbol, exchange="NSE"):
    return Instrument(symbol=symbol, exchange=exchange)

def hold(symbol, qty=1, price=None, exchange="NSE"):
    return Holding(instrument=inst(symbol, exchange), quantity=qty, current_price=price)

def quote(symbol, price, exchange="NSE", as_of=T0, source="yfinance"):
    return Quote(instrument=inst(symbol, exchange), price=price, currency="INR", as_of=as_of, source=source)


class FakeProvider:
    name = "fake"

    def __init__(self, quotes=(), error=None):
        self.table = {q.instrument: q for q in quotes}
        self.error = error
        self.calls: list[list[Instrument]] = []

    async def quotes(self, instruments):
        self.calls.append(list(instruments))
        if self.error:
            raise self.error
        return [self.table[i] for i in instruments if i in self.table]


# ---------------------------------------------------------------- filling
async def test_missing_price_is_filled_from_the_provider():
    r = await price_holdings([hold("TCS", 5)], FakeProvider([quote("TCS", 2500.0)]))
    assert isinstance(r, PricingResult) and r.holdings[0].current_price == 2500.0

async def test_zero_price_counts_as_missing():
    r = await price_holdings([hold("TCS", 5, price=0)], FakeProvider([quote("TCS", 2500.0)]))
    assert r.holdings[0].current_price == 2500.0

async def test_existing_price_is_kept_and_not_looked_up():
    p = FakeProvider([quote("TCS", 9999.0), quote("INFY", 1500.0)])
    r = await price_holdings([hold("TCS", 5, price=2400.0), hold("INFY", 2)], p)
    assert [h.current_price for h in r.holdings] == [2400.0, 1500.0]
    assert p.calls == [[inst("INFY")]]                               # TCS was never asked for

async def test_a_provider_that_returns_extra_quotes_cannot_overwrite_a_held_price():
    class Chatty(FakeProvider):
        async def quotes(self, instruments):            # ignores the request, returns everything it knows
            self.calls.append(list(instruments))
            return list(self.table.values())
    p = Chatty([quote("TCS", 1.0), quote("INFY", 1500.0)])
    r = await price_holdings([hold("TCS", price=2400.0), hold("INFY")], p)
    assert [h.current_price for h in r.holdings] == [2400.0, 1500.0]       # e.g. a live Kite price beats a stale one

async def test_no_quote_leaves_the_holding_unpriced():
    r = await price_holdings([hold("TCS"), hold("GHOST")], FakeProvider([quote("TCS", 2500.0)]))
    assert [h.current_price for h in r.holdings] == [2500.0, None]

async def test_other_fields_survive_pricing():
    h = Holding(instrument=inst("TCS"), quantity=5, avg_price=2000.0, asset_class="equity")
    [out] = (await price_holdings([h], FakeProvider([quote("TCS", 2500.0)]))).holdings
    assert (out.quantity, out.avg_price, out.asset_class, out.instrument) == (5, 2000.0, "equity", inst("TCS"))

async def test_order_is_preserved():
    hs = [hold("C"), hold("A"), hold("B")]
    r = await price_holdings(hs, FakeProvider([quote(s, 1.0) for s in "ABC"]))
    assert [h.instrument.symbol for h in r.holdings] == ["C", "A", "B"]


# ---------------------------------------------------------------- calls to the provider
async def test_one_call_with_deduplicated_instruments():
    p = FakeProvider([quote("TCS", 2500.0)])
    await price_holdings([hold("TCS", 1), hold("TCS", 2)], p)       # same instrument from two sources
    assert p.calls == [[inst("TCS")]]

async def test_no_call_when_everything_is_already_priced():
    p = FakeProvider()
    r = await price_holdings([hold("TCS", price=2400.0)], p)
    assert p.calls == [] and r.as_of is None and r.sources == []

async def test_empty_input_makes_no_call():
    p = FakeProvider()
    r = await price_holdings([], p)
    assert p.calls == [] and r.holdings == []

async def test_exchange_is_respected():
    p = FakeProvider([quote("TCS", 2490.0, exchange="BSE")])
    r = await price_holdings([hold("TCS", exchange="BSE")], p)
    assert p.calls == [[inst("TCS", "BSE")]] and r.holdings[0].current_price == 2490.0

async def test_provider_failure_propagates_so_the_agent_can_say_so():
    with pytest.raises(RuntimeError):
        await price_holdings([hold("TCS")], FakeProvider(error=RuntimeError("yahoo down")))


# ---------------------------------------------------------------- provenance: when and from where
async def test_as_of_is_the_oldest_quote_time_used():
    p = FakeProvider([quote("A", 1.0, as_of=T0), quote("B", 1.0, as_of=T0 - timedelta(minutes=20))])
    r = await price_holdings([hold("A"), hold("B")], p)
    assert r.as_of == T0 - timedelta(minutes=20)                   # report the most conservative freshness

async def test_sources_are_listed_once_sorted():
    p = FakeProvider([quote("A", 1.0, source="yfinance"), quote("B", 1.0, source="kite"), quote("C", 1.0, source="kite")])
    r = await price_holdings([hold("A"), hold("B"), hold("C")], p)
    assert r.sources == ["kite", "yfinance"]

async def test_unquoted_symbols_are_reported():
    r = await price_holdings([hold("TCS"), hold("GHOST")], FakeProvider([quote("TCS", 1.0)]))
    assert r.unquoted == ["GHOST"]

async def test_already_priced_holdings_are_not_reported_unquoted():
    r = await price_holdings([hold("TCS", price=5.0)], FakeProvider())
    assert r.unquoted == []


# ---------------------------------------------------------------- inputs are not mutated
async def test_inputs_are_not_mutated():
    original = hold("TCS")
    r = await price_holdings([original], FakeProvider([quote("TCS", 2500.0)]))
    assert original.current_price is None and r.holdings[0] is not original


# ---------------------------------------------------------------- end to end with the real sample source
async def test_sample_portfolio_prices_and_produces_metrics():
    hs = await SampleSource().holdings()
    p = FakeProvider([quote(h.instrument.symbol, 100.0) for h in hs])
    r = await price_holdings(hs, p)
    m = compute_portfolio_metrics(r.holdings)
    assert m.unpriced == [] and len(m.holdings) == len(hs) and m.total_value > 0
    assert len(p.calls) == 1

async def test_partially_priced_portfolio_still_produces_metrics_and_lists_the_gap():
    hs = [hold("TCS", 10), hold("GHOST", 5)]
    r = await price_holdings(hs, FakeProvider([quote("TCS", 2500.0)]))
    m = compute_portfolio_metrics(r.holdings)
    assert m.unpriced == ["GHOST"] and m.total_value == 25000.0
