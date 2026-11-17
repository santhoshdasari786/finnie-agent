"""CachedProvider: a TTL cache, retry with backoff, and stale data as a fallback, in front of any MarketDataProvider.

Run:  .venv/bin/python -m pytest tests/data/market_cache_test.py -v
No network, no real sleeping: the inner provider is scripted, the clock and sleep are fakes.

Contract
  * a quote or a history is cached per instrument (history: per instrument AND range) for `ttl` seconds
  * "not found" (None / no quote) is never cached and never retried: it is an answer, not a failure
  * a ProviderUnavailable from the inner provider (rate limit, network) is retried `retries` times, waiting
    backoff, 2*backoff, 4*backoff ... between attempts. Any other exception is a bug and passes straight through
  * when every attempt fails and an older copy exists (younger than max_stale), that copy is returned with
    stale=True and its original as_of; otherwise ProviderUnavailable is raised
  * after a failed refresh the key "cools down" for `cooldown` seconds: no new attempts, no waiting, stale or an error at once
  * identical requests in flight at the same time share one fetch
  * at most `max_entries` are kept; the least recently used goes first
"""
import asyncio
from datetime import date, datetime, timezone

import pytest

from src.core.config import MarketDataCfg
from src.data.market.base import ProviderUnavailable
from src.data.market.cache import CachedProvider, build_market_provider
from src.data.market.models import Instrument, PriceHistory, PricePoint, Quote

pytestmark = pytest.mark.asyncio

A, B, C = Instrument(symbol="AAA"), Instrument(symbol="BBB"), Instrument(symbol="CCC")
DOWN = ProviderUnavailable("yahoo is rate limiting us")


def quote(inst, price=100.0):
    return Quote(instrument=inst, price=price, change_pct=1.0, currency="INR",
                 as_of=datetime(2026, 11, 17, 5, 30, tzinfo=timezone.utc), source="fake")


def history(inst, rng="3m", close=100.0):
    return PriceHistory(instrument=inst, range=rng, currency="INR", source="fake",
                        as_of=datetime(2026, 11, 17, 5, 30, tzinfo=timezone.utc),
                        points=[PricePoint(date=date(2026, 8, 3), close=close), PricePoint(date=date(2026, 8, 4), close=close + 1)])


class Clock:
    def __init__(self):
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds                         # waiting takes (fake) time, like the real thing


class Inner:
    """Scripted provider. quote_script[symbol] / history_script[(symbol, range)] is a list of outcomes consumed in
    order (the last one repeats): a Quote / PriceHistory, None (not found), or an Exception to raise."""
    name = "fake"

    def __init__(self):
        self.quote_calls: list[list[str]] = []
        self.history_calls: list[tuple[str, str]] = []
        self.quote_script: dict[str, list] = {}
        self.history_script: dict[tuple[str, str], list] = {}
        self.pause = 0                                # how many event-loop turns each fetch takes

    @staticmethod
    def _next(script):
        item = script[0] if len(script) == 1 else script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def quotes(self, instruments):
        self.quote_calls.append([i.symbol for i in instruments])
        for _ in range(self.pause):
            await asyncio.sleep(0)
        found = []
        for i in instruments:
            script = self.quote_script.setdefault(i.symbol, [quote(i)])
            item = self._next(script)
            if item is not None:
                found.append(item)
        return found

    async def history(self, instrument, rng):
        self.history_calls.append((instrument.symbol, rng))
        for _ in range(self.pause):
            await asyncio.sleep(0)
        script = self.history_script.setdefault((instrument.symbol, rng), [history(instrument, rng)])
        return self._next(script)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def inner():
    return Inner()


def make(inner, clock, **kw):
    opts = dict(ttl=100, max_stale=1000, max_entries=50, retries=2, backoff=0.5, cooldown=30, clock=clock, sleep=clock.sleep)
    return CachedProvider(inner, **{**opts, **kw})


def symbols(quotes):
    return [q.instrument.symbol for q in quotes]


# ================================================================ the cache
async def test_a_second_request_inside_the_ttl_does_not_reach_the_provider(inner, clock):
    p = make(inner, clock)
    await p.quotes([A])
    clock.now += 99.9
    await p.quotes([A])
    assert inner.quote_calls == [["AAA"]]


async def test_the_entry_expires_exactly_at_the_ttl(inner, clock):
    p = make(inner, clock)
    await p.quotes([A])
    clock.now += 100
    await p.quotes([A])
    assert len(inner.quote_calls) == 2


