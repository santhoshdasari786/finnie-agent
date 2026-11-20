"""Two agents answering one question: "Can I reach 1 crore in 10 years with my portfolio?"

Run:  .venv/bin/python -m pytest tests/workflow/portfolio_goal_test.py -v
Stub agents only: no LLM, no network.

Contract
  * a goal question that also says "my portfolio" runs the portfolio agent first, then the goal agent with the
    portfolio's total value as the starting balance (passed in the goal agent's saved facts, `ctx.slots`)
  * the reply is the goal agent's (agent "goal_planning", its chart data) with a code-written line saying where the starting
    balance came from, and `meta.collaboration` naming both agents
  * the portfolio agent does not say "ok" (not connected, login needed, error): that reply is returned as it is and the
    goal agent is not called, so the user is never given a projection from a balance that was not read
  * the portfolio agent crashes: the goal agent still answers, without the portfolio, and nothing is claimed
  * the user's own starting balance wins: no "taken from your portfolio" line when the plan did not use it
  * an ordinary goal question never calls the portfolio agent
"""
import pytest

from src.common.models import QASettings
from src.core.guardrails import Guardrails
from src.workflow.nodes import make_nodes
from src.workflow.router import route_by_rules
from src.workflow.state import RoutingDecision
from tests.conftest import StubAgent

pytestmark = pytest.mark.asyncio

QUESTION = "Can I reach 1 crore in 10 years with my portfolio?"
PORTFOLIO_OK = {"metrics": {"total_value": 500000.0}, "sources": ["sample"]}


def build(stub_agents, portfolio=None, goal=None):
    if portfolio is not None:
        stub_agents["portfolio"] = portfolio
    if goal is not None:
        stub_agents["goal_planning"] = goal
    settings = QASettings()
    return make_nodes(stub_agents, Guardrails(settings), settings)


def state(text=QUESTION):
    decision = route_by_rules(text) or RoutingDecision(intent="concept_qa", confidence=0.5, source="fallback",
                                                       normalized_question=text)
    return {"text": text, "thread_id": "t1", "decision": decision,
            "guard": Guardrails(QASettings()).check(text), "history": []}


def goal_stub(start=500000.0, status="ok"):
    return StubAgent("goal_planning", text="Goal answer.", status=status,
                     data={"plan": {"start": start}, "inputs": {}, "paths": []})


async def test_the_router_already_sees_both_intents():
    d = route_by_rules(QUESTION)
    assert d.intent == "goal" and "portfolio" in d.secondary_intents


async def test_the_goal_agent_starts_from_the_portfolio_value(stub_agents):
    folio = StubAgent("portfolio", data=PORTFOLIO_OK)
    goal = goal_stub()
    nodes = build(stub_agents, folio, goal)
    out = await nodes["run_agent"](state())
    assert len(folio.calls) == 1 and len(goal.calls) == 1
    assert goal.calls[0][1].slots["starting_balance"] == 500000.0
    r = out["result"]
    assert r.agent == "goal_planning" and r.data["plan"]["start"] == 500000.0
    assert "₹500,000" in r.text and "portfolio" in r.text.lower() and "Goal answer." in r.text
    assert r.meta["collaboration"] == {"agents": ["portfolio", "goal_planning"], "starting_balance": 500000.0}


async def test_the_portfolio_agent_is_asked_to_analyse_not_to_answer_the_goal(stub_agents):
    folio = StubAgent("portfolio", data=PORTFOLIO_OK)
    nodes = build(stub_agents, folio, goal_stub())
    await nodes["run_agent"](state())
    assert "goal" not in folio.calls[0][0].lower() and "portfolio" in folio.calls[0][0].lower()


@pytest.mark.parametrize("status", ["clarify", "needs_login", "error"])
async def test_a_portfolio_that_is_not_ready_is_shown_as_it_is(stub_agents, status):
    data = {"metrics": {"total_value": 500000.0}}       # a value is present, but the status is not ok: it must not be used
    if status == "needs_login":
        data["login_url"] = "https://example.test/login"
    folio = StubAgent("portfolio", text="Connect a portfolio first.", status=status, data=data)
    goal = goal_stub()
    nodes = build(stub_agents, folio, goal)
    out = await nodes["run_agent"](state())
    assert out["result"].agent == "portfolio" and out["result"].status == status
    assert goal.calls == []


async def test_a_portfolio_with_no_value_is_shown_as_it_is(stub_agents):
    folio = StubAgent("portfolio", text="Your connected portfolio has no holdings yet.", data={"sources": ["sample"]})
    goal = goal_stub()
    out = await build(stub_agents, folio, goal)["run_agent"](state())
    assert out["result"].agent == "portfolio" and goal.calls == []


async def test_a_crashing_portfolio_agent_does_not_stop_the_goal_answer(stub_agents):
    folio = StubAgent("portfolio")
    folio.raises = RuntimeError("boom")
    goal = goal_stub(start=0.0)
    out = await build(stub_agents, folio, goal)["run_agent"](state())
    assert out["result"].agent == "goal_planning" and "starting_balance" not in goal.calls[0][1].slots
    assert "collaboration" not in out["result"].meta and "as the starting balance" not in out["result"].text


