"""A portfolio question asked BEFORE connecting is answered as soon as the connection succeeds.

Real case (2026-11-14): "how's the market treating me?" -> menu -> "connect kite" -> login -> "connect kite"
said "connected" and forgot the question, so the user had to ask again.

Rules under test
  * asking with nothing connected (or with an expired session) remembers the question for this thread
  * the next SUCCESSFUL connect answers it in the same reply: "Connected to X." + the analysis
  * it is answered once, per thread, newest question wins, and `disconnect` forgets it
  * a bare menu request ("connect to my portfolio") is not a question and remembers nothing
  * if the analysis fails after connecting, the user still hears "connected" and is told to retry
  * no loops: a source that says "connected" but keeps expiring ends in a message, not recursion

Run:  .venv/bin/python -m pytest tests/agents/portfolioanalysis/pending_question_test.py -v
"""
import pytest

from src.agents.portfolio_analysis_agent import PortfolioAnalysisAgent
from src.common.models import QASettings
from src.core.contracts import AgentContext, UserProfile
from src.data.portfolio.base import ConnectInfo, SessionExpired
from src.data.portfolio.sample import SampleSource
from src.data.portfolio.store import ConnectionStore

from tests.agents.portfolioanalysis.portfolio_analysis_agent_test import EmptySource, FakeKite, FakeProvider
from tests.conftest import FakeLLM

pytestmark = pytest.mark.asyncio

Q = "how's the market treating me?"


class LyingSource:
    """Says it is connected, then expires on every read."""
    name, label = "lying", "Lying source"
    reads = 0
    async def status(self): return "available"
    async def connect(self, **p): return ConnectInfo(connected=True, message="Connected to lying.")
    async def holdings(self):
        type(self).reads += 1
        raise SessionExpired("lying")


def ctx(thread="t1"):
    return AgentContext(thread_id=thread, profile=UserProfile())

@pytest.fixture
def store():
    return ConnectionStore({"sample": SampleSource, "kite": FakeKite, "empty": EmptySource, "lying": LyingSource})

@pytest.fixture
def llm():
    return FakeLLM("Your portfolio is spread across stocks, a fund and gold.")

@pytest.fixture
def provider():
    return FakeProvider()

@pytest.fixture
def agent(store, provider, llm):
    return PortfolioAnalysisAgent(store, provider, llm=llm, settings=QASettings())

def kite(store, thread="t1"):
    return store._instances[(thread, "kite")]


# ================================================================ the store's pending slot
async def test_take_pending_returns_the_question_once():
    s = ConnectionStore({})
    s.set_pending("t", Q)
    assert s.take_pending("t") == Q and s.take_pending("t") is None

async def test_a_newer_pending_question_replaces_the_older():
    s = ConnectionStore({})
    s.set_pending("t", "first"); s.set_pending("t", "second")
    assert s.take_pending("t") == "second"

async def test_pending_is_per_thread():
    s = ConnectionStore({})
    s.set_pending("a", Q)
    assert s.take_pending("b") is None and s.take_pending("a") == Q

async def test_clear_pending_forgets_it():
    s = ConnectionStore({})
    s.set_pending("t", Q); s.clear_pending("t")
    assert s.take_pending("t") is None

async def test_close_all_forgets_pending_questions():
    s = ConnectionStore({})
    s.set_pending("t", Q)
    await s.close_all()
    assert s.take_pending("t") is None


# ================================================================ the happy path
async def test_a_question_asked_first_is_answered_when_a_source_connects(agent, llm):
    first = await agent.run(Q, ctx())
    assert first.status == "clarify"                                   # the menu, as before
    r = await agent.run("connect sample", ctx())
    assert r.status == "ok" and "Portfolio:" in r.text                 # the analysis, in the same reply
    assert "QUESTION\n" + Q in llm.prompt_text()                       # the model saw the ORIGINAL question

async def test_the_reply_starts_with_the_connection_message(agent):
    await agent.run(Q, ctx())
    r = await agent.run("connect sample", ctx())
    assert r.text.index("Connected") < r.text.index("Portfolio:")