async def test_each_instrument_is_cached_on_its_own(inner, clock):
    p = make(inner, clock)
    await p.quotes([A, B])
    await p.quotes([B, C])
    fetched = sorted(s for call in inner.quote_calls for s in call)
    assert fetched == ["AAA", "BBB", "CCC"]                      # B was not fetched twice


async def test_the_result_keeps_the_order_asked_and_drops_duplicates(inner, clock):
    p = make(inner, clock)
    assert symbols(await p.quotes([B, A, B])) == ["BBB", "AAA"]
    assert symbols(await p.quotes([C, A])) == ["CCC", "AAA"]


async def test_no_instruments_means_no_calls(inner, clock):
    assert await make(inner, clock).quotes([]) == []
    assert inner.quote_calls == []


async def test_a_cached_quote_keeps_the_time_it_was_really_fetched(inner, clock):
    p = make(inner, clock)
    first = (await p.quotes([A]))[0]
    clock.now += 50
    again = (await p.quotes([A]))[0]
    assert again.as_of == first.as_of and again.stale is False


async def test_what_you_get_is_a_copy_so_changing_it_cannot_corrupt_the_cache(inner, clock):
    p = make(inner, clock)
    got = (await p.quotes([A]))[0]
    got.price = -1
    assert (await p.quotes([A]))[0].price == 100.0
    h = await p.history(A, "3m")
    h.points.clear()
    assert len((await p.history(A, "3m")).points) == 2


async def test_history_is_cached_per_instrument_and_per_range(inner, clock):
    p = make(inner, clock)
    await p.history(A, "3m")
    await p.history(A, "3m")
    await p.history(A, "1y")
    await p.history(B, "3m")
    assert inner.history_calls == [("AAA", "3m"), ("AAA", "1y"), ("BBB", "3m")]


async def test_quotes_and_history_do_not_share_entries(inner, clock):
    p = make(inner, clock)
    await p.quotes([A])
    await p.history(A, "3m")
    assert len(inner.quote_calls) == 1 and len(inner.history_calls) == 1


# ================================================================ not found is not a failure
async def test_a_symbol_with_no_quote_is_not_cached_and_not_retried(inner, clock):
    inner.quote_script["AAA"] = [None]
    p = make(inner, clock)
    assert await p.quotes([A]) == []
    assert await p.quotes([A]) == []
    assert len(inner.quote_calls) == 2 and clock.sleeps == []


async def test_history_not_found_is_none_not_cached_not_retried(inner, clock):
    inner.history_script[("AAA", "3m")] = [None]
    p = make(inner, clock)
    assert await p.history(A, "3m") is None
    assert await p.history(A, "3m") is None
    assert len(inner.history_calls) == 2 and clock.sleeps == []


async def test_not_found_after_a_good_answer_leaves_the_old_entry_alone(inner, clock):
    inner.history_script[("AAA", "3m")] = [history(A), None]
    p = make(inner, clock, ttl=10)
    await p.history(A, "3m")
    clock.now += 11
    assert await p.history(A, "3m") is None                      # an honest "not found" now
    assert p.stats()["entries"] == 1


# ================================================================ retry with backoff
async def test_a_transient_failure_is_retried_with_doubling_waits(inner, clock):
    inner.quote_script["AAA"] = [DOWN, DOWN, quote(A, 123.0)]
    p = make(inner, clock)
    got = await p.quotes([A])
    assert got[0].price == 123.0 and len(inner.quote_calls) == 3
    assert clock.sleeps == [0.5, 1.0]


async def test_the_wait_grows_with_the_backoff_setting(inner, clock):
    inner.quote_script["AAA"] = [DOWN]
    p = make(inner, clock, retries=3, backoff=1.0)
    with pytest.raises(ProviderUnavailable):
        await p.quotes([A])
    assert clock.sleeps == [1.0, 2.0, 4.0] and len(inner.quote_calls) == 4


async def test_zero_retries_means_one_attempt(inner, clock):
    inner.quote_script["AAA"] = [DOWN]
    p = make(inner, clock, retries=0)
    with pytest.raises(ProviderUnavailable):
        await p.quotes([A])
    assert len(inner.quote_calls) == 1 and clock.sleeps == []


async def test_history_is_retried_too(inner, clock):
    inner.history_script[("AAA", "3m")] = [DOWN, history(A)]
    assert (await make(inner, clock).history(A, "3m")).points
    assert clock.sleeps == [0.5]


