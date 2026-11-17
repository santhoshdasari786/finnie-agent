"""The three RAG command-line tools and the Finnie terminal chat, driven in-process.

Run:  .venv/bin/python -m pytest tests/rag/cli_test.py -v
Offline: the glossary tool reads the real glossary; the ingestion and retrieval tools get fake components; the chat gets a fake graph.
"""
import asyncio
import builtins
import sys
from pathlib import Path

import pytest

from src.core.contracts import AgentResult, Citation
from src.rag.common.models import SearchHit

ROOT = Path(__file__).resolve().parents[2]


def run_cli(module, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["tool", *argv])
    module.main()


# ================================================================ glossary tool
def test_the_glossary_tool_shows_a_definition_and_where_to_read_more(monkeypatch, capsys):
    from src.rag.glossary import cli
    monkeypatch.chdir(ROOT)
    run_cli(cli, monkeypatch, "what is an ETF?", "--config", "src/config/rag.yaml")
    out = capsys.readouterr().out
    assert "ALIAS match on 'etf'" in out and "Exchange-traded fund" in out and "read more: mutual-funds-and-etfs" in out and "sources:" in out


def test_the_glossary_tool_says_when_a_term_is_not_there(monkeypatch, capsys):
    from src.rag.glossary import cli
    monkeypatch.chdir(ROOT)
    run_cli(cli, monkeypatch, "what is a warrant", "--config", "src/config/rag.yaml")
    assert "NO MATCH" in capsys.readouterr().out


def test_the_glossary_tool_flags_an_ambiguous_term(monkeypatch, capsys):
    from src.rag.glossary import cli
    monkeypatch.chdir(ROOT)
    run_cli(cli, monkeypatch, "what is a bond", "--config", "src/config/rag.yaml")
    out = capsys.readouterr().out
    assert "AMBIGUOUS" in out and "Bond (fixed income)" in out and "Bond (surety / legal)" in out


def test_the_glossary_tool_can_override_the_fuzzy_cutoff(monkeypatch, capsys):
    from src.rag.glossary import cli
    monkeypatch.chdir(ROOT)
    run_cli(cli, monkeypatch, "expense ratoi", "--config", "src/config/rag.yaml", "--fuzzy", "0.8")
    assert "FUZZY match" in capsys.readouterr().out


# ================================================================ retrieval tool
class FakeEmbedder:
    model_id, dimensions = "fake", 3

    def embed_query(self, text):
        return [1.0, 0.0, 0.0]


class FakeStore:
    name = "kb__fake__3"

    def __init__(self, count=5):
        self.count, self.searches = count, []

    def ensure_collection(self): ...

    def info(self):
        return type("I", (), {"count": self.count})()

    def search(self, vector, k, filters=None):
        self.searches.append((k, filters))
        return [SearchHit("a:0", "alpha text about SIPs", 0.91, {"doc_id": "a", "title": "Alpha"})]


def fake_build(store):
    from src.rag.retrieval.retrievers.vector import VectorRetriever

    def build(kind, spec, **extra):
        if kind == "embedder":
            return FakeEmbedder()
        if kind == "vector_store":
            return store
        if kind == "postprocessor":
            return type("Pass", (), {"process": lambda self, q, hits: hits})()
        if kind == "retriever":
            return VectorRetriever(**extra)
        raise AssertionError(kind)

    return build


def test_the_retrieval_tool_prints_the_status_and_each_chunk(monkeypatch, capsys):
    from src.rag.retrieval import cli
    store = FakeStore()
    monkeypatch.setattr(cli, "build", fake_build(store))
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    run_cli(cli, monkeypatch, "what is a SIP", "--config", str(ROOT / "src/config/rag.yaml"), "--category", "products", "--k", "2")
    out = capsys.readouterr().out
    assert out.startswith("ok best: 0.91") and "Alpha" in out and "a:0" in out
    assert store.searches == [(2 * 4, {"topic": "products"})]


def test_the_retrieval_tool_refuses_an_empty_collection(monkeypatch):
    from src.rag.retrieval import cli
    monkeypatch.setattr(cli, "build", fake_build(FakeStore(count=0)))
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    with pytest.raises(SystemExit, match="empty"):
        run_cli(cli, monkeypatch, "q", "--config", str(ROOT / "src/config/rag.yaml"))