async def test_the_kite_flow_from_the_bug_report(agent, store, llm):
    await agent.run(Q, ctx())                                          # menu
    login = await agent.run("connect kite", ctx())                     # link
    assert login.status == "needs_login" and llm.calls == []           # nothing is answered before the login
    kite(store).logged_in = True                                       # the user approved in the browser
    r = await agent.run("connect kite", ctx())
    assert r.status == "ok" and "KITESTOCK" in r.text and "Connected to Zerodha." in r.text
    assert "QUESTION\n" + Q in llm.prompt_text()

async def test_the_question_survives_the_login_step(agent, store):
    await agent.run(Q, ctx())
    await agent.run("connect kite", ctx())
    assert store.take_pending("t1") == Q


# ================================================================ answered once, newest wins
async def test_it_is_answered_only_once(agent, llm):
    await agent.run(Q, ctx())
    await agent.run("connect sample", ctx())
    calls = len(llm.calls)
    r = await agent.run("connect empty", ctx())
    assert len(llm.calls) == calls and "analyze my portfolio" in r.text

async def test_the_newest_question_wins(agent, llm):
    await agent.run("what is my risk?", ctx())
    await agent.run(Q, ctx())
    await agent.run("connect sample", ctx())
    seen = llm.prompt_text()
    assert "QUESTION\n" + Q in seen and "what is my risk?" not in seen

async def test_other_threads_are_not_answered(agent, llm):
    await agent.run(Q, ctx("t1"))
    r = await agent.run("connect sample", ctx("t2"))
    assert llm.calls == [] and "analyze my portfolio" in r.text


# ================================================================ things that are NOT questions
async def test_a_plain_connect_with_nothing_pending_is_unchanged(agent, llm):
    r = await agent.run("connect sample", ctx())
    assert llm.calls == [] and "Say 'analyze my portfolio'" in r.text

async def test_asking_for_the_menu_remembers_nothing(agent, llm):
    await agent.run("connect to my portfolio", ctx())
    r = await agent.run("connect sample", ctx())
    assert llm.calls == [] and "analyze my portfolio" in r.text

async def test_disconnect_forgets_the_question(agent, llm):
    await agent.run(Q, ctx())
    await agent.run("connect kite", ctx())
    await agent.run("disconnect kite", ctx())
    r = await agent.run("connect sample", ctx())
    assert llm.calls == [] and "analyze my portfolio" in r.text


# ================================================================ expiry
async def test_a_question_asked_after_the_session_expired_is_answered_after_the_new_login(agent, store, llm):
    await agent.run("connect kite", ctx())
    kite(store).logged_in = True
    await agent.run("connect kite", ctx())                             # connected
    kite(store).logged_in = False                                      # the Kite session times out
    r = await agent.run(Q, ctx())
    assert r.status == "needs_login"
    kite(store).logged_in = True                                       # logs in again
    r = await agent.run("connect kite", ctx())
    assert r.status == "ok" and "KITESTOCK" in r.text
    assert "QUESTION\n" + Q in llm.prompt_text()


# ================================================================ failure after connecting
async def test_if_the_analysis_fails_the_user_still_hears_they_are_connected(store, llm):
    agent = PortfolioAnalysisAgent(store, FakeProvider(error=RuntimeError("down")), llm=llm, settings=QASettings())
    await agent.run(Q, ctx())
    r = await agent.run("connect sample", ctx())
    assert r.status == "ok" and "Connected" in r.text and "try again" in r.text.lower()

async def test_a_failed_resume_does_not_leave_the_question_pending(store, llm):
    agent = PortfolioAnalysisAgent(store, FakeProvider(error=RuntimeError("down")), llm=llm, settings=QASettings())
    await agent.run(Q, ctx())
    await agent.run("connect sample", ctx())
    assert store.take_pending("t1") is None

async def test_a_source_that_keeps_expiring_ends_in_a_message_not_a_loop(agent, llm):
    LyingSource.reads = 0
    await agent.run("connect lying", ctx())
    r = await agent.run(Q, ctx())                                      # holdings expire -> reconnect -> expire again
    assert r.status in ("ok", "error", "needs_login") and llm.calls == []
    assert LyingSource.reads <= 3                                      # bounded: not 100s of retries