async def test_the_users_own_starting_balance_is_not_overwritten_in_the_story(stub_agents):
    folio = StubAgent("portfolio", data=PORTFOLIO_OK)
    goal = goal_stub(start=200000.0)            # the plan used the user's 2 lakh, not the portfolio's 5 lakh
    out = await build(stub_agents, folio, goal)["run_agent"](state())
    assert "as the starting balance" not in out["result"].text and "collaboration" not in out["result"].meta


async def test_a_goal_that_still_needs_numbers_says_the_portfolio_will_be_the_start(stub_agents):
    folio = StubAgent("portfolio", data=PORTFOLIO_OK)
    goal = StubAgent("goal_planning", text="How many years do you have?", status="clarify")
    out = await build(stub_agents, folio, goal)["run_agent"](state("Can I retire early with my portfolio?"))
    r = out["result"]
    assert r.status == "clarify" and "₹500,000" in r.text and "How many years" in r.text


async def test_an_ordinary_goal_question_never_calls_the_portfolio_agent(stub_agents):
    folio = StubAgent("portfolio", data=PORTFOLIO_OK)
    goal = goal_stub(start=0.0)
    out = await build(stub_agents, folio, goal)["run_agent"](state("Can I reach 1 crore in 10 years saving 20000 a month?"))
    assert folio.calls == [] and out["result"].agent == "goal_planning" and "collaboration" not in out["result"].meta


async def test_without_a_portfolio_agent_the_goal_agent_answers_alone(stub_agents):
    del stub_agents["portfolio"]
    goal = goal_stub(start=0.0)
    out = await build(stub_agents, None, goal)["run_agent"](state())
    assert out["result"].agent == "goal_planning" and len(goal.calls) == 1


# ================================================================ connecting in the middle of the question
from src.core.contracts import AgentResult
from src.workflow.memory import ConversationMemory


def build_with_memory(stub_agents, portfolio, goal):
    stub_agents["portfolio"], stub_agents["goal_planning"] = portfolio, goal
    settings = QASettings()
    memory = ConversationMemory()
    return make_nodes(stub_agents, Guardrails(settings), settings, memory), memory


class ScriptedPortfolio(StubAgent):
    """First answers 'not connected', then (after the user connects) answers with a value."""
    def __init__(self):
        super().__init__("portfolio")
        self.script = [("clarify", None), ("ok", PORTFOLIO_OK)]

    async def run(self, query, ctx=None):
        self.calls.append((query, ctx))
        status, data = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        return AgentResult(agent="portfolio", status=status, text="portfolio text", data=data, disclaimer="d")


async def test_connecting_in_the_middle_finishes_the_goal_question(stub_agents):
    folio, goal = ScriptedPortfolio(), goal_stub()
    nodes, memory = build_with_memory(stub_agents, folio, goal)
    first = await nodes["run_agent"](state())
    assert first["result"].agent == "portfolio" and goal.calls == []             # asked to connect first
    after = await nodes["run_agent"](state("connect sample"))                    # the user connects
    r = after["result"]
    assert r.agent == "goal_planning" and r.meta["collaboration"]["starting_balance"] == 500000.0
    assert goal.calls[0][0] == QUESTION                                          # the ORIGINAL question, not "connect sample"
    assert goal.calls[0][1].slots["starting_balance"] == 500000.0


async def test_the_remembered_question_is_used_once(stub_agents):
    folio, goal = ScriptedPortfolio(), goal_stub()
    nodes, _ = build_with_memory(stub_agents, folio, goal)
    await nodes["run_agent"](state())
    await nodes["run_agent"](state("connect sample"))
    again = await nodes["run_agent"](state("analyze my portfolio"))
    assert again["result"].agent == "portfolio" and len(goal.calls) == 1


async def test_still_waiting_for_a_login_keeps_the_question(stub_agents):
    folio, goal = ScriptedPortfolio(), goal_stub()
    folio.script = [("clarify", None), ("needs_login", {"login_url": "https://x.test"}), ("ok", PORTFOLIO_OK)]
    nodes, _ = build_with_memory(stub_agents, folio, goal)
    await nodes["run_agent"](state())
    mid = await nodes["run_agent"](state("connect kite"))
    assert mid["result"].status == "needs_login" and goal.calls == []
    done = await nodes["run_agent"](state("connect kite"))
    assert done["result"].agent == "goal_planning"


async def test_an_unrelated_question_forgets_the_remembered_goal(stub_agents):
    folio, goal = ScriptedPortfolio(), goal_stub()
    nodes, _ = build_with_memory(stub_agents, folio, goal)
    await nodes["run_agent"](state())
    await nodes["run_agent"](state("What is a SIP?"))                            # concept question, goes to finance_qa
    later = await nodes["run_agent"](state("connect sample"))
    assert later["result"].agent == "portfolio" and goal.calls == []


async def test_memory_clear_forgets_the_remembered_goal():
    memory = ConversationMemory()
    memory.set_pending_goal("t1", QUESTION)
    memory.clear("t1")
    assert memory.take_pending_goal("t1") is None


async def test_without_memory_a_not_ready_portfolio_still_just_shows_the_menu(stub_agents):
    folio = StubAgent("portfolio", status="clarify")
    out = await build(stub_agents, folio, goal_stub())["run_agent"](state())
    assert out["result"].agent == "portfolio"
