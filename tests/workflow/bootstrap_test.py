"""Wiring: bootstrap builds the six agents, shares one cached market provider, and returns a Runtime; main.py builds the app.

Run:  .venv/bin/python -m pytest tests/workflow/bootstrap_test.py -v
No network and no keys: the knowledge base (Chroma + embeddings) and the LLM are replaced by fakes; everything else is real.

Contract
  build_agents    all six agents are real (none left as a "not available yet" placeholder), the two Q&A agents share one retriever,
                  and the market agent and the portfolio agent share ONE cached provider (so a price is fetched once)
  build_runtime   graph + agents + store + memory, ready to serve; build_app is its graph
  _Pending        a placeholder agent answers with a polite error, never crashes
  src.main        the FastAPI app, with CORS origins from FINNIE_CORS_ORIGINS
"""
import importlib

import pytest

from src.common.models import QASettings
from src.data.market.base import PROVIDERS
from src.data.market.cache import CachedProvider
from src.data.portfolio.store import ConnectionStore
from src.rag.common.models import Rag
from src.workflow import bootstrap
from src.workflow.runtime import Runtime
from src.workflow.state import AGENT_NAMES

from tests.conftest import FakeGlossary, FakeLLM, FakeRetriever

pytestmark = pytest.mark.asyncio


@pytest.fixture
def wired(monkeypatch):
    retriever, glossary = FakeRetriever(), FakeGlossary()
    monkeypatch.setattr(bootstrap, "build_rag", lambda: Rag(retriever, glossary, QASettings()))
    monkeypatch.setattr(bootstrap.LLMFactory, "get_default", classmethod(lambda cls: FakeLLM("an answer [1]")))
    return retriever, glossary


# ================================================================ the agents
async def test_every_agent_name_has_a_real_agent(wired):
    agents = bootstrap.build_agents(ConnectionStore())
    assert set(agents) == set(AGENT_NAMES)
    assert [n for n, a in agents.items() if isinstance(a, bootstrap._Pending)] == []
    assert [n for n, a in agents.items() if getattr(a, "name", n) != n] == []


async def test_the_two_qa_agents_share_one_retriever_and_glossary(wired):
    retriever, glossary = wired
    agents = bootstrap.build_agents()
    for name in ("finance_qa", "tax_education"):
        assert agents[name]._retriever is retriever and agents[name]._glossary is glossary


async def test_the_market_and_portfolio_agents_share_one_cached_provider(wired):
    agents = bootstrap.build_agents()
    provider = agents["market_analysis"].provider
    assert isinstance(provider, CachedProvider) and agents["portfolio"]._provider is provider
    assert isinstance(provider._inner, PROVIDERS["yfinance"])


async def test_the_cache_settings_come_from_app_yaml(wired):
    from src.core.config import load_app_config
    cfg = load_app_config().market_data
    provider = bootstrap.build_agents()["market_analysis"].provider
    assert provider._ttl == cfg.cache_ttl_seconds and provider._retries == cfg.retries


async def test_the_given_connection_store_is_the_one_the_portfolio_agent_uses(wired):
    store = ConnectionStore()
    assert bootstrap.build_agents(store)["portfolio"]._store is store


async def test_a_store_is_created_when_none_is_given(wired):
    assert isinstance(bootstrap.build_agents()["portfolio"]._store, ConnectionStore)


# ================================================================ the placeholder
async def test_a_pending_agent_answers_with_a_polite_error():
    pending = bootstrap._Pending("goal_planning")
    r = await pending.run("anything")
    assert pending.ready is False and r.status == "error" and "goal_planning" in r.text and r.disclaimer


# ================================================================ the runtime
async def test_build_runtime_returns_everything_one_app_needs(wired):
    store = ConnectionStore()
    rt = bootstrap.build_runtime(store=store)
    assert isinstance(rt, Runtime) and rt.store is store and rt.memory is not None and rt.graph is not None
    assert set(rt.agents) == set(AGENT_NAMES)


async def test_the_runtime_answers_a_question_through_the_whole_graph(wired):
    from src.workflow.graph import ask
    retriever, _ = wired
    rt = bootstrap.build_runtime()
    result = await ask(rt.graph, "What is a goal planning thing?", thread_id="boot-test-0001")
    assert result.agent and result.text
    await rt.close()


async def test_build_app_is_the_runtimes_graph(wired):
    assert hasattr(bootstrap.build_app(), "ainvoke")


async def test_a_given_memory_and_settings_are_used(wired):
    from src.workflow.memory import ConversationMemory
    memory = ConversationMemory()
    rt = bootstrap.build_runtime(settings=QASettings(max_question_chars=77), memory=memory)
    assert rt.memory is memory


# ================================================================ src.main
async def test_the_app_is_a_fastapi_app_with_the_default_origins(monkeypatch):
    monkeypatch.delenv("FINNIE_CORS_ORIGINS", raising=False)
    import src.main
    main = importlib.reload(src.main)
    cors = next(m for m in main.app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    assert main.app.title.startswith("Finnie") and "http://localhost:5173" in cors.kwargs["allow_origins"]


async def test_cors_origins_come_from_the_environment_and_are_trimmed(monkeypatch):
    monkeypatch.setenv("FINNIE_CORS_ORIGINS", " https://a.example , https://b.example ,, ")
    import src.main
    main = importlib.reload(src.main)
    cors = next(m for m in main.app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    assert cors.kwargs["allow_origins"] == ["https://a.example", "https://b.example"]
    monkeypatch.delenv("FINNIE_CORS_ORIGINS")
    importlib.reload(main)
