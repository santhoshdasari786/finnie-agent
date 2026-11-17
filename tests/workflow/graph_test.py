"""The compiled graph end to end, with stub agents (no LLM, no network).

Run:  .venv/bin/python -m pytest tests/workflow/graph_test.py -v
Nodes are tested in nodes_test.py; here we test the WIRING: which path a message takes.
"""
import pytest

from src.common.models import QASettings
from src.core.guardrails import DISTRESS_SUFFIX, Guardrails
from src.workflow.graph import ask, build_graph

pytestmark = pytest.mark.asyncio

DISTRESS = "I can't pay my credit card EMI"


@pytest.fixture
def settings():
    return QASettings()

@pytest.fixture
def app(stub_agents, settings):
    return build_graph(stub_agents, Guardrails(settings), settings)

def called(stub_agents):
    return [n for n, a in stub_agents.items() if a.calls]


# ---------------------------------------------------------------- routing paths
@pytest.mark.parametrize("text, agent", [
    ("What is a SIP?", "finance_qa"),
    ("Nifty close today", "market_analysis"),
    ("Analyze my portfolio", "portfolio"),
    ("capital gains tax on shares", "tax_education"),
    ("Can I retire at 50?", "goal_planning"),
    ("latest news on Infosys", "news_synthesizer"),
])
async def test_each_question_reaches_exactly_one_agent(app, stub_agents, text, agent):
    r = await ask(app, text)
    assert r.agent == agent and called(stub_agents) == [agent]


# ---------------------------------------------------------------- the guard branch
async def test_blocked_message_never_reaches_an_agent(app, stub_agents):
    r = await ask(app, "I want to die")
    assert r.agent == "guard" and r.status == "redirect"
    assert called(stub_agents) == []

async def test_blocked_even_when_a_hint_is_given(app, stub_agents):
    r = await ask(app, "I want to die", agent="portfolio")
    assert r.agent == "guard" and called(stub_agents) == []

async def test_empty_message_is_blocked(app, stub_agents):
    r = await ask(app, "   ")
    assert r.agent == "guard" and called(stub_agents) == []


# ---------------------------------------------------------------- the hint
async def test_hint_overrides_the_rules(app, stub_agents):
    r = await ask(app, "Analyze my portfolio", agent="tax_education")
    assert r.agent == "tax_education" and called(stub_agents) == ["tax_education"]

async def test_unknown_hint_is_rejected_and_nothing_runs(app, stub_agents):
    with pytest.raises(ValueError):
        await ask(app, "What is a SIP?", agent="made_up")
    assert called(stub_agents) == []


# ---------------------------------------------------------------- context and output
async def test_flags_thread_and_profile_reach_the_agent(app, stub_agents):
    await ask(app, f"{DISTRESS}. What is a SIP?", thread_id="t-42")
    _, ctx = stub_agents["finance_qa"].calls[0]
    assert "financial_distress" in ctx.flags and ctx.thread_id == "t-42"

async def test_distress_suffix_is_appended_exactly_once(app):
    r = await ask(app, f"{DISTRESS}. What is a SIP?")
    assert r.text.count(DISTRESS_SUFFIX) == 1

async def test_normal_answer_has_no_suffix(app):
    r = await ask(app, "What is a SIP?")
    assert DISTRESS_SUFFIX not in r.text


# ---------------------------------------------------------------- failures stay inside the graph
async def test_agent_crash_becomes_an_error_result(app, stub_agents, settings):
    stub_agents["finance_qa"].raises = RuntimeError("boom")
    r = await ask(app, "What is a SIP?")
    assert r.status == "error" and "boom" not in r.text and settings.error_message in r.text

async def test_needs_login_survives_the_whole_graph(settings):
    from tests.conftest import StubAgent
    from src.workflow.state import AGENT_NAMES
    agents = {n: StubAgent(n) for n in AGENT_NAMES}
    agents["portfolio"] = StubAgent("portfolio", status="needs_login", data={"login_url": "https://kite.example/login"})
    app = build_graph(agents, Guardrails(settings), settings)
    r = await ask(app, "Analyze my portfolio")
    assert r.status == "needs_login" and r.data["login_url"].startswith("https://")

async def test_the_graph_is_reusable_across_calls(app, stub_agents):
    a = await ask(app, "Nifty close today")
    b = await ask(app, "What is a SIP?")
    assert (a.agent, b.agent) == ("market_analysis", "finance_qa")
