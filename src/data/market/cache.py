import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from src.core.config import MarketDataCfg
from src.data.market.base import MarketDataProvider, ProviderUnavailable
from src.data.market.models import Instrument, PriceHistory, Quote

log = logging.getLogger(__name__)


@dataclass
class _Entry:
    value: Any
    stored_at: float


class CachedProvider:
    """A TTL cache, retry with backoff and a stale fallback in front of any MarketDataProvider.

    - a quote is cached per instrument, a history per instrument and range, for `ttl` seconds
    - "not found" (None / no quote) is an answer: never cached, never retried
    - ProviderUnavailable (rate limit, network) is retried `retries` times, waiting backoff, 2*backoff, 4*backoff ...
      Any other exception is a bug and passes straight through
    - if every attempt fails and a copy younger than `max_stale` exists, that copy is returned with stale=True
    - after a failed refresh the key cools down for `cooldown` seconds: no attempts, no waiting
    - identical requests in flight at the same time share one fetch
    - at most `max_entries` are kept, least recently used first out
    """

    def __init__(self, inner: MarketDataProvider, *, ttl: float = 1800.0, max_stale: float = 86400.0, max_entries: int = 512,
                 retries: int = 2, backoff: float = 0.5, cooldown: float = 30.0,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep):
        self.name = inner.name
        self._inner = inner
        self._ttl, self._max_stale, self._max_entries = ttl, max_stale, max_entries
        self._retries, self._backoff, self._cooldown = retries, backoff, cooldown
        self._clock, self._sleep = clock, sleep
        self._entries: OrderedDict[tuple, _Entry] = OrderedDict()
        self._inflight: dict[tuple, asyncio.Future] = {}
        self._cooling_until: dict[tuple, float] = {}
        self._counts = {"hits": 0, "misses": 0, "retries": 0, "stale_served": 0}

    # ------------------------------------------------------------------ the provider interface
    async def quotes(self, instruments: list[Instrument]) -> list[Quote]:
        wanted = list(dict.fromkeys(instruments))                       # unique, in the order asked
        outcomes = await asyncio.gather(*(self._get(("q", i), self._quote_fetcher(i)) for i in wanted), return_exceptions=True)
        for o in outcomes:
            if isinstance(o, BaseException) and not isinstance(o, ProviderUnavailable):
                raise o                                                 # a bug, not an outage
        found = [o for o in outcomes if isinstance(o, Quote)]
        down = [o for o in outcomes if isinstance(o, ProviderUnavailable)]
        if down and not found:
            raise down[0]                                               # never hide an outage behind "not found"
        return found

    async def history(self, instrument: Instrument, range: str) -> PriceHistory | None:
        return await self._get(("h", instrument, range), lambda: self._inner.history(instrument, range))

    # ------------------------------------------------------------------ bookkeeping
    def stats(self) -> dict:
        return {**self._counts, "entries": len(self._entries)}

    def clear(self) -> None:
        self._entries.clear()
        self._cooling_until.clear()

    # ------------------------------------------------------------------ internals
    def _quote_fetcher(self, instrument: Instrument) -> Callable[[], Awaitable[Quote | None]]:
        async def fetch() -> Quote | None:
            found = await self._inner.quotes([instrument])
            return found[0] if found else None
        return fetch

    @staticmethod
    def _copy(value: Any, **update: Any) -> Any:
        return None if value is None else value.model_copy(update=update, deep=True)

    async def _get(self, key: tuple, fetch: Callable[[], Awaitable[Any]]) -> Any:
        now = self._clock()
        entry = self._entries.get(key)
        if entry and now - entry.stored_at < self._ttl:
            self._entries.move_to_end(key)
            self._counts["hits"] += 1
            return self._copy(entry.value)
        self._counts["misses"] += 1
        if now < self._cooling_until.get(key, 0.0):
            return self._copy(self._stale_or_raise(entry, ProviderUnavailable("cooling down after a failed refresh")))
        task = self._inflight.get(key)
        if task is None:
            task = asyncio.ensure_future(self._refresh(key, fetch, entry))
            self._inflight[key] = task
            task.add_done_callback(lambda t, k=key: self._finished(k, t))
        return self._copy(await asyncio.shield(task))                  # one caller giving up must not cancel the shared fetch

    def _finished(self, key: tuple, task: asyncio.Future) -> None:
        self._inflight.pop(key, None)
        if not task.cancelled():
            task.exception()                                           # mark it retrieved: waiters re-raise it themselves

    async def _refresh(self, key: tuple, fetch: Callable[[], Awaitable[Any]], entry: _Entry | None) -> Any:
        for attempt in range(self._retries + 1):
            try:
                value = await fetch()
            except ProviderUnavailable as error:
                if attempt < self._retries:
                    self._counts["retries"] += 1
                    await self._sleep(self._backoff * 2 ** attempt)
                    continue
                self._cooling_until[key] = self._clock() + self._cooldown
                log.warning("market data unavailable for %s after %d attempts: %s", key[1:], attempt + 1, error)
                return self._stale_or_raise(entry, error)
            self._cooling_until.pop(key, None)
            if value is not None:                                      # "not found" is not stored
                self._store(key, value)
            return value
        raise AssertionError("unreachable")                            # the loop always returns or raises

    def _stale_or_raise(self, entry: _Entry | None, error: ProviderUnavailable) -> Any:
        if entry is not None and self._clock() - entry.stored_at <= self._max_stale:
            self._counts["stale_served"] += 1
            return self._copy(entry.value, stale=True)                 # as_of stays the time it was really fetched
        raise error

    def _store(self, key: tuple, value: Any) -> None:
        self._entries[key] = _Entry(value, self._clock())
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)                          # least recently used


def build_market_provider(inner: MarketDataProvider, cfg: MarketDataCfg, **clock_and_sleep: Any) -> MarketDataProvider:
    """The configured cache around `inner`; a ttl of 0 means no cache at all."""
    if cfg.cache_ttl_seconds <= 0:
        return inner
    return CachedProvider(
        inner, ttl=cfg.cache_ttl_seconds, max_stale=cfg.cache_max_stale_seconds, max_entries=cfg.cache_max_entries,
        retries=cfg.retries, backoff=cfg.retry_base_seconds, cooldown=cfg.cooldown_seconds, **clock_and_sleep)
