"""GET /market/history?symbol=TCS&range=3m : the price series behind the Market tab's chart.

Run:  .venv/bin/python -m pytest tests/api/market_history_api_test.py -v
No network: the market provider is a fake that records what it was asked.

Contract
  200  {symbol, name, range, currency, source, as_of, points:[{date, close}], latest, change_pct, high, low}
  422  a symbol we cannot resolve (or a bad range): the request is malformed
  404  the provider has no usable data (unknown ticker, fewer than 2 points)
  502  the provider failed: {"error": "<generic message>"}, never the cause
  503  this server has no market provider with history
  * it never touches the graph, the memory or a thread lock
"""
from datetime import date, datetime, timezone

import pytest
from starlette.testclient import TestClient

from src.api.app import create_app
from src.data.market.models import Instrument, PriceHistory, PricePoint
from tests.api.chat_api_test import make_runtime
from tests.conftest import StubAgent
from src.workflow.state import AGENT_NAMES


def make_history(instrument, rng, closes=(100.0, 110.0, 105.0)):
    return PriceHistory(
        instrument=instrument, range=rng, currency="INR", source="yfinance",
        as_of=datetime(2026, 11, 17, 5, 30, tzinfo=timezone.utc),
        points=[PricePoint(date=date(2026, 8, 3 + i), close=c) for i, c in enumerate(closes)])


class FakeProvider:
    name = "fake"

    def __init__(self, result="default", raises=None):
        self.calls: list[tuple] = []
        self.result = result
        self.raises = raises

    async def history(self, instrument, range):
        self.calls.append((instrument, range))
        if self.raises:
            raise self.raises
        return make_history(instrument, range) if self.result == "default" else self.result


class MarketStub(StubAgent):
    def __init__(self, provider):
        super().__init__("market_analysis")
        self.provider = provider


def client_for(provider):
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents["market_analysis"] = MarketStub(provider)
    runtime = make_runtime(agents)
    return TestClient(create_app(runtime=runtime)), runtime


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def client(provider):
    c, _ = client_for(provider)
    with c:
        yield c


# ================================================================ the happy path
def test_the_reply_has_the_documented_fields(client):
    res = client.get("/market/history", params={"symbol": "TCS", "range": "3m"})
    assert res.status_code == 200
    assert set(res.json()) == {"symbol", "name", "range", "currency", "source", "as_of", "points",
                               "latest", "change_pct", "high", "low", "stale", "age_seconds"}


def test_the_numbers_are_computed_in_code(client):
    body = client.get("/market/history", params={"symbol": "TCS"}).json()
    assert body["latest"] == 105.0 and body["high"] == 110.0 and body["low"] == 100.0 and body["change_pct"] == 5.0
    assert body["points"][0] == {"date": "2026-08-03", "close": 100.0}
    assert body["source"] == "yfinance" and body["currency"] == "INR" and body["as_of"].startswith("2026-11-17")


def test_the_reply_says_how_old_the_data_is_and_whether_it_is_fresh(client):
    body = client.get("/market/history", params={"symbol": "TCS"}).json()
    assert body["stale"] is False and isinstance(body["age_seconds"], int) and body["age_seconds"] > 0


def test_stale_data_is_flagged_not_hidden():
    p = FakeProvider()
    p.result = make_history(Instrument(symbol="TCS"), "3m").model_copy(update={"stale": True})
    c, _ = client_for(p)
    with c:
        body = c.get("/market/history", params={"symbol": "TCS"}).json()
    assert body["stale"] is True and body["latest"] == 105.0


def test_an_outage_with_nothing_cached_is_a_retryable_502():
    from src.data.market.base import ProviderUnavailable
    c, _ = client_for(FakeProvider(raises=ProviderUnavailable("rate limited")))
    with c:
        res = c.get("/market/history", params={"symbol": "TCS"})
    assert res.status_code == 502 and "rate limited" not in res.text


def test_the_range_defaults_to_three_months(client, provider):
    client.get("/market/history", params={"symbol": "TCS"})
    assert provider.calls[0][1] == "3m"


@pytest.mark.parametrize("rng", ["1m", "3m", "6m", "1y"])
def test_every_range_is_passed_through(client, provider, rng):
    body = client.get("/market/history", params={"symbol": "TCS", "range": rng}).json()
    assert provider.calls[-1][1] == rng and body["range"] == rng


