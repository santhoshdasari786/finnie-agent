"""Slot filling: when an agent asks a question, the user's short answer goes back to THAT agent.

Real case: "can I retire at 50?" -> Finnie asks "How many years...?" -> the user says "10 years, 20000 a month".
That reply has no goal words, so the rules do not fire and the message used to fall through to Q&A.

How it works
  * an agent marks its question: AgentResult(status="clarify", meta={"awaiting": "<agent name>"})
  * ConversationMemory remembers it per thread; ANY later answer from an agent clears it
  * in `route`, an unmatched message that looks like an answer (a number, an amount word, a risk word) is sent
    to the awaiting agent. The classifier is skipped.
  * a message the RULES place elsewhere always wins ("analyze my portfolio", "What is the 80C limit?")

Run:  .venv/bin/python -m pytest tests/workflow/awaiting_test.py -v
"""
import pytest

from src.common.models import QASettings
from src.core.contracts import AgentResult
from src.core.guardrails import Guardrails
from src.workflow.graph import ask, build_graph
from src.workflow.memory import ConversationMemory, looks_like_slot_answer

from tests.conftest import StubAgent

pytestmark = pytest.mark.asyncio

AWAIT = {"awaiting": "goal_planning", "missing": ["horizon_years"]}


def res(status="ok", meta=None, agent="goal_planning"):
    return AgentResult(agent=agent, status=status, text="text", disclaimer="d", meta=meta or {})


# ================================================================ looks_like_slot_answer
@pytest.mark.parametrize("text", [
    "10 years, 20000 a month", "20000", "about 10 years", "50 lakh", "1 crore", "20k monthly", "I'm aggressive",
    "moderate", "10", "for 15 yrs", "5 lakh saved already",
])
async def test_these_look_like_answers(text):
    assert looks_like_slot_answer(text)

@pytest.mark.parametrize("text", [
    "What is a SIP?", "hello", "tell me a joke", "no idea", "", "   ", "why",
    "I have been thinking about this for a long time and honestly I am not sure what to do because there are so "
    "many options and I keep changing my mind about 3 different things every single day",
])
async def test_these_do_not(text):
    assert not looks_like_slot_answer(text)


# ================================================================ the memory
async def test_nothing_is_awaited_at_first():
    assert ConversationMemory().awaiting("t") is None

async def test_a_clarify_with_awaiting_is_remembered():
    m = ConversationMemory()
    m.remember("t", "can I retire at 50?", res("clarify", AWAIT))
    assert m.awaiting("t") == "goal_planning"

async def test_a_normal_answer_clears_it():
    m = ConversationMemory()
    m.remember("t", "q", res("clarify", AWAIT))
    m.remember("t", "10 years", res("ok"))
    assert m.awaiting("t") is None

async def test_a_clarify_without_awaiting_clears_it():
    m = ConversationMemory()
    m.remember("t", "q", res("clarify", AWAIT))
    m.remember("t", "q2", res("clarify", {}, agent="portfolio"))
    assert m.awaiting("t") is None

async def test_a_no_source_answer_clears_it():
    m = ConversationMemory()
    m.remember("t", "q", res("clarify", AWAIT))
    m.remember("t", "q2", res("no_source", agent="finance_qa"))
    assert m.awaiting("t") is None

@pytest.mark.parametrize("status", ["error", "redirect", "needs_login"])
async def test_failures_do_not_change_it(status):
    m = ConversationMemory()
    m.remember("t", "q", res("clarify", AWAIT))
    data = {"login_url": "https://x"} if status == "needs_login" else None
    m.remember("t", "q2", AgentResult(agent="a", status=status, text="t", disclaimer="d", data=data))
    assert m.awaiting("t") == "goal_planning"

async def test_it_is_per_thread():
    m = ConversationMemory()
    m.remember("a", "q", res("clarify", AWAIT))
    assert m.awaiting("b") is None

async def test_clear_forgets_it():
    m = ConversationMemory()
    m.remember("t", "q", res("clarify", AWAIT))
    m.clear("t")
    assert m.awaiting("t") is None