async def test_exhausted_retries_with_nothing_cached_raise(inner, clock):
    inner.history_script[("AAA", "3m")] = [DOWN]
    with pytest.raises(ProviderUnavailable):
        await make(inner, clock).history(A, "3m")


async def test_a_programming_error_is_not_retried_and_does_not_cool_the_key_down(inner, clock):
    inner.history_script[("AAA", "3m")] = [ValueError("unknown range"), history(A)]
    p = make(inner, clock)
    with pytest.raises(ValueError):
        await p.history(A, "3m")
    assert clock.sleeps == [] and len(inner.history_calls) == 1
    assert (await p.history(A, "3m")).points                     # no cool-down: the next call goes straight through


async def test_an_unexpected_quote_error_passes_straight_through(inner, clock):
    inner.quote_script["AAA"] = [RuntimeError("bug")]
    with pytest.raises(RuntimeError):
        await make(inner, clock).quotes([A, B])


# ================================================================ several instruments, some failing
async def test_one_failing_symbol_does_not_hide_the_others(inner, clock):
    inner.quote_script["BBB"] = [DOWN]
    got = await make(inner, clock).quotes([A, B])
    assert symbols(got) == ["AAA"]


async def test_if_every_symbol_fails_the_failure_is_raised(inner, clock):
    inner.quote_script["AAA"] = [DOWN]
    inner.quote_script["BBB"] = [DOWN]
    with pytest.raises(ProviderUnavailable):
        await make(inner, clock).quotes([A, B])


async def test_a_failure_is_not_hidden_behind_a_not_found(inner, clock):
    inner.quote_script["AAA"] = [None]                           # genuinely unknown
    inner.quote_script["BBB"] = [DOWN]
    with pytest.raises(ProviderUnavailable):
        await make(inner, clock).quotes([A, B])


async def test_only_not_found_is_an_empty_list_not_an_error(inner, clock):
    inner.quote_script["AAA"] = [None]
    inner.quote_script["BBB"] = [None]
    assert await make(inner, clock).quotes([A, B]) == []


# ================================================================ stale fallback
async def test_when_a_refresh_fails_the_old_copy_is_served_and_marked_stale(inner, clock):
    p = make(inner, clock)
    first = (await p.quotes([A]))[0]
    inner.quote_script["AAA"] = [DOWN]
    clock.now += 500                                              # past the ttl, inside max_stale
    got = (await p.quotes([A]))[0]
    assert got.stale is True and got.price == first.price and got.as_of == first.as_of
    assert p.stats()["stale_served"] == 1


async def test_a_fresh_hit_is_never_marked_stale(inner, clock):
    p = make(inner, clock)
    await p.quotes([A])
    assert (await p.quotes([A]))[0].stale is False


async def test_history_falls_back_to_stale_too(inner, clock):
    p = make(inner, clock)
    await p.history(A, "3m")
    inner.history_script[("AAA", "3m")] = [DOWN]
    clock.now += 500
    got = await p.history(A, "3m")
    assert got.stale is True and len(got.points) == 2


async def test_a_copy_exactly_max_stale_old_is_still_served(inner, clock):
    p = make(inner, clock, max_stale=1000)
    await p.quotes([A])
    inner.quote_script["AAA"] = [DOWN]
    clock.now += 998.5                                            # the retries wait 0.5 + 1.0 s, so the copy is exactly 1000 s old
    assert (await p.quotes([A]))[0].stale is True


async def test_a_copy_older_than_max_stale_is_not_served(inner, clock):
    p = make(inner, clock, max_stale=1000)
    await p.quotes([A])
    inner.quote_script["AAA"] = [DOWN]
    clock.now += 1001
    with pytest.raises(ProviderUnavailable):
        await p.quotes([A])


async def test_the_stale_copy_is_returned_for_one_symbol_while_another_is_fresh(inner, clock):
    p = make(inner, clock)
    await p.quotes([A])
    clock.now += 500
    inner.quote_script["AAA"] = [DOWN]
    got = {q.instrument.symbol: q for q in await p.quotes([A, B])}
    assert got["AAA"].stale is True and got["BBB"].stale is False


async def test_a_successful_refresh_after_a_failure_is_fresh_again(inner, clock):
    p = make(inner, clock, cooldown=0)
    await p.quotes([A])
    inner.quote_script["AAA"] = [DOWN, DOWN, DOWN, quote(A, 150.0)]       # all 3 attempts fail, the 4th call succeeds
    clock.now += 500
    assert (await p.quotes([A]))[0].stale is True
    clock.now += 1                                                # cooldown is 0: the next call tries again
    again = (await p.quotes([A]))[0]
    assert again.stale is False and again.price == 150.0