def test_the_symbol_is_resolved_before_it_reaches_the_provider(client, provider):
    client.get("/market/history", params={"symbol": "tcs"})
    client.get("/market/history", params={"symbol": "nifty"})
    client.get("/market/history", params={"symbol": "^BSESN"})
    assert provider.calls[0][0] == Instrument(symbol="TCS")
    assert provider.calls[1][0] == Instrument(symbol="NIFTY50", exchange="INDEX")
    assert provider.calls[2][0] == Instrument(symbol="SENSEX", exchange="INDEX")


def test_an_index_reply_carries_its_display_name(client):
    body = client.get("/market/history", params={"symbol": "NIFTY50"}).json()
    assert body["symbol"] == "NIFTY50" and body["name"] == "Nifty 50"


# ================================================================ a malformed request is 422
@pytest.mark.parametrize("symbol", ["^GSPC", "TCS.NS", "<script>", "a b", "A" * 21, "", "TCS;DROP"])
def test_a_symbol_we_cannot_resolve_is_422(client, provider, symbol):
    res = client.get("/market/history", params={"symbol": symbol})
    assert res.status_code == 422
    assert provider.calls == []


def test_a_missing_symbol_is_422(client):
    assert client.get("/market/history").status_code == 422


@pytest.mark.parametrize("rng", ["10y", "1d", "", "ALL", "1M "])
def test_a_range_outside_the_four_is_422(client, provider, rng):
    assert client.get("/market/history", params={"symbol": "TCS", "range": rng}).status_code == 422
    assert provider.calls == []


def test_an_unsupported_index_says_which_ones_are_supported(client):
    detail = client.get("/market/history", params={"symbol": "^GSPC"}).json()["detail"]
    assert "Nifty 50" in str(detail) and "Sensex" in str(detail)


# ================================================================ no data, a failure, no provider
def test_no_data_is_404_with_a_message(provider):
    provider.result = None
    c, _ = client_for(provider)
    with c:
        res = c.get("/market/history", params={"symbol": "NOSUCH"})
    assert res.status_code == 404 and res.json() == {"error": "I couldn't find price history for NOSUCH."}


def test_a_single_point_cannot_draw_a_line_so_it_is_404(provider):
    provider.result = make_history(Instrument(symbol="TCS"), "3m", closes=(100.0,))
    c, _ = client_for(provider)
    with c:
        assert c.get("/market/history", params={"symbol": "TCS"}).status_code == 404


def test_a_provider_failure_is_502_without_the_cause():
    p = FakeProvider(raises=RuntimeError("secret internal detail: api key abc123"))
    c, _ = client_for(p)
    with c:
        res = c.get("/market/history", params={"symbol": "TCS"})
    assert res.status_code == 502
    assert res.json() == {"error": "I couldn't load price history right now. Please try again."}
    assert "secret" not in res.text and "abc123" not in res.text


def test_without_a_provider_that_has_history_it_is_503():
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}          # StubAgent has no .provider
    c = TestClient(create_app(runtime=make_runtime(agents)))
    with c:
        assert c.get("/market/history", params={"symbol": "TCS"}).status_code == 503


def test_a_provider_without_a_history_method_is_503():
    class QuotesOnly:
        name = "quotes-only"
    c, _ = client_for(QuotesOnly())
    with c:
        assert c.get("/market/history", params={"symbol": "TCS"}).status_code == 503


# ================================================================ it is not a chat
def test_it_does_not_touch_the_graph_or_memory(provider):
    c, runtime = client_for(provider)
    with c:
        c.get("/market/history", params={"symbol": "TCS"})
    assert all(not a.calls for a in runtime.agents.values() if isinstance(a, StubAgent))


def test_it_is_listed_in_the_openapi_description(client):
    assert "/market/history" in client.get("/openapi.json").json()["paths"]


def test_the_dev_server_origin_may_call_it(client):
    res = client.get("/market/history", params={"symbol": "TCS"}, headers={"Origin": "http://localhost:5173"})
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_the_openapi_description_names_the_reply_fields(client):
    schema = client.get("/openapi.json").json()["components"]["schemas"]["HistoryOut"]
    assert {"symbol", "name", "range", "currency", "source", "as_of", "points", "latest", "change_pct", "high", "low",
            "stale", "age_seconds"} <= set(schema["properties"])