async def test_a_clarify_is_still_stored_in_the_history():
    m = ConversationMemory()
    m.remember("t", "can I retire at 50?", res("clarify", AWAIT))
    assert len(m.history("t")) == 2


# ================================================================ the graph
@pytest.fixture
def settings():
    return QASettings()

@pytest.fixture
def agents(stub_agents):
    stub_agents["goal_planning"] = StubAgent("goal_planning", status="clarify", meta=dict(AWAIT))
    return stub_agents

def app_for(agents, settings, classifier=None):
    mem = ConversationMemory()
    return build_graph(agents, Guardrails(settings), settings, memory=mem, classifier=classifier), mem

class FakeClassifier:
    def __init__(self):
        self.calls = []
    async def classify(self, text):
        self.calls.append(text)
        return None

ANSWER = "10 years, 20000 a month"

async def test_the_answer_goes_back_to_the_agent_that_asked(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, ANSWER, thread_id="t")
    assert r.agent == "goal_planning" and len(agents["goal_planning"].calls) == 2
    assert agents["goal_planning"].calls[1][0] == ANSWER

async def test_the_agent_sees_the_question_it_asked_in_the_history(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, ANSWER, thread_id="t")
    _, ctx = agents["goal_planning"].calls[1]
    assert [t.role for t in ctx.history] == ["user", "assistant"] and ctx.history[0].text == "can I retire at 50?"

async def test_without_the_mark_the_same_answer_goes_to_qa(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", status="ok")       # asked nothing
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, ANSWER, thread_id="t")
    assert r.agent == "finance_qa"

async def test_the_decision_says_why(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    out = await app.ainvoke({"text": ANSWER, "thread_id": "t", "agent": None})
    assert out["decision"].source == "awaiting" and out["decision"].intent == "goal"

async def test_the_classifier_is_not_called_for_an_answer(agents, settings):
    fc = FakeClassifier()
    app, _ = app_for(agents, settings, fc)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, ANSWER, thread_id="t")
    assert fc.calls == []


# ---------------------------------------------------------------- the rules still win
async def test_a_rule_for_another_agent_wins(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, "Analyze my portfolio", thread_id="t")
    assert r.agent == "portfolio"

async def test_a_tax_question_with_a_number_goes_to_tax(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, "What is the 80C limit?", thread_id="t")
    assert r.agent == "tax_education"

async def test_a_concept_question_is_not_taken_as_an_answer(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, "What is a SIP?", thread_id="t")
    assert r.agent == "finance_qa"

async def test_a_hint_still_overrides(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, ANSWER, thread_id="t", agent="market_analysis")
    assert r.agent == "market_analysis"


# ---------------------------------------------------------------- it lasts one answer
async def test_after_the_agent_answers_the_next_message_is_routed_normally(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    agents["goal_planning"].status = "ok"
    await ask(app, ANSWER, thread_id="t")                       # answered, no longer awaiting
    r = await ask(app, "20000", thread_id="t")
    assert r.agent == "finance_qa"

async def test_if_the_agent_asks_again_it_keeps_waiting(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, "10 years", thread_id="t")                   # still clarify, still awaiting
    r = await ask(app, "20000 a month", thread_id="t")
    assert r.agent == "goal_planning" and len(agents["goal_planning"].calls) == 3

async def test_another_thread_is_not_affected(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="a")
    r = await ask(app, ANSWER, thread_id="b")
    assert r.agent == "finance_qa"

async def test_a_blocked_message_is_still_blocked(agents, settings):
    app, _ = app_for(agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, "I want to die", thread_id="t")
    assert r.agent == "guard"

async def test_it_never_sends_an_answer_to_an_unknown_agent(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", status="clarify", meta={"awaiting": "made_up"})
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, ANSWER, thread_id="t")
    assert r.agent == "finance_qa"

async def test_the_graph_without_memory_ignores_all_this(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", status="clarify", meta=dict(AWAIT))
    app = build_graph(stub_agents, Guardrails(settings), settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    assert (await ask(app, ANSWER, thread_id="t")).agent == "finance_qa"