# ================================================================ cool-down
async def test_after_a_failed_refresh_the_key_is_left_alone_for_the_cooldown(inner, clock):
    p = make(inner, clock, cooldown=30)
    await p.quotes([A])
    inner.quote_script["AAA"] = [DOWN]
    clock.now += 500
    await p.quotes([A])                                           # exhausts the retries, serves stale
    attempts, waited = len(inner.quote_calls), len(clock.sleeps)
    clock.now += 10
    got = (await p.quotes([A]))[0]
    assert got.stale is True
    assert len(inner.quote_calls) == attempts and len(clock.sleeps) == waited      # no new attempt, no waiting


async def test_the_cooldown_ends_exactly_when_it_says(inner, clock):
    p = make(inner, clock, cooldown=30)
    await p.quotes([A])
    inner.quote_script["AAA"] = [DOWN]
    clock.now += 500
    await p.quotes([A])
    failed_at = clock.now
    attempts = len(inner.quote_calls)
    clock.now = failed_at + 29.9
    await p.quotes([A])
    assert len(inner.quote_calls) == attempts                      # still cooling down
    clock.now = failed_at + 30
    await p.quotes([A])
    assert len(inner.quote_calls) > attempts                       # exactly at the cooldown: tries again


async def test_clear_also_ends_a_cooldown(inner, clock):
    inner.history_script[("AAA", "3m")] = [DOWN, DOWN, DOWN, history(A)]
    p = make(inner, clock, cooldown=1000)
    with pytest.raises(ProviderUnavailable):
        await p.history(A, "3m")
    p.clear()
    assert (await p.history(A, "3m")).points                       # would fail fast without clear()


async def test_after_the_cooldown_it_tries_again(inner, clock):
    p = make(inner, clock, cooldown=30)
    await p.quotes([A])
    inner.quote_script["AAA"] = [DOWN]
    clock.now += 500
    await p.quotes([A])
    attempts = len(inner.quote_calls)
    clock.now += 31
    await p.quotes([A])
    assert len(inner.quote_calls) > attempts


async def test_with_nothing_cached_the_cooldown_fails_fast(inner, clock):
    inner.history_script[("AAA", "3m")] = [DOWN]
    p = make(inner, clock, cooldown=30)
    with pytest.raises(ProviderUnavailable):
        await p.history(A, "3m")
    attempts, waited = len(inner.history_calls), len(clock.sleeps)
    with pytest.raises(ProviderUnavailable):
        await p.history(A, "3m")
    assert len(inner.history_calls) == attempts and len(clock.sleeps) == waited


async def test_one_key_cooling_down_does_not_block_another(inner, clock):
    inner.quote_script["AAA"] = [DOWN]
    p = make(inner, clock)
    with pytest.raises(ProviderUnavailable):
        await p.quotes([A])
    assert symbols(await p.quotes([B])) == ["BBB"]


# ================================================================ requests in flight
async def test_identical_requests_at_the_same_time_share_one_fetch(inner, clock):
    inner.pause = 3
    p = make(inner, clock)
    first, second = await asyncio.gather(p.quotes([A]), p.quotes([A]))
    assert len(inner.quote_calls) == 1 and first[0].price == second[0].price == 100.0


async def test_different_instruments_at_the_same_time_are_fetched_separately(inner, clock):
    inner.pause = 3
    p = make(inner, clock)
    await asyncio.gather(p.quotes([A]), p.quotes([B]))
    assert sorted(s for call in inner.quote_calls for s in call) == ["AAA", "BBB"]


async def test_a_shared_failure_reaches_every_waiter(inner, clock):
    inner.pause = 3
    inner.history_script[("AAA", "3m")] = [DOWN]
    p = make(inner, clock)
    results = await asyncio.gather(p.history(A, "3m"), p.history(A, "3m"), return_exceptions=True)
    assert all(isinstance(r, ProviderUnavailable) for r in results)
    assert len(inner.history_calls) == 3                          # one shared attempt sequence: 1 + 2 retries


async def test_one_caller_giving_up_does_not_cancel_the_fetch_the_others_wait_for(inner, clock):
    inner.pause = 5
    p = make(inner, clock)
    quitter = asyncio.ensure_future(p.quotes([A]))
    stayer = asyncio.ensure_future(p.quotes([A]))
    for _ in range(3):                                            # both are now waiting on the one shared fetch
        await asyncio.sleep(0)
    assert len(inner.quote_calls) == 1
    quitter.cancel()
    assert (await stayer)[0].price == 100.0
    assert len(inner.quote_calls) == 1


