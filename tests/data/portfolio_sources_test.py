"""PortfolioSource registry, the bundled `sample` source, and the per-thread ConnectionStore. No network.

Run:  .venv/bin/python -m pytest tests/data/portfolio_sources_test.py -v
Why a store: connecting is a multi-turn conversation. The store remembers, PER THREAD, which sources are
connected, and keeps ONE instance per (thread, source): a Kite login is bound to the session that made it.
"""
import pytest

from src.data.market.models import Instrument
from src.data.portfolio import base
from src.data.portfolio.base import ConnectInfo
from src.data.portfolio.models import Holding
from src.data.portfolio.sample import SampleSource
from src.data.portfolio.store import ConnectionStore

pytestmark = pytest.mark.asyncio


def holding(symbol, qty=1):
    return Holding(instrument=Instrument(symbol=symbol), quantity=qty)


class FakeSource:
    """A source that needs a login first. `logged_in` flips when the 'user' finishes logging in."""
    name = "fake"
    label = "Fake broker (needs login)"
    instances = 0

    def __init__(self):
        FakeSource.instances += 1
        self.logged_in = False
        self.connect_calls = 0

    async def status(self):
        return "connected" if self.logged_in else "needs_login"

    async def connect(self, **params):
        self.connect_calls += 1
        if self.logged_in:
            return ConnectInfo(connected=True, message="Connected.")
        return ConnectInfo(connected=False, message="Log in, then say 'connect fake' again.",
                           login_url="https://fake.example/login")

    async def holdings(self):
        return [holding("FAKE1", 3)]


class OtherSource:
    name = "other"
    label = "Other"

    async def status(self):
        return "available"

    async def connect(self, **params):
        return ConnectInfo(connected=True, message="ok")

    async def holdings(self):
        return [holding("OTHER1", 7)]


@pytest.fixture
def store():
    FakeSource.instances = 0
    return ConnectionStore({"sample": SampleSource, "fake": FakeSource, "other": OtherSource})


# ---------------------------------------------------------------- ConnectInfo
async def test_connected_info_needs_no_url():
    assert ConnectInfo(connected=True, message="ok").login_url is None

async def test_not_connected_without_a_url_is_allowed_for_non_login_failures():
    assert ConnectInfo(connected=False, message="paste your CSV").login_url is None


# ---------------------------------------------------------------- registry
async def test_sample_is_registered_by_name():
    assert base.SOURCES["sample"] is SampleSource

async def test_duplicate_source_name_is_rejected(monkeypatch):
    monkeypatch.setattr(base, "SOURCES", {"x": object})
    with pytest.raises(ValueError, match="already registered"):
        base.register_source("x")(type("Dup", (), {}))

async def test_a_new_source_can_be_attached_by_name(monkeypatch):
    monkeypatch.setattr(base, "SOURCES", {})
    @base.register_source("later")
    class Later:
        name, label = "later", "Later"
    assert base.SOURCES["later"] is Later


# ---------------------------------------------------------------- the sample source
async def test_sample_needs_no_login():
    s = SampleSource()
    assert await s.status() == "available"
    info = await s.connect()
    assert info.connected and info.login_url is None

async def test_sample_holdings_are_unpriced_and_classified():
    hs = await SampleSource().holdings()
    assert len(hs) >= 5
    assert all(h.current_price is None for h in hs)            # prices come from the market-data layer
    assert all(h.asset_class for h in hs) and all(h.quantity > 0 for h in hs)

async def test_sample_covers_several_asset_classes():
    classes = {h.asset_class for h in await SampleSource().holdings()}
    assert {"equity", "gold"} <= classes and len(classes) >= 3

async def test_sample_symbols_are_unique():
    symbols = [h.instrument.symbol for h in await SampleSource().holdings()]
    assert len(symbols) == len(set(symbols))

async def test_sample_returns_fresh_objects_each_call():
    a, b = await SampleSource().holdings(), await SampleSource().holdings()
    a[0].current_price = 1.0
    assert b[0].current_price is None


# ---------------------------------------------------------------- the menu
async def test_options_lists_every_source_with_its_label(store):
    assert dict(store.options()) == {"sample": SampleSource.label, "fake": "Fake broker (needs login)", "other": "Other"}

async def test_sample_has_a_human_label():
    assert SampleSource.label and "sample" in SampleSource.label.lower()


# ---------------------------------------------------------------- connecting
async def test_connect_sample_marks_the_thread_connected(store):
    info = await store.connect("t1", "sample")
    assert info.connected and store.connected("t1") == ["sample"]

async def test_nothing_is_connected_at_first(store):
    assert store.connected("t1") == []

async def test_unknown_source_is_rejected(store):
    with pytest.raises(ValueError, match="unknown"):
        await store.connect("t1", "nope")

async def test_login_source_is_not_connected_until_the_login_is_done(store):
    info = await store.connect("t1", "fake")
    assert not info.connected and info.login_url.startswith("https://")
    assert store.connected("t1") == []

async def test_connecting_again_after_login_completes_the_connection(store):
    await store.connect("t1", "fake")
    store._instances[("t1", "fake")].logged_in = True          # the user finished logging in
    info = await store.connect("t1", "fake")
    assert info.connected and store.connected("t1") == ["fake"]

async def test_one_instance_per_thread_and_source(store):
    await store.connect("t1", "fake")
    await store.connect("t1", "fake")
    assert FakeSource.instances == 1                            # the login session must be reused

