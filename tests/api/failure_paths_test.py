"""The small failure paths that keep shutdown, session end and parsing calm: nothing here may raise to the user.

Run:  .venv/bin/python -m pytest tests/api/failure_paths_test.py -v
"""
import asyncio
import logging

import pytest
from starlette.testclient import TestClient

from src.api.app import _default_build, create_app
from src.core.grounding import numbers_in
from src.data.news.google_news import GoogleNewsProvider
from src.workflow.runtime import Runtime
from tests.api.chat_api_test import FakeStore, make_runtime


# ---------------------------------------------------------------- the runtime is built lazily
def test_the_default_build_asks_bootstrap_for_a_runtime(monkeypatch):
    sentinel = object()
    monkeypatch.setattr("src.workflow.bootstrap.build_runtime", lambda: sentinel)
    assert _default_build() is sentinel


def test_the_app_builds_its_runtime_at_startup_when_none_is_given():
    built = []
    rt = make_runtime()

    def build():
        built.append(1)
        return rt

    with TestClient(create_app(build=build)) as client:
        assert client.get("/health").status_code == 200
    assert built == [1]


# ---------------------------------------------------------------- ending a session
class CrashingSource:
    async def close(self):
        raise RuntimeError("callback server already gone")


def test_a_source_that_fails_to_close_does_not_fail_the_request(caplog):
    store = FakeStore()
    store._fake_open["thread-0001"] = ["kite"]
    store.disconnect = lambda thread, name: CrashingSource()
    with TestClient(create_app(runtime=make_runtime(store=store))) as client, caplog.at_level(logging.ERROR):
        res = client.delete("/sessions/thread-0001")
    assert res.status_code == 204 and "closing a portfolio source failed" in caplog.text


# ---------------------------------------------------------------- shutdown
class BrokenStore(FakeStore):
    async def close_all(self):
        raise RuntimeError("connection already closed")


def test_a_failure_while_closing_connections_is_logged_not_raised(caplog):
    rt = Runtime(graph=None, agents={}, store=BrokenStore(), memory=None)
    with caplog.at_level(logging.ERROR):
        asyncio.run(rt.close())
    assert "closing connections failed" in caplog.text


# ---------------------------------------------------------------- numbers in text
@pytest.mark.parametrize("text, expected", [
    ("₹36,00,000 and 3,600,000", {3600000.0}),
    ("grew 7.5% in 10 years", {7.5, 10.0}),
    ("", set()),
    (None, set()),
    ("no digits here", set()),
    ("1,2,3", {123.0}),
])
def test_numbers_are_read_whatever_the_grouping(text, expected):
    assert numbers_in(text) == expected


# ---------------------------------------------------------------- news feed parsing
def feed(*items):
    body = "".join(f"<item><title>{t}</title><link>{l}</link><pubDate>{d}</pubDate>{s}</item>" for t, l, d, s in items)
    return f"<rss><channel>{body}</channel></rss>".encode()


def test_an_item_with_an_unreadable_date_is_skipped():
    xml = feed(("Good - Mint", "https://x.example/1", "Mon, 16 Nov 2026 10:00:00 GMT", ""),
               ("Bad date - Mint", "https://x.example/2", "not a date", ""))
    items = asyncio.run(GoogleNewsProvider(fetch=lambda url: xml).search("rbi", days=7, limit=10))
    assert [i.url for i in items] == ["https://x.example/1"]


def test_a_publisher_is_taken_from_the_title_when_the_feed_has_no_source_tag():
    xml = feed(("RBI holds rates - Economic Times", "https://x.example/1", "Mon, 16 Nov 2026 10:00:00 GMT", ""))
    item = asyncio.run(GoogleNewsProvider(fetch=lambda url: xml).search("rbi", days=7, limit=10))[0]
    assert item.title == "RBI holds rates" and item.publisher == "Economic Times"


def test_the_result_is_capped_at_the_limit():
    rows = [(f"T{i} - P", f"https://x.example/{i}", "Mon, 16 Nov 2026 10:00:00 GMT", "") for i in range(6)]
    assert len(asyncio.run(GoogleNewsProvider(fetch=lambda url: feed(*rows)).search("q", days=7, limit=3))) == 3