# ================================================================ ingestion tool
def test_the_ingestion_tool_wires_the_pipeline_from_the_config_and_prints_the_stats(monkeypatch, capsys):
    from src.rag.ingestion import cli
    built, pipelines = [], []

    def build(kind, spec, **extra):
        built.append(kind)
        return {"embedder": FakeEmbedder(), "vector_store": FakeStore()}.get(kind, f"<{kind}>")

    class Pipeline:
        def __init__(self, **kw):
            pipelines.append(kw)

        def run(self):
            return {"seen": 3, "ingested": 2}

    monkeypatch.setattr(cli, "build", build)
    monkeypatch.setattr(cli, "IngestionPipeline", Pipeline)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    run_cli(cli, monkeypatch, "--config", str(ROOT / "src/config/rag.yaml"))
    assert "{'seen': 3, 'ingested': 2}" in capsys.readouterr().out
    assert set(built) == {"embedder", "vector_store", "loader", "chunker", "manifest"}
    assert pipelines[0]["batch_size"] == 64 and pipelines[0]["on_error"] == "skip_and_log"


def test_the_ingestion_tool_requires_a_config(monkeypatch):
    from src.rag.ingestion import cli
    monkeypatch.setattr(sys, "argv", ["tool"])
    with pytest.raises(SystemExit):
        cli.main()


# ================================================================ the terminal chat
class FakeStoreForChat:
    def __init__(self):
        self.closed = 0

    async def close_all(self):
        self.closed += 1


def drive_chat(monkeypatch, lines, replies):
    """Runs agents.cli.main() with scripted keyboard input and a fake graph. Returns (what was asked, the store)."""
    from src.agents import cli
    asked, feed, store = [], iter(lines), FakeStoreForChat()
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(feed))
    monkeypatch.setattr(cli, "ConnectionStore", lambda: store)
    monkeypatch.setattr(cli, "build_app", lambda store=None: "graph")

    async def ask(app, text, thread_id="default", agent=None):
        asked.append((text, agent, thread_id))
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(cli, "ask", ask)
    asyncio.run(cli.main())
    return asked, store


def result(text="An answer.", status="ok", **kw):
    return AgentResult(agent="finance_qa", status=status, text=text, disclaimer="Educational only.", **kw)


def test_a_question_is_asked_and_answered_with_a_disclaimer_then_exit(monkeypatch, capsys):
    asked, store = drive_chat(monkeypatch, ["What is a SIP?", "exit"], [result()])
    out = capsys.readouterr().out
    assert asked == [("What is a SIP?", None, "cli")] and "[finance_qa: ok]" in out and "An answer." in out and "Educational only." in out
    assert store.closed == 1                                      # live broker connections are closed on exit


def test_the_agent_command_forces_an_agent(monkeypatch):
    asked, _ = drive_chat(monkeypatch, ["/agent tax_education What is 80C?", ""], [result()])
    assert asked == [("What is 80C?", "tax_education", "cli")]


def test_citations_are_listed(monkeypatch, capsys):
    cites = [Citation(source="https://x.example/a", title="Alpha article", excerpt="e")]
    drive_chat(monkeypatch, ["q", "quit"], [result(citations=cites)])
    assert "citations:" in capsys.readouterr().out


def test_a_login_link_is_shown(monkeypatch, capsys):
    drive_chat(monkeypatch, ["connect kite", "exit"], [result("Open the link", status="needs_login", data={"login_url": "https://kite.example/login"})])
    assert ">>> https://kite.example/login" in capsys.readouterr().out


def test_an_unknown_agent_name_is_reported_and_the_chat_carries_on(monkeypatch, capsys):
    asked, store = drive_chat(monkeypatch, ["/agent nope hi", "What is a SIP?", "exit"], [ValueError("unknown agent 'nope'"), result()])
    out = capsys.readouterr().out
    assert "unknown agent 'nope'" in out and len(asked) == 2 and store.closed == 1


def test_the_store_is_closed_even_when_the_chat_crashes(monkeypatch):
    from src.agents import cli
    store = FakeStoreForChat()
    monkeypatch.setattr(builtins, "input", lambda prompt="": "hi")
    monkeypatch.setattr(cli, "ConnectionStore", lambda: store)
    monkeypatch.setattr(cli, "build_app", lambda store=None: "graph")

    async def boom(*a, **k):
        raise RuntimeError("graph exploded")

    monkeypatch.setattr(cli, "ask", boom)
    with pytest.raises(RuntimeError):
        asyncio.run(cli.main())
    assert store.closed == 1


@pytest.mark.parametrize("line, expected", [
    ("What is a SIP?", ("What is a SIP?", None)),
    ("/agent tax_education What is 80C?", ("What is 80C?", "tax_education")),
    ("/agent goal_planning", ("", "goal_planning")),
    ("/agentx hello", ("/agentx hello", None)),
])
def test_parse_splits_the_agent_command_from_the_question(line, expected):
    from src.agents.cli import parse
    assert parse(line) == expected


def test_importing_the_chat_does_not_start_it():
    import importlib
    from src.agents import cli
    importlib.reload(cli)                                         # would block on input() if main() ran at import