async def test_threads_are_isolated(store):
    await store.connect("t1", "sample")
    assert store.connected("t2") == []
    await store.connect("t2", "fake")
    assert FakeSource.instances == 1 and store.connected("t1") == ["sample"]

async def test_two_threads_get_separate_instances_of_the_same_source(store):
    await store.connect("t1", "fake")
    await store.connect("t2", "fake")
    assert FakeSource.instances == 2

async def test_connected_names_keep_connection_order(store):
    await store.connect("t1", "other")
    await store.connect("t1", "sample")
    assert store.connected("t1") == ["other", "sample"]

async def test_connecting_the_same_source_twice_lists_it_once(store):
    await store.connect("t1", "sample")
    await store.connect("t1", "sample")
    assert store.connected("t1") == ["sample"]


# ---------------------------------------------------------------- holdings
async def test_holdings_with_nothing_connected_is_empty(store):
    assert await store.holdings("t1") == []

async def test_holdings_come_from_connected_sources_only(store):
    await store.connect("t1", "other")
    await store.connect("t1", "fake")                           # pending login: must NOT contribute
    assert [h.instrument.symbol for h in await store.holdings("t1")] == ["OTHER1"]

async def test_holdings_are_gathered_across_connected_sources(store):
    await store.connect("t1", "other")
    await store.connect("t1", "sample")
    symbols = {h.instrument.symbol for h in await store.holdings("t1")}
    assert "OTHER1" in symbols and len(symbols) > 1

async def test_a_failing_source_propagates_so_the_agent_can_report_it(store):
    await store.connect("t1", "other")
    store._instances[("t1", "other")].holdings = _boom
    with pytest.raises(RuntimeError):
        await store.holdings("t1")

async def _boom():
    raise RuntimeError("source down")


# ---------------------------------------------------------------- disconnecting
async def test_disconnect_removes_only_that_source(store):
    await store.connect("t1", "other")
    await store.connect("t1", "sample")
    store.disconnect("t1", "other")
    assert store.connected("t1") == ["sample"]

async def test_disconnect_forgets_the_instance_so_a_fresh_login_starts_clean(store):
    await store.connect("t1", "fake")
    store.disconnect("t1", "fake")
    await store.connect("t1", "fake")
    assert FakeSource.instances == 2

async def test_disconnecting_something_not_connected_is_a_no_op(store):
    store.disconnect("t1", "sample")
    assert store.connected("t1") == []

async def test_default_store_uses_the_global_registry():
    assert dict(ConnectionStore().options())["sample"] == SampleSource.label


# ---------------------------------------------------------------- lifecycle: closing sources (needed for live connections)
class ClosableSource(OtherSource):
    name, label = "closable", "Closable"
    instances: list = []

    def __init__(self):
        self.closed = 0
        ClosableSource.instances.append(self)

    async def close(self):
        self.closed += 1


class FailingClose(ClosableSource):
    name, label = "failing", "Failing close"

    async def close(self):
        raise RuntimeError("close blew up")


@pytest.fixture
def cstore():
    ClosableSource.instances = []
    return ConnectionStore({"closable": ClosableSource, "failing": FailingClose, "other": OtherSource})

async def test_disconnect_returns_the_removed_instance_so_the_caller_can_close_it(cstore):
    await cstore.connect("t1", "closable")
    inst = cstore.disconnect("t1", "closable")
    assert inst is ClosableSource.instances[0]

async def test_disconnect_of_something_never_connected_returns_none(cstore):
    assert cstore.disconnect("t1", "closable") is None

async def test_close_all_closes_every_instance_and_forgets_everything(cstore):
    await cstore.connect("t1", "closable")
    await cstore.connect("t2", "closable")
    await cstore.connect("t1", "other")                       # no close() method: must be tolerated
    await cstore.close_all()
    assert [i.closed for i in ClosableSource.instances] == [1, 1]
    assert cstore.connected("t1") == [] and cstore.connected("t2") == []

async def test_close_all_keeps_going_when_one_close_fails(cstore):
    await cstore.connect("t1", "failing")
    await cstore.connect("t1", "closable")
    await cstore.close_all()                                  # must not raise
    assert ClosableSource.instances[-1].closed == 1

async def test_a_failed_reconnect_removes_the_stale_connection(store):
    await store.connect("t1", "fake")
    store._instances[("t1", "fake")].logged_in = True
    await store.connect("t1", "fake")
    assert store.connected("t1") == ["fake"]
    store._instances[("t1", "fake")].logged_in = False        # the session expired
    info = await store.connect("t1", "fake")
    assert not info.connected and store.connected("t1") == []

async def test_opened_lists_sources_with_a_live_instance_including_pending_logins(store):
    await store.connect("t1", "sample")
    await store.connect("t1", "fake")                         # login still pending: NOT connected, but a connection is open
    await store.connect("t2", "other")
    assert store.connected("t1") == ["sample"]
    assert store.opened("t1") == ["sample", "fake"] and store.opened("t2") == ["other"]

async def test_opened_forgets_a_disconnected_source(store):
    await store.connect("t1", "fake")
    store.disconnect("t1", "fake")
    assert store.opened("t1") == []

async def test_session_expired_error_carries_the_source_name():
    from src.data.portfolio.base import SessionExpired
    e = SessionExpired("kite")
    assert e.source == "kite" and isinstance(e, Exception) and "kite" in str(e)

async def test_instrument_accepts_the_mutual_fund_exchange():
    assert Instrument(symbol="INF846K01DP8", exchange="MF").exchange == "MF"
