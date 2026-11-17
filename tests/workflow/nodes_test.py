"""Graph nodes, tested one at a time with stub agents (no LLM, no network, no LangGraph).

Run:  .venv/bin/python -m pytest tests/workflow/nodes_test.py -v
A node takes the state dict and returns a PARTIAL update; tests merge it back like LangGraph does.
"""
import pytest

from src.common.models import QASettings
from src.core.guardrails import DISTRESS_SUFFIX, Guardrails
from src.workflow.nodes import make_nodes
from tests.conftest import StubAgent

pytestmark = pytest.mark.asyncio

DISTRESS = "I can't pay my credit card EMI"


@pytest.fixture
def settings():
    return QASettings()

@pytest.fixture
def nodes(stub_agents, settings):
    return make_nodes(stub_agents, Guardrails(settings), settings)

async def step(node, state):
    """Run one node and merge its partial update, exactly what LangGraph does."""
    return {**state, **await node(state)}

def base(text, **extra):
    return {"text": text, "thread_id": "t1", **extra}


# ---------------------------------------------------------------- input_guard
async def test_input_guard_blocks_self_harm(nodes):
    s = await step(nodes["input_guard"], base("I want to die"))
    assert s["guard"].blocked and s["guard"].category == "self_harm"

async def test_input_guard_passes_with_flags(nodes):
    s = await step(nodes["input_guard"], base(f"{DISTRESS}. What is a SIP?"))
    assert not s["guard"].blocked and "financial_distress" in s["guard"].flags

async def test_input_guard_never_calls_an_agent(nodes, stub_agents):
    await nodes["input_guard"](base("I want to die"))
    assert all(a.calls == [] for a in stub_agents.values())


# ---------------------------------------------------------------- route
async def test_route_uses_rules(nodes):
    s = await step(nodes["route"], base("Analyze my portfolio"))
    assert s["decision"].intent == "portfolio" and s["decision"].source == "rules"

async def test_route_falls_back_to_concept_qa(nodes):
    s = await step(nodes["route"], base("What is a SIP?"))
    assert s["decision"].intent == "concept_qa" and s["decision"].source == "fallback"

async def test_route_hint_skips_the_rules(nodes):
    # the text says "portfolio" but the caller named the tax agent: the hint wins
    s = await step(nodes["route"], base("Analyze my portfolio", agent="tax_education"))
    assert s["decision"].intent == "tax" and s["decision"].source == "hint" and s["decision"].confidence == 1.0

@pytest.mark.parametrize("hint", ["evil", "Finance_QA", "concept_qa"])    # unknown, wrong case, an INTENT not an agent
async def test_route_rejects_an_unknown_hint(nodes, hint):
    with pytest.raises(ValueError):
        await nodes["route"](base("hi", agent=hint))

async def test_route_normalizes_whitespace(nodes):
    s = await step(nodes["route"], base("  What   is\na SIP? "))
    assert s["decision"].normalized_question == "What is a SIP?"

async def test_every_agent_name_is_a_valid_hint(nodes, stub_agents):
    for name in stub_agents:
        s = await step(nodes["route"], base("hi", agent=name))
        assert s["decision"].source == "hint"


# ---------------------------------------------------------------- run_agent
async def routed(nodes, text, **extra):
    s = await step(nodes["input_guard"], base(text, **extra))
    return await step(nodes["route"], s)

async def test_run_agent_calls_the_chosen_agent_once(nodes, stub_agents):
    s = await step(nodes["run_agent"], await routed(nodes, "Analyze my portfolio"))
    assert len(stub_agents["portfolio"].calls) == 1
    assert all(a.calls == [] for n, a in stub_agents.items() if n != "portfolio")
    assert s["result"].agent == "portfolio" and s["result"].status == "ok"

async def test_guard_flags_and_thread_reach_the_agent(nodes, stub_agents):
    await step(nodes["run_agent"], await routed(nodes, f"{DISTRESS}. What was the Nifty close today?"))
    query, ctx = stub_agents["market_analysis"].calls[0]
    assert "financial_distress" in ctx.flags and ctx.thread_id == "t1"
    assert query.startswith("I can't pay")

