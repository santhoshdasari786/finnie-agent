import asyncio
import json
import logging

from fastmcp import Client
from fastmcp.client.auth import OAuth

from src.data.market.models import Instrument
from src.data.portfolio.base import ConnectInfo, SessionExpired, SourceStatus, register_source
from src.data.portfolio.models import Holding

log = logging.getLogger(__name__)

KITE_MCP_URL = "https://mcp.kite.trade/mcp"
# READ-ONLY by construction: the only three (tool, mode) calls this app can ever make. Kite's `orders`, `gtt` and
# `alerts` tools can place/modify/delete, and `session` has mode=logout, so a list of tool NAMES would not be enough.
ALLOWED_CALLS = frozenset({("session", "status"), ("portfolio", "holdings"), ("mutual_funds", "holdings")})

PAGE_SIZE = 500            # Kite's maximum page
MAX_PAGES = 20             # a server that never stops paging is an error, not an endless loop

_EXPIRED_WORDS = ("session", "log in", "login", "authenticat", "expired", "unauthor", "401", "invalid token", "bearer")
_DEBT_WORDS = ("liquid", "debt", "bond", "gilt", "overnight", "money market", "short duration", "credit risk", "psu")

_LOGIN_MESSAGE = "Open the link, log in to Zerodha and approve access, then say 'connect kite' again."
_NO_RESPONSE = "Kite didn't respond in time. Say 'connect kite' to try again."
_NOT_ACTIVE = "Kite says the session isn't active. Say 'connect kite' to log in again."


class _LinkOAuth(OAuth):
    """The normal fastmcp OAuth flow, but the authorization link goes to `on_link` instead of a browser."""

    def __init__(self, on_link, **kw):
        self._on_link = on_link
        super().__init__(**kw)

    async def redirect_handler(self, authorization_url: str) -> None:
        self._on_link(authorization_url)


def _default_client(on_link):
    return Client(KITE_MCP_URL, auth=_LinkOAuth(on_link, client_name="Finnie capstone (read-only)"))


