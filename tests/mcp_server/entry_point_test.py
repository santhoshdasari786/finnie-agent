"""python -m src.mcp_server: logs go to stderr (stdout belongs to the protocol) and the server runs over stdio without a banner."""
import logging
import sys

from src.mcp_server import __main__ as entry


def test_the_server_runs_over_stdio_without_a_banner(monkeypatch):
    runs = []
    monkeypatch.setattr(entry, "create_server", lambda: type("S", (), {"run": lambda self, **kw: runs.append(kw)})())
    monkeypatch.setattr(logging, "basicConfig", lambda **kw: None)
    entry.main()
    assert runs == [{"transport": "stdio", "show_banner": False}]


def test_logging_is_sent_to_stderr_never_stdout(monkeypatch):
    seen = {}
    monkeypatch.setattr(entry, "create_server", lambda: type("S", (), {"run": lambda self, **kw: None})())
    monkeypatch.setattr(logging, "basicConfig", lambda **kw: seen.update(kw))
    entry.main()
    assert seen["stream"] is sys.stderr and seen["level"] == logging.INFO
