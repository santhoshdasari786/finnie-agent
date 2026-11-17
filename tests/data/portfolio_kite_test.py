"""KiteSource with a FAKE MCP client (no network, no login, no real account).

Run:  .venv/bin/python -m pytest tests/data/portfolio_kite_test.py -v

Verified against the live Kite MCP server (scripts/kite_tools.py, scripts/kite_shape.py):
  * the endpoint speaks OAuth: connecting starts an authorization; the user opens a link, logs in to Zerodha,
    approves, and the connection completes. There is NO separate `login` tool any more.
  * tools are grouped: session(mode=status|logout), portfolio(mode=holdings|profile|margins|positions),
    mutual_funds(mode=holdings), orders / gtt / alerts (can place, modify, delete!)
  * session status -> {authenticated, kite_session_expired, terminated, ...}
  * portfolio holdings -> {data: [rows], pagination: {from, limit, total, has_more, returned}}

Rules pinned here:
  * connect() starts the connection IN THE BACKGROUND, captures the authorization link and returns it (needs_login)
  * the SAME command, run again after approval, finds the connection finished -> connected
  * ONE login per session: the connection is kept until close() (== 'disconnect'); connect() again just re-checks
  * if the session expires, connect() drops the dead connection and asks for a fresh login
  * READ-ONLY by (tool, mode): only session/status, portfolio/holdings, mutual_funds/holdings can ever be called
  * every call times out; holdings are fetched page by page
UNVERIFIED (your account has no funds): the keys of a mutual-fund row (assumed: tradingsymbol, fund, quantity,
average_price, last_price).
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from src.data.market.models import Instrument
from src.data.portfolio import base
from src.data.portfolio.base import SessionExpired
from src.data.portfolio.kite import ALLOWED_CALLS, KiteSource

pytestmark = pytest.mark.asyncio

OAUTH_URL = "https://mcp.kite.trade/authorize?response_type=code&client_id=dcr1.abc&state=xyz"

EQUITY = [
    {"tradingsymbol": "RELIANCE", "exchange": "NSE", "quantity": 10, "t1_quantity": 0,
     "average_price": 2400.0, "last_price": 1320.0},
    {"tradingsymbol": "TCS", "exchange": "BSE", "quantity": 4, "t1_quantity": 1,
     "average_price": 3300.0, "last_price": 2500.0},
]
MF = [
    {"tradingsymbol": "INF846K01DP8", "fund": "Axis Bluechip Fund - Direct Plan", "quantity": 50.5,
     "average_price": 40.0, "last_price": 55.25},
    {"tradingsymbol": "INF200K01RJ1", "fund": "SBI Liquid Fund - Direct Plan", "quantity": 10.0,
     "average_price": 3000.0, "last_price": 3100.0},
]


def reply(obj, style="text"):
    """The three ways an MCP result can carry a payload: JSON text, structured_content, or a parsed .data."""
    if style == "structured":
        return SimpleNamespace(data=object(), content=[], structured_content=obj)
    if style == "data":
        return SimpleNamespace(data=obj, content=[], structured_content=None)
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return SimpleNamespace(data=None, content=[SimpleNamespace(text=text)], structured_content=None)


class FakeMCP:
    """Stands in for fastmcp.Client(URL, auth=OAuth...).

    Entering the client IS the OAuth step: unless `preauthorized`, it reports the authorization link through
    `on_link` and then waits until the test calls approve() (the user clicking 'approve' in the browser).
    `session_ok` is the Kite session behind it (flip to False = it expired).
    """

    def __init__(self, on_link, *, preauthorized=False, session_ok=True, equity=EQUITY, mf=MF, hang=False,
                 enter_error=None, stall_enter=False, expired_as="status", page_cap=500, always_more=False,
                 bare_list=False, style="text", status_extra=None):
        self.on_link, self.preauthorized, self.session_ok = on_link, preauthorized, session_ok
        self.equity, self.mf, self.hang = equity, mf, hang
        self.enter_error, self.stall_enter, self.expired_as = enter_error, stall_enter, expired_as
        self.page_cap, self.always_more, self.bare_list, self.style = page_cap, always_more, bare_list, style
        self.status_extra = status_extra or {}
        self.approved = asyncio.Event()
        self.entered = self.exited = 0
        self.calls: list[tuple[str, str | None]] = []      # (tool, mode)
        self.requests: list[tuple[str, dict]] = []         # (tool, full arguments)

    def approve(self):
        self.approved.set()

    async def __aenter__(self):
        if self.stall_enter:
            await asyncio.sleep(10)
        if self.enter_error:
            raise self.enter_error
        if not self.preauthorized:
            self.on_link(OAUTH_URL)
            await self.approved.wait()
        self.entered += 1
        return self

    async def __aexit__(self, *exc):
        self.exited += 1

    def _status(self):
        ok = self.session_ok
        return {"authenticated": ok, "kite_session_expired": not ok, "terminated": False, "refresh_available": False,
                "status": "active" if ok else "expired", "session_id": "s-1", "created_at": "2026-11-12T04:00:00Z",
                "expires_at": "2026-11-13T00:30:00Z", "kite_session_expires_at": "2026-11-13T00:30:00Z",
                **self.status_extra}

    async def call_tool(self, name, arguments=None, **kw):
        args = dict(arguments or {})
        mode = args.get("mode")
        self.calls.append((name, mode))
        self.requests.append((name, args))
        if self.hang:
            await asyncio.sleep(10)
        if not self.session_ok and self.expired_as == "raise":
            raise RuntimeError("Session expired or invalid. Please log in again.")
        if not self.session_ok and self.expired_as == "text":
            return reply("Session expired. Please log in again.")
        if (name, mode) == ("session", "status"):
            return reply(self._status(), self.style)
        if not self.session_ok:                                # status-style expiry: data calls fail
            raise RuntimeError("Kite session expired")
        if (name, mode) == ("portfolio", "holdings"):
            start, limit = args.get("from", 0), min(args.get("limit", 100), self.page_cap)
            rows = self.equity if self.always_more else self.equity[start:start + limit]
            if self.bare_list:
                return reply(rows, self.style)
            more = True if self.always_more else start + len(rows) < len(self.equity)
            return reply({"data": rows, "pagination": {"from": start, "limit": limit, "total": len(self.equity),
                                                       "has_more": more, "returned": len(rows)}}, self.style)
        if (name, mode) == ("mutual_funds", "holdings"):
            return reply({"data": self.mf}, self.style)
        raise AssertionError(f"unexpected call {name}/{mode}")


class Box:
    """Collects every client the factory builds (a reconnect builds a new one).

    `override` changes how clients built AFTER the first one behave, e.g. {"preauthorized": False} = 'the next
    connection needs a fresh OAuth approval'.
    """
    def __init__(self):
        self.clients: list[FakeMCP] = []
        self.override: dict = {}

    @property
    def client(self) -> FakeMCP:
        return self.clients[-1]


def make(timeout=5, **kw):
    box = Box()
    def factory(on_link):
        c = FakeMCP(on_link, **{**kw, **(box.override if box.clients else {})})
        box.clients.append(c)
        return c
    return KiteSource(client_factory=factory, timeout=timeout), box


async def ready(**kw):
    """A source that is connected and holds a live client (already-authorised path)."""
    src, box = make(preauthorized=True, **kw)
    assert (await src.connect()).connected
    return src, box


# ---------------------------------------------------------------- registry and the read-only guard
async def test_registered_as_kite_with_a_zerodha_label():
    assert base.SOURCES["kite"] is KiteSource and "zerodha" in KiteSource.label.lower()

async def test_exactly_three_read_calls_are_allowed():
    assert ALLOWED_CALLS == {("session", "status"), ("portfolio", "holdings"), ("mutual_funds", "holdings")}

@pytest.mark.parametrize("tool, mode", [
    ("orders", "place"), ("orders", "modify"), ("orders", "cancel"), ("orders", "list"), ("orders", "approval_status"),
    ("gtt", "place"), ("gtt", "modify"), ("gtt", "delete"), ("gtt", "list"),
    ("alerts", "create"), ("alerts", "modify"), ("alerts", "delete"), ("alerts", "get"),
    ("session", "logout"),                                    # would end the session for every client
    ("portfolio", "profile"), ("portfolio", "positions"), ("portfolio", "margins"),
    ("market", "quote"), ("help", None), ("made_up_tool", "x"),
])
async def test_anything_outside_the_three_reads_never_reaches_the_client(tool, mode):
    src, box = await ready()
    box.client.calls.clear()
    with pytest.raises(PermissionError):
        await src._call(tool, mode)
    assert box.client.calls == []

async def test_a_full_session_only_makes_allowlisted_calls():
    src, box = await ready()
    await src.connect()
    await src.holdings()
    assert set(box.client.calls) <= ALLOWED_CALLS


# ---------------------------------------------------------------- the OAuth login flow
async def test_first_connect_returns_the_authorization_link():
    src, box = make()
    info = await src.connect()
    assert not info.connected and info.login_url == OAUTH_URL
    assert "connect kite" in info.message.lower() and len(box.clients) == 1

async def test_asking_again_before_approval_returns_the_same_link_without_a_second_login():
    src, box = make()
    first = await src.connect()
    again = await src.connect()
    assert again.login_url == first.login_url and not again.connected
    assert len(box.clients) == 1                                # still the SAME pending login

async def test_same_command_finishes_the_connection_after_approval():
    src, box = make()
    await src.connect()
    box.client.approve()                                        # the user clicked 'approve' in the browser
    await asyncio.sleep(0.01)
    info = await src.connect()
    assert info.connected and info.login_url is None
    assert len(box.clients) == 1 and box.client.entered == 1    # ONE connection carried the whole login

async def test_an_already_authorised_connection_needs_no_link():
    src, box = make(preauthorized=True)
    info = await src.connect()
    assert info.connected and info.login_url is None

async def test_one_login_per_session_connect_again_just_rechecks():
    src, box = await ready()
    for _ in range(3):
        assert (await src.connect()).connected
    assert len(box.clients) == 1 and box.client.entered == 1 and box.client.exited == 0

async def test_holdings_keep_working_without_asking_again():
    src, box = await ready()
    await src.connect()
    assert len(await src.holdings()) == 4 and len(box.clients) == 1

async def test_oauth_done_but_kite_says_the_session_is_not_active_starts_over():
    src, box = make(preauthorized=True, session_ok=False)
    info = await src.connect()
    assert not info.connected and "connect kite" in info.message.lower()
    assert box.client.exited == 1                                # the useless connection was closed, not kept


# ---------------------------------------------------------------- expiry: ask again
async def test_expired_session_drops_the_dead_connection_and_asks_for_a_fresh_login():
    src, box = await ready()
    box.override = {"preauthorized": False}                     # the next connection needs a fresh approval
    box.client.session_ok = False                               # the Kite session expired
    info = await src.connect()
    assert box.clients[0].exited == 1                           # the dead connection was closed, not leaked
    assert not info.connected and info.login_url == OAUTH_URL and len(box.clients) == 2

async def test_after_an_expiry_the_fresh_login_completes_with_the_same_command():
    src, box = await ready()
    box.override = {"preauthorized": False}
    box.clients[0].session_ok = False
    await src.connect()
    box.client.approve()
    await asyncio.sleep(0.01)
    assert (await src.connect()).connected

@pytest.mark.parametrize("expired_as", ["raise", "text"])
async def test_other_forms_of_expiry_are_detected_too(expired_as):
    src, box = await ready(expired_as=expired_as)
    box.override = {"preauthorized": False}
    box.client.session_ok = False
    assert not (await src.connect()).connected

@pytest.mark.parametrize("extra", [{"authenticated": False}, {"kite_session_expired": True}, {"terminated": True}])
async def test_any_one_bad_status_flag_means_not_logged_in(extra):
    src, box = await ready()
    box.client.status_extra = extra
    assert await src.status() == "needs_login"

async def test_status_flags_are_read_not_word_matched():
    # words like 'expired' or 'login' inside perfectly healthy data must not log the user out
    src, box = await ready(status_extra={"status": "active (login refreshed, nothing expired)", "session_id": "login-expired-1"})
    assert (await src.connect()).connected

async def test_holdings_after_the_session_expires_raises_session_expired():
    src, box = await ready()
    box.client.session_ok = False
    with pytest.raises(SessionExpired) as e:
        await src.holdings()
    assert e.value.source == "kite"

async def test_holdings_before_any_connection_raises_session_expired():
    src, box = make(preauthorized=True)
    with pytest.raises(SessionExpired):
        await src.holdings()
    assert box.clients == []

async def test_holdings_while_a_login_is_pending_raises_session_expired():
    src, box = make()
    await src.connect()
    with pytest.raises(SessionExpired):
        await src.holdings()

async def test_other_failures_are_not_mistaken_for_expiry():
    src, box = await ready()
    async def boom(name, arguments=None, **kw):
        raise ConnectionError("network down")
    box.client.call_tool = boom
    with pytest.raises(ConnectionError):
        await src.holdings()

async def test_holdings_calls_time_out():
    src, box = await ready(timeout=0.05)
    box.client.hang = True
    with pytest.raises(asyncio.TimeoutError):
        await src.holdings()


# ---------------------------------------------------------------- failed attempts recover
async def test_a_failed_login_attempt_is_replaced_by_a_new_one_next_time():
    src, box = make(enter_error=TimeoutError("oauth callback timed out"))
    info = await src.connect()
    assert not info.connected and info.login_url is None
    assert (await src.connect()).login_url is None and len(box.clients) == 2      # tried again, did not stay stuck

async def test_a_server_that_never_answers_fails_fast_instead_of_hanging():
    src, box = make(stall_enter=True, timeout=0.05)
    info = await asyncio.wait_for(src.connect(), timeout=2)
    assert not info.connected and "respond" in info.message.lower()

async def test_a_timed_out_attempt_is_cancelled_so_the_next_try_starts_fresh():
    src, box = make(stall_enter=True, timeout=0.05)
    await src.connect()
    await src.connect()
    assert len(box.clients) == 2                                # did not keep waiting on the dead attempt

async def test_unexpected_connection_errors_propagate():
    src, box = make(enter_error=ConnectionError("dns failure"))
    with pytest.raises(ConnectionError):
        await src.connect()


# ---------------------------------------------------------------- status (never opens a connection)
async def test_status_before_connect_is_needs_login_and_opens_nothing():
    src, box = make()
    assert await src.status() == "needs_login" and box.clients == []

async def test_status_while_a_login_is_pending_is_needs_login():
    src, box = make()
    await src.connect()
    assert await src.status() == "needs_login"

async def test_status_when_connected_and_after_expiry():
    src, box = await ready()
    assert await src.status() == "connected"
    box.client.session_ok = False
    assert await src.status() == "needs_login"


# ---------------------------------------------------------------- holdings mapping
async def test_equity_fields_are_mapped():
    src, _ = await ready()
    hs = {h.instrument.symbol: h for h in await src.holdings() if h.instrument.exchange != "MF"}
    r = hs["RELIANCE"]
    assert (r.instrument, r.quantity, r.avg_price, r.current_price, r.asset_class) == \
           (Instrument(symbol="RELIANCE", exchange="NSE"), 10, 2400.0, 1320.0, "equity")

async def test_exchange_is_kept():
    src, _ = await ready()
    tcs = next(h for h in await src.holdings() if h.instrument.symbol == "TCS")
    assert tcs.instrument.exchange == "BSE"

async def test_t1_quantity_counts_as_owned():
    src, _ = await ready()
    tcs = next(h for h in await src.holdings() if h.instrument.symbol == "TCS")
    assert tcs.quantity == 5                                  # 4 settled + 1 arriving tomorrow

async def test_zero_last_price_becomes_unpriced_so_yfinance_can_fill_it():
    src, _ = await ready(equity=[{**EQUITY[0], "last_price": 0}])
    h = next(h for h in await src.holdings() if h.instrument.symbol == "RELIANCE")
    assert h.current_price is None

async def test_fully_sold_rows_are_dropped():
    src, _ = await ready(equity=[{**EQUITY[0], "quantity": 0, "t1_quantity": 0}])
    assert [h for h in await src.holdings() if h.instrument.exchange != "MF"] == []

async def test_empty_account_gives_no_holdings():
    src, _ = await ready(equity=[], mf=[])
    assert await src.holdings() == []

@pytest.mark.parametrize("style", ["text", "structured", "data"])
async def test_every_way_of_carrying_the_payload_is_understood(style):
    src, _ = await ready(style=style)
    assert {h.instrument.symbol for h in await src.holdings() if h.instrument.exchange != "MF"} == {"RELIANCE", "TCS"}

async def test_a_bare_list_reply_is_accepted_as_one_page():
    src, box = await ready(bare_list=True)
    assert len([h for h in await src.holdings() if h.instrument.exchange != "MF"]) == 2
    assert [c for c in box.client.calls if c == ("portfolio", "holdings")] == [("portfolio", "holdings")]

async def test_mutual_funds_are_mapped_with_nav_as_price():
    src, _ = await ready()
    mfs = {h.instrument.symbol: h for h in await src.holdings() if h.instrument.exchange == "MF"}
    axis = mfs["INF846K01DP8"]
    assert (axis.quantity, axis.avg_price, axis.current_price) == (50.5, 40.0, 55.25)

async def test_fund_class_is_guessed_from_the_name():
    src, _ = await ready()
    mfs = {h.instrument.symbol: h.asset_class for h in await src.holdings() if h.instrument.exchange == "MF"}
    assert mfs == {"INF846K01DP8": "equity_fund", "INF200K01RJ1": "debt_fund"}


# ---------------------------------------------------------------- pagination
async def test_holdings_ask_for_full_detail_in_big_pages():
    src, box = await ready()
    await src.holdings()
    args = next(a for n, a in box.client.requests if n == "portfolio")
    assert args["mode"] == "holdings" and args["type"] == "full" and args["limit"] == 500 and args["from"] == 0

async def test_every_page_is_fetched_until_has_more_is_false():
    many = [{**EQUITY[0], "tradingsymbol": f"S{i}"} for i in range(5)]
    src, box = await ready(equity=many, page_cap=2)           # the server hands out 2 rows at a time
    got = [h for h in await src.holdings() if h.instrument.exchange != "MF"]
    assert [h.instrument.symbol for h in got] == [f"S{i}" for i in range(5)]
    offsets = [a["from"] for n, a in box.client.requests if n == "portfolio"]
    assert offsets == [0, 2, 4]                                # advances by what was actually returned

async def test_it_stops_when_has_more_is_false_even_if_the_page_is_full():
    two = EQUITY[:2]
    src, box = await ready(equity=two, page_cap=2)
    await src.holdings()
    assert len([r for r in box.client.requests if r[0] == "portfolio"]) == 1

async def test_a_server_that_never_stops_paging_is_an_error_not_an_endless_loop():
    src, box = await ready(always_more=True)
    with pytest.raises(RuntimeError, match="pagination"):
        await src.holdings()
    assert len([r for r in box.client.requests if r[0] == "portfolio"]) <= 25


# ---------------------------------------------------------------- lifecycle (== 'disconnect')
async def test_close_exits_the_client_once_and_forgets_the_session():
    src, box = await ready()
    await src.close()
    await src.close()                                         # idempotent
    assert box.client.exited == 1 and await src.status() == "needs_login"

async def test_close_without_connecting_is_a_no_op():
    src, box = make()
    await src.close()
    assert box.clients == []

async def test_close_cancels_a_login_that_was_never_finished():
    src, box = make()
    await src.connect()                                       # pending: waiting for the user to approve
    await src.close()
    await asyncio.sleep(0.01)
    info = await src.connect()                                # a fresh login starts, nothing stale is reused
    assert info.login_url == OAUTH_URL and len(box.clients) == 2

async def test_after_close_a_new_connect_opens_a_fresh_connection():
    src, box = await ready()
    await src.close()
    assert (await src.connect()).connected and len(box.clients) == 2