async def test_profile_reaches_the_agent(nodes, stub_agents):
    from src.core.contracts import UserProfile
    prof = UserProfile(risk_appetite="aggressive", risk_source="stated")
    await step(nodes["run_agent"], await routed(nodes, "Analyze my portfolio", profile=prof))
    assert stub_agents["portfolio"].calls[0][1].profile.risk_appetite == "aggressive"

async def test_a_crashing_agent_becomes_an_error_result(nodes, stub_agents, settings):
    stub_agents["portfolio"].raises = RuntimeError("secret internal detail")
    s = await step(nodes["run_agent"], await routed(nodes, "Analyze my portfolio"))
    assert s["result"].status == "error" and s["result"].text == settings.error_message
    assert "secret" not in s["result"].text

async def test_a_missing_agent_becomes_an_error_result(settings):
    nodes = make_nodes({}, Guardrails(settings), settings)             # no agents built at all
    s = await step(nodes["input_guard"], base("Analyze my portfolio"))
    s = await step(nodes["route"], s)
    s = await step(nodes["run_agent"], s)
    assert s["result"].status == "error" and s["result"].disclaimer

async def test_needs_login_passes_through_unchanged(nodes, stub_agents):
    stub_agents["portfolio"].status = "needs_login"
    stub_agents["portfolio"].data = {"login_url": "https://kite.example/login"}
    s = await step(nodes["run_agent"], await routed(nodes, "Analyze my portfolio"))
    assert s["result"].status == "needs_login" and s["result"].data["login_url"]


# ---------------------------------------------------------------- respond_blocked
async def test_respond_blocked_builds_a_redirect(nodes, settings):
    s = await step(nodes["input_guard"], base("I want to die"))
    s = await step(nodes["respond_blocked"], s)
    r = s["result"]
    assert r.status == "redirect" and r.agent == "guard" and r.text == s["guard"].reply
    assert r.disclaimer == settings.disclaimer and r.meta["category"] == "self_harm"

async def test_blocked_input_never_reaches_any_agent(nodes, stub_agents):
    s = await step(nodes["input_guard"], base("I want to die"))
    await nodes["respond_blocked"](s)
    assert all(a.calls == [] for a in stub_agents.values())


# ---------------------------------------------------------------- output_guard
async def test_output_guard_appends_the_distress_suffix(nodes):
    s = await step(nodes["input_guard"], base(f"{DISTRESS}. What is a SIP?"))
    s = await step(nodes["route"], s)
    s = await step(nodes["run_agent"], s)
    s = await step(nodes["output_guard"], s)
    assert s["result"].text.endswith(DISTRESS_SUFFIX)

async def test_output_guard_is_idempotent(nodes):
    # the real Q&A agent already appends the suffix itself; the graph must not add it a second time
    s = await step(nodes["input_guard"], base(f"{DISTRESS}. What is a SIP?"))
    s = await step(nodes["route"], s)
    s = await step(nodes["run_agent"], s)
    s = await step(nodes["output_guard"], s)
    s = await step(nodes["output_guard"], s)
    assert s["result"].text.count(DISTRESS_SUFFIX) == 1

async def test_output_guard_leaves_normal_answers_alone(nodes):
    s = await step(nodes["input_guard"], base("What is a SIP?"))
    s = await step(nodes["route"], s)
    s = await step(nodes["run_agent"], s)
    before = s["result"].text
    s = await step(nodes["output_guard"], s)
    assert s["result"].text == before

async def test_output_guard_does_not_mutate_the_agents_result(nodes):
    s = await step(nodes["input_guard"], base(f"{DISTRESS}. What is a SIP?"))
    s = await step(nodes["route"], s)
    s = await step(nodes["run_agent"], s)
    original = s["result"]
    s2 = await step(nodes["output_guard"], s)
    assert original.text != s2["result"].text and not original.text.endswith(DISTRESS_SUFFIX)