async def test_returned_copies_are_independent_between_waiters(inner, clock):
    inner.pause = 2
    p = make(inner, clock)
    one, two = await asyncio.gather(p.quotes([A]), p.quotes([A]))
    one[0].price = -5
    assert two[0].price == 100.0


# ================================================================ size limit
async def test_the_least_recently_used_entry_is_dropped_first(inner, clock):
    p = make(inner, clock, max_entries=2)
    await p.quotes([A])
    await p.quotes([B])
    await p.quotes([A])                                           # A is now the most recently used
    await p.quotes([C])                                           # B goes
    inner.quote_calls.clear()
    await p.quotes([A])
    await p.quotes([B])
    assert inner.quote_calls == [["BBB"]]
    assert p.stats()["entries"] == 2


async def test_clear_forgets_everything(inner, clock):
    p = make(inner, clock)
    await p.quotes([A])
    await p.history(A, "3m")
    p.clear()
    assert p.stats()["entries"] == 0
    await p.quotes([A])
    assert len(inner.quote_calls) == 2


# ================================================================ bookkeeping
async def test_stats_count_hits_misses_and_retries(inner, clock):
    inner.quote_script["AAA"] = [DOWN, quote(A)]
    p = make(inner, clock)
    await p.quotes([A])                                           # miss, one retry
    await p.quotes([A])                                           # hit
    await p.quotes([A])                                           # hit
    s = p.stats()
    assert (s["hits"], s["misses"], s["retries"], s["stale_served"], s["entries"]) == (2, 1, 1, 0, 1)


async def test_it_looks_like_the_provider_it_wraps(inner, clock):
    p = make(inner, clock)
    assert p.name == "fake" and callable(p.quotes) and callable(p.history)


async def test_the_cache_works_with_the_real_defaults():
    p = CachedProvider(Inner())
    assert (await p.quotes([A]))[0].price == 100.0


# ================================================================ built from the settings
async def test_the_settings_become_the_behaviour(inner, clock):
    cfg = MarketDataCfg(cache_ttl_seconds=60, cache_max_entries=7, cache_max_stale_seconds=500, retries=1,
                        retry_base_seconds=2.0, cooldown_seconds=5)
    p = build_market_provider(inner, cfg, clock=clock, sleep=clock.sleep)
    assert isinstance(p, CachedProvider)
    inner.quote_script["AAA"] = [DOWN]
    with pytest.raises(ProviderUnavailable):
        await p.quotes([A])
    assert clock.sleeps == [2.0]                                  # retries=1, backoff=2.0
    await p.quotes([B])
    clock.now += 59
    await p.quotes([B])
    clock.now += 2
    await p.quotes([B])                                           # ttl 60 has passed
    assert inner.quote_calls.count(["BBB"]) == 2


async def test_max_stale_comes_from_the_settings(inner, clock):
    cfg = MarketDataCfg(cache_ttl_seconds=10, cache_max_stale_seconds=50, retries=0)
    p = build_market_provider(inner, cfg, clock=clock, sleep=clock.sleep)
    await p.quotes([A])
    inner.quote_script["AAA"] = [DOWN]
    clock.now += 40                                                # expired (ttl 10) but younger than max_stale (50)
    assert (await p.quotes([A]))[0].stale is True
    clock.now += 1000                                              # past the cooldown, and far older than max_stale
    with pytest.raises(ProviderUnavailable):
        await p.quotes([A])


async def test_max_entries_comes_from_the_settings(inner, clock):
    p = build_market_provider(inner, MarketDataCfg(cache_max_entries=1), clock=clock, sleep=clock.sleep)
    await p.quotes([A])
    await p.quotes([B])                                            # A is pushed out
    await p.quotes([A])
    assert inner.quote_calls.count(["AAA"]) == 2


async def test_a_larger_max_entries_keeps_more(inner, clock):
    p = build_market_provider(inner, MarketDataCfg(cache_max_entries=2), clock=clock, sleep=clock.sleep)
    await p.quotes([A])
    await p.quotes([B])
    await p.quotes([A])                                            # both still fit
    assert inner.quote_calls == [["AAA"], ["BBB"]]


async def test_a_ttl_of_zero_switches_the_cache_off(inner):
    assert build_market_provider(inner, MarketDataCfg(cache_ttl_seconds=0)) is inner