def _payload(result):
    """A tool result as plain data: structured_content -> JSON text -> .data (if dict/list) -> the raw text."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, (dict, list)):
        return structured
    text = "".join(getattr(c, "text", "") for c in (getattr(result, "content", None) or []))
    try:
        return json.loads(text)
    except ValueError:
        pass
    data = getattr(result, "data", None)
    return data if isinstance(data, (dict, list)) else text


def _expired(text: str) -> bool:
    """Free text that reads like 'please log in again'. Only used on errors and plain-text replies, never on data."""
    low = text.lower()
    return any(w in low for w in _EXPIRED_WORDS)


def _page(result, source: str) -> tuple[list[dict], bool]:
    """(rows, has_more) from a paged reply: {data: [...], pagination: {has_more}} or a bare list."""
    payload = _payload(result)
    if isinstance(payload, str):
        if _expired(payload):
            raise SessionExpired(source)
        raise ValueError("unexpected reply from Kite")
    if isinstance(payload, list):
        rows, pagination = payload, {}
    else:
        rows, pagination = payload.get("data") or payload.get("holdings") or [], payload.get("pagination") or {}
    rows = [r for r in rows if isinstance(r, dict)]
    return rows, bool(pagination["has_more"]) if "has_more" in pagination else len(rows) >= PAGE_SIZE


@register_source("kite")
class KiteSource:
    name = "kite"
    label = "Zerodha Kite (live account, read-only, needs login)"

    def __init__(self, client_factory=None, timeout: float = 30.0):
        self._factory = client_factory or _default_client
        self._timeout = timeout
        self._client = None                  # the live connection: ONE per source, kept until close()
        self._task: asyncio.Task | None = None       # a login in progress (waiting for the user to approve)
        self._link: str | None = None
        self._link_ready = asyncio.Event()

    # ---------------------------------------------------------------- low level
    async def _call(self, tool: str, mode: str | None, **args):
        if (tool, mode) not in ALLOWED_CALLS:
            raise PermissionError(f"{tool}/{mode} is not allowed: this source is read-only")
        if self._client is None:
            raise SessionExpired(self.name)
        return await asyncio.wait_for(self._client.call_tool(tool, {"mode": mode, **args}), self._timeout)

    async def _logged_in(self) -> bool:
        try:
            result = await self._call("session", "status")
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            if _expired(str(e)):
                return False
            raise
        status = _payload(result)
        if isinstance(status, dict):
            return bool(status.get("authenticated")) and not status.get("kite_session_expired") and not status.get("terminated")
        return not _expired(status)

        # ---------------------------------------------------------------- login attempt (background)
    def _on_link(self, url: str) -> None:
        self._link = url
        self._link_ready.set()

    async def _establish(self, client) -> None:
        await client.__aenter__()            # for OAuth this returns only after the user has approved
        self._client = client

    def _start_attempt(self) -> None:
        self._link = None
        self._link_ready = asyncio.Event()
        self._task = asyncio.create_task(self._establish(self._factory(self._on_link)))

    async def _cancel_attempt(self) -> None:
        task, self._task = self._task, None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except BaseException:
                pass

    def _reap(self) -> ConnectInfo | None:
        """Collect a finished attempt. Returns a ConnectInfo only if it FAILED (and re-raises unexpected errors)."""
        if self._task is None or not self._task.done():
            return None
        task, self._task = self._task, None
        error = None if task.cancelled() else task.exception()
        if error is None:
            return None
        if isinstance(error, TimeoutError):
            return ConnectInfo(connected=False, message="The Kite login timed out. Say 'connect kite' to start again.")
        raise error

        # ---------------------------------------------------------------- public API
    async def status(self) -> SourceStatus:
        if self._client is None:
            return "needs_login"
        try:
            return "connected" if await self._logged_in() else "needs_login"
        except Exception:
            return "needs_login"

    async def connect(self, **params) -> ConnectInfo:
        failed = self._reap()
        if failed:
            return failed
        try:
            if self._client is not None:
                if await self._logged_in():
                    return ConnectInfo(connected=True, message="Connected to Zerodha Kite (read-only).")
                await self.close()                            # an expired session: drop it and log in afresh
            if self._task is None:
                self._start_attempt()
            return await self._wait_for_login_step()
        except asyncio.TimeoutError:
            return ConnectInfo(connected=False, message=_NO_RESPONSE)

    async def _wait_for_login_step(self) -> ConnectInfo:
        link = asyncio.ensure_future(self._link_ready.wait())
        try:
            done, _ = await asyncio.wait({self._task, link}, timeout=self._timeout, return_when=asyncio.FIRST_COMPLETED)
        finally:
            link.cancel()
        if not done:                                          # nothing happened: do not leave a stuck attempt behind
            await self._cancel_attempt()
            return ConnectInfo(connected=False, message=_NO_RESPONSE)
        if self._task is not None and self._task in done:     # connected without needing a link (token still valid)
            failed = self._reap()
            if failed:
                return failed
            if await self._logged_in():
                return ConnectInfo(connected=True, message="Connected to Zerodha Kite (read-only).")
            await self.close()                                # OAuth worked but Kite's session is not active
            return ConnectInfo(connected=False, message=_NOT_ACTIVE)
        return ConnectInfo(connected=False, login_url=self._link, message=_LOGIN_MESSAGE)


    async def holdings(self) -> list[Holding]:
        if self._client is None:
            raise SessionExpired(self.name)
        try:
            equity = await self._all_pages()
            funds = _page(await self._call("mutual_funds", "holdings"), self.name)[0]
        except asyncio.TimeoutError:
            raise
        except SessionExpired:
            raise
        except Exception as e:
            if _expired(str(e)):
                raise SessionExpired(self.name) from e
            raise
        return [h for h in (*map(self._equity, equity), *map(self._fund, funds)) if h]

    async def _all_pages(self) -> list[dict]:
        rows: list[dict] = []
        for _ in range(MAX_PAGES):
            page, more = _page(await self._call("portfolio", "holdings", type="full", limit=PAGE_SIZE, **{"from": len(rows)}),
                               self.name)
            rows += page
            if not more or not page:
                return rows
        raise RuntimeError("holdings pagination did not finish")

    @staticmethod
    def _equity(row: dict) -> Holding | None:
        qty = (row.get("quantity") or 0) + (row.get("t1_quantity") or 0)       # settled + arriving tomorrow
        if qty <= 0:
            return None
        exchange = row.get("exchange") if row.get("exchange") in ("NSE", "BSE") else "NSE"
        return Holding(instrument=Instrument(symbol=row["tradingsymbol"], exchange=exchange), quantity=qty,
                       avg_price=row.get("average_price") or None, current_price=row.get("last_price") or None,
                       asset_class="equity")

    @staticmethod
    def _fund(row: dict) -> Holding | None:
        qty = row.get("quantity") or 0
        if qty <= 0:
            return None
        name = (row.get("fund") or "").lower()
        return Holding(instrument=Instrument(symbol=row["tradingsymbol"], exchange="MF"), quantity=qty,
                       avg_price=row.get("average_price") or None, current_price=row.get("last_price") or None,
                       asset_class="debt_fund" if any(w in name for w in _DEBT_WORDS) else "equity_fund")

    async def close(self) -> None:
        await self._cancel_attempt()
        self._link = None
        if self._client is not None:
            client, self._client = self._client, None
            await client.__aexit__(None, None, None)
