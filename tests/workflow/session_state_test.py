"""Memory v2: the session remembers FACTS, not just text.

Run:  .venv/bin/python -m pytest tests/workflow/session_state_test.py -v

Contract (agents -> memory)
  AgentResult.meta["learned"] = {"profile": {...}, "slots": {...}, "slots_reset": True}
      profile      fields of UserProfile the user told us (risk_appetite, ...). Saved for the whole thread.
      slots        this agent's working facts (a goal's target, horizon, monthly amount...). Saved per (thread, agent).
      slots_reset  forget this agent's slots first, then apply the new ones.
  AgentResult.meta["summary"]   a short line stored in history instead of the full answer text.

Contract (memory -> agents)
  AgentContext.profile   the saved profile, for EVERY agent
  AgentContext.slots     the saved slots of THE agent being run, never another agent's

Why: a transcript forgets numbers (answers are cut), and the LLM has to re-derive them every turn.
"""
import pytest

from src.common.models import QASettings
from src.core.contracts import AgentContext, AgentResult, UserProfile
from src.core.guardrails import Guardrails
from src.workflow.graph import ask, build_graph
from src.workflow.memory import ConversationMemory

from tests.conftest import StubAgent

pytestmark = pytest.mark.asyncio


def res(agent="goal_planning", status="ok", text="text", **meta):
    return AgentResult(agent=agent, status=status, text=text, disclaimer="d", meta=meta)

def learned(profile=None, slots=None, reset=False):
    out = {}
    if profile is not None:
        out["profile"] = profile
    if slots is not None:
        out["slots"] = slots
    if reset:
        out["slots_reset"] = True
    return {"learned": out}


# ================================================================ AgentContext
async def test_the_context_carries_slots_and_defaults_to_none():
    assert AgentContext(thread_id="t").slots == {}
    assert AgentContext(thread_id="t", slots={"a": 1}).slots == {"a": 1}


# ================================================================ the profile
async def test_a_new_thread_has_the_default_profile():
    assert ConversationMemory().profile("t") == UserProfile()

async def test_a_learned_profile_field_is_saved():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "aggressive", "risk_source": "stated"})))
    p = m.profile("t")
    assert p.risk_appetite == "aggressive" and p.risk_source == "stated"

async def test_other_profile_fields_are_untouched():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "aggressive"})))
    assert m.profile("t").currency == "INR" and m.profile("t").jurisdiction == "india"

async def test_a_later_update_keeps_earlier_fields():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "aggressive"})))
    m.remember("t", "q", res(**learned(profile={"knowledge_level": "advanced"})))
    assert m.profile("t").risk_appetite == "aggressive" and m.profile("t").knowledge_level == "advanced"

async def test_a_later_update_overrides_the_same_field():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "aggressive"})))
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "conservative"})))
    assert m.profile("t").risk_appetite == "conservative"

async def test_none_values_do_not_erase_a_saved_field():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "aggressive"})))
    m.remember("t", "q", res(**learned(profile={"risk_appetite": None})))
    assert m.profile("t").risk_appetite == "aggressive"

async def test_an_invalid_profile_update_is_ignored_entirely():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "reckless", "knowledge_level": "advanced"})))
    assert m.profile("t") == UserProfile()

async def test_the_profile_is_per_thread():
    m = ConversationMemory()
    m.remember("a", "q", res(**learned(profile={"risk_appetite": "aggressive"})))
    assert m.profile("b").risk_appetite is None

async def test_profile_returns_a_copy():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "aggressive"})))
    m.profile("t").risk_appetite = "conservative"
    assert m.profile("t").risk_appetite == "aggressive"


# ================================================================ slots
async def test_a_new_thread_has_no_slots():
    assert ConversationMemory().slots("t", "goal_planning") == {}

async def test_learned_slots_are_saved_for_that_agent():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(slots={"monthly_contribution": 20000, "horizon_years": 10})))
    assert m.slots("t", "goal_planning") == {"monthly_contribution": 20000, "horizon_years": 10}

async def test_slots_merge_across_turns():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(slots={"a": 1})))
    m.remember("t", "q", res(**learned(slots={"b": 2})))
    assert m.slots("t", "goal_planning") == {"a": 1, "b": 2}

async def test_a_new_value_overrides_an_old_one():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(slots={"a": 1})))
    m.remember("t", "q", res(**learned(slots={"a": 3})))
    assert m.slots("t", "goal_planning") == {"a": 3}

async def test_none_slot_values_are_not_stored():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(slots={"a": 1, "b": None})))
    assert m.slots("t", "goal_planning") == {"a": 1}

async def test_slots_belong_to_the_agent_that_learned_them():
    m = ConversationMemory()
    m.remember("t", "q", res(agent="goal_planning", **learned(slots={"a": 1})))
    assert m.slots("t", "portfolio") == {}

async def test_slots_are_per_thread():
    m = ConversationMemory()
    m.remember("a", "q", res(**learned(slots={"a": 1})))
    assert m.slots("b", "goal_planning") == {}

async def test_slots_return_a_copy():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(slots={"a": 1})))
    m.slots("t", "goal_planning")["a"] = 99
    assert m.slots("t", "goal_planning") == {"a": 1}

async def test_a_reset_forgets_old_slots_then_applies_the_new_ones():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(slots={"a": 1, "b": 2})))
    m.remember("t", "q", res(**learned(slots={"c": 3}, reset=True)))
    assert m.slots("t", "goal_planning") == {"c": 3}

async def test_a_bare_reset_just_forgets():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(slots={"a": 1})))
    m.remember("t", "q", res(**learned(reset=True)))
    assert m.slots("t", "goal_planning") == {}

async def test_a_reset_does_not_touch_the_profile():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "aggressive"}, slots={"a": 1})))
    m.remember("t", "q", res(**learned(reset=True)))
    assert m.profile("t").risk_appetite == "aggressive"

async def test_a_clarify_still_saves_what_it_learned():
    m = ConversationMemory()
    m.remember("t", "q", res(status="clarify", **learned(slots={"monthly_contribution": 20000})))
    assert m.slots("t", "goal_planning") == {"monthly_contribution": 20000}

async def test_no_source_results_can_learn_too():
    m = ConversationMemory()
    m.remember("t", "q", res(status="no_source", **learned(slots={"a": 1})))
    assert m.slots("t", "goal_planning") == {"a": 1}

@pytest.mark.parametrize("status", ["error", "redirect", "needs_login"])
async def test_failures_learn_nothing(status):
    m = ConversationMemory()
    data = {"login_url": "https://x"} if status == "needs_login" else None
    r = AgentResult(agent="goal_planning", status=status, text="t", disclaimer="d", data=data,
                    meta=learned(slots={"a": 1}, profile={"risk_appetite": "aggressive"}))
    m.remember("t", "q", r)
    assert m.slots("t", "goal_planning") == {} and m.profile("t").risk_appetite is None

@pytest.mark.parametrize("junk", ["text", 5, ["a"], None, {"slots": "nope"}, {"profile": [1]}, {"slots": [1]}])
async def test_malformed_learned_data_is_ignored(junk):
    m = ConversationMemory()
    m.remember("t", "q", res(learned=junk))
    assert m.slots("t", "goal_planning") == {} and m.profile("t") == UserProfile()
    assert len(m.history("t")) == 2                               # the turn itself is still remembered

async def test_clear_forgets_profile_and_slots_too():
    m = ConversationMemory()
    m.remember("t", "q", res(**learned(profile={"risk_appetite": "aggressive"}, slots={"a": 1})))
    m.clear("t")
    assert m.profile("t") == UserProfile() and m.slots("t", "goal_planning") == {}

async def test_clear_leaves_other_threads_alone():
    m = ConversationMemory()
    m.remember("a", "q", res(**learned(slots={"a": 1})))
    m.remember("b", "q", res(**learned(slots={"b": 2})))
    m.clear("a")
    assert m.slots("b", "goal_planning") == {"b": 2}


# ================================================================ summaries in history
async def test_a_summary_replaces_the_long_answer_in_history():
    m = ConversationMemory()
    m.remember("t", "q", res(text="very long answer " * 50, summary="Goal: ₹5,000,000 in 10 years"))
    assert m.history("t")[1].text == "Goal: ₹5,000,000 in 10 years"

async def test_without_a_summary_the_text_is_used():
    m = ConversationMemory()
    m.remember("t", "q", res(text="the answer"))
    assert m.history("t")[1].text == "the answer"

async def test_a_blank_summary_falls_back_to_the_text():
    m = ConversationMemory()
    m.remember("t", "q", res(text="the answer", summary="   "))
    assert m.history("t")[1].text == "the answer"

async def test_a_summary_is_cut_like_any_text():
    m = ConversationMemory(max_chars=10)
    m.remember("t", "q", res(summary="s" * 100))
    assert len(m.history("t")[1].text) == 10


# ================================================================ in the graph
@pytest.fixture
def settings():
    return QASettings()

def app_for(agents, settings):
    mem = ConversationMemory()
    return build_graph(agents, Guardrails(settings), settings, memory=mem), mem

async def test_a_profile_learned_by_one_agent_reaches_another(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", meta=learned(profile={"risk_appetite": "aggressive"}))
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, "Analyze my portfolio", thread_id="t")
    _, ctx = stub_agents["portfolio"].calls[0]
    assert ctx.profile.risk_appetite == "aggressive"

async def test_slots_come_back_to_the_agent_that_learned_them(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", meta=learned(slots={"monthly_contribution": 30000}))
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, "can I retire at 50?", thread_id="t")
    assert stub_agents["goal_planning"].calls[0][1].slots == {}
    assert stub_agents["goal_planning"].calls[1][1].slots == {"monthly_contribution": 30000}

async def test_other_agents_never_see_them(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", meta=learned(slots={"monthly_contribution": 30000}))
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, "Analyze my portfolio", thread_id="t")
    assert stub_agents["portfolio"].calls[0][1].slots == {}

async def test_another_thread_starts_fresh(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", meta=learned(
        profile={"risk_appetite": "aggressive"}, slots={"monthly_contribution": 30000}))
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="a")
    await ask(app, "can I retire at 50?", thread_id="b")
    ctx = stub_agents["goal_planning"].calls[1][1]
    assert ctx.slots == {} and ctx.profile.risk_appetite is None

async def test_a_blocked_message_learns_nothing(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", meta=learned(slots={"a": 1}))
    app, mem = app_for(stub_agents, settings)
    await ask(app, "I want to die", thread_id="t")
    assert mem.slots("t", "goal_planning") == {}

async def test_the_graph_without_memory_gives_agents_empty_state(stub_agents, settings):
    app = build_graph(stub_agents, Guardrails(settings), settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    ctx = stub_agents["goal_planning"].calls[0][1]
    assert ctx.slots == {} and ctx.profile == UserProfile()

async def test_the_history_the_agent_sees_uses_the_summary(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", text="long " * 100, meta={"summary": "short summary"})
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, "can I retire at 50?", thread_id="t")
    assert stub_agents["goal_planning"].calls[1][1].history[1].text == "short summary"


# ================================================================ the router saves a stated risk appetite itself
async def test_a_stated_risk_is_saved_without_calling_any_agent(stub_agents, settings):
    app, mem = app_for(stub_agents, settings)
    r = await ask(app, "I'm an aggressive investor", thread_id="t")
    assert r.agent == "router" and r.status == "ok" and "aggressive" in r.text.lower()
    assert mem.profile("t").risk_appetite == "aggressive" and mem.profile("t").risk_source == "stated"
    assert not [n for n, a in stub_agents.items() if a.calls]

async def test_the_saved_risk_reaches_the_next_agent(stub_agents, settings):
    app, _ = app_for(stub_agents, settings)
    await ask(app, "I'm a conservative investor", thread_id="t")
    await ask(app, "can I retire at 50?", thread_id="t")
    assert stub_agents["goal_planning"].calls[0][1].profile.risk_appetite == "conservative"

async def test_a_later_statement_replaces_the_earlier_one(stub_agents, settings):
    app, mem = app_for(stub_agents, settings)
    await ask(app, "I'm an aggressive investor", thread_id="t")
    await ask(app, "my risk appetite is conservative", thread_id="t")
    assert mem.profile("t").risk_appetite == "conservative"

async def test_the_confirmation_says_what_it_will_be_used_for(stub_agents, settings):
    app, _ = app_for(stub_agents, settings)
    r = await ask(app, "I'm an aggressive investor", thread_id="t")
    assert "projection" in r.text.lower() or "portfolio" in r.text.lower()

async def test_the_statement_is_kept_in_the_history(stub_agents, settings):
    app, mem = app_for(stub_agents, settings)
    await ask(app, "I'm an aggressive investor", thread_id="t")
    assert len(mem.history("t")) == 2

async def test_a_risk_statement_does_not_break_a_pending_question(stub_agents, settings):
    stub_agents["goal_planning"] = StubAgent("goal_planning", status="clarify", meta={"awaiting": "goal_planning"})
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, "I'm aggressive", thread_id="t")
    r = await ask(app, "10 years, 20000 a month", thread_id="t")
    assert r.agent == "goal_planning" and len(stub_agents["goal_planning"].calls) == 2

async def test_the_router_result_never_clears_an_awaited_agent():
    m = ConversationMemory()
    m.remember("t", "q", AgentResult(agent="goal_planning", status="clarify", text="t", disclaimer="d",
                                     meta={"awaiting": "goal_planning"}))
    m.remember("t", "q2", AgentResult(agent="router", status="ok", text="t", disclaimer="d"))
    assert m.awaiting("t") == "goal_planning"

async def test_a_router_clarify_does_not_clear_it_either():
    m = ConversationMemory()
    m.remember("t", "q", AgentResult(agent="goal_planning", status="clarify", text="t", disclaimer="d",
                                     meta={"awaiting": "goal_planning"}))
    m.remember("t", "q2", AgentResult(agent="router", status="clarify", text="t", disclaimer="d"))
    assert m.awaiting("t") == "goal_planning"


@pytest.mark.parametrize("text, phrase", [("I'm an aggressive investor", "an aggressive investor"),
                                          ("I'm a conservative investor", "a conservative investor"),
                                          ("I'm moderate", "a moderate investor")])
async def test_the_confirmation_uses_the_right_article(stub_agents, settings, text, phrase):
    app, _ = app_for(stub_agents, settings)
    assert phrase in (await ask(app, text, thread_id="t")).text


# ================================================================ last agent, and re-running the goal after a change of risk
async def test_the_last_agent_is_remembered():
    m = ConversationMemory()
    assert m.last_agent("t") is None
    m.remember("t", "q", res(agent="goal_planning"))
    assert m.last_agent("t") == "goal_planning"

async def test_the_routers_replies_do_not_change_it():
    m = ConversationMemory()
    m.remember("t", "q", res(agent="goal_planning"))
    m.remember("t", "q", res(agent="router"))
    assert m.last_agent("t") == "goal_planning"

async def test_failures_do_not_change_it():
    m = ConversationMemory()
    m.remember("t", "q", res(agent="goal_planning"))
    m.remember("t", "q", AgentResult(agent="portfolio", status="error", text="t", disclaimer="d"))
    assert m.last_agent("t") == "goal_planning"

async def test_last_agent_is_per_thread_and_cleared():
    m = ConversationMemory()
    m.remember("a", "q", res(agent="goal_planning"))
    assert m.last_agent("b") is None
    m.clear("a")
    assert m.last_agent("a") is None


def goal_stub(**kw):
    return StubAgent("goal_planning", meta=learned(slots={"monthly_contribution": 20000, "horizon_years": 10}), **kw)

async def test_a_risk_word_after_a_goal_answer_recalculates_it(stub_agents, settings):
    stub_agents["goal_planning"] = goal_stub()
    app, mem = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, "aggressive", thread_id="t")
    assert r.agent == "goal_planning" and len(stub_agents["goal_planning"].calls) == 2
    assert "aggressive" in r.text.lower() and r.text.lower().startswith("updated")
    _, ctx = stub_agents["goal_planning"].calls[1]
    assert ctx.profile.risk_appetite == "aggressive" and ctx.slots == {"monthly_contribution": 20000, "horizon_years": 10}
    assert mem.profile("t").risk_appetite == "aggressive" and mem.profile("t").risk_source == "stated"

async def test_the_recalculation_keeps_the_agents_own_facts(stub_agents, settings):
    stub_agents["goal_planning"] = goal_stub()
    app, mem = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, "aggressive", thread_id="t")
    assert mem.slots("t", "goal_planning") == {"monthly_contribution": 20000, "horizon_years": 10}

async def test_it_is_not_recalculated_when_the_last_agent_was_another_one(stub_agents, settings):
    stub_agents["goal_planning"] = goal_stub()
    app, mem = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, "Analyze my portfolio", thread_id="t")
    r = await ask(app, "aggressive", thread_id="t")
    assert r.agent == "router" and len(stub_agents["goal_planning"].calls) == 1
    assert mem.profile("t").risk_appetite == "aggressive"

async def test_it_is_not_recalculated_without_a_goal_to_recalculate(stub_agents, settings):
    app, mem = app_for(stub_agents, settings)
    r = await ask(app, "aggressive", thread_id="t")
    assert r.agent == "router" and not stub_agents["goal_planning"].calls
    assert mem.profile("t").risk_appetite == "aggressive"

async def test_a_goal_that_cannot_be_recalculated_still_saves_the_preference(stub_agents, settings):
    stub_agents["goal_planning"] = goal_stub()
    app, mem = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    stub_agents["goal_planning"].status = "clarify"
    r = await ask(app, "aggressive", thread_id="t")
    assert r.agent == "router" and r.status == "ok" and mem.profile("t").risk_appetite == "aggressive"

async def test_a_crashing_goal_agent_does_not_lose_the_preference(stub_agents, settings):
    stub_agents["goal_planning"] = goal_stub()
    app, mem = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    stub_agents["goal_planning"].raises = RuntimeError("boom")
    r = await ask(app, "aggressive", thread_id="t")
    assert r.agent == "router" and r.status == "ok" and "boom" not in r.text
    assert mem.profile("t").risk_appetite == "aggressive"

async def test_repeating_the_word_recalculates_again(stub_agents, settings):
    stub_agents["goal_planning"] = goal_stub()
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    await ask(app, "aggressive", thread_id="t")
    r = await ask(app, "conservative", thread_id="t")
    assert r.agent == "goal_planning" and stub_agents["goal_planning"].calls[2][1].profile.risk_appetite == "conservative"


async def test_the_update_line_has_no_article_to_get_wrong(stub_agents, settings):
    stub_agents["goal_planning"] = goal_stub()
    app, _ = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    for word in ("aggressive", "conservative", "moderate"):
        r = await ask(app, word, thread_id="t")
        assert f"risk appetite is now {word}" in r.text and " a aggressive" not in r.text

async def test_another_agent_with_saved_facts_is_not_recalculated(stub_agents, settings):
    stub_agents["portfolio"] = StubAgent("portfolio", meta=learned(slots={"something": 1}))
    app, mem = app_for(stub_agents, settings)
    await ask(app, "Analyze my portfolio", thread_id="t")
    r = await ask(app, "aggressive", thread_id="t")
    assert r.agent == "router" and len(stub_agents["portfolio"].calls) == 1
    assert mem.profile("t").risk_appetite == "aggressive"

async def test_the_recalculated_result_still_saves_the_new_risk(stub_agents, settings):
    stub_agents["goal_planning"] = goal_stub()
    app, mem = app_for(stub_agents, settings)
    await ask(app, "can I retire at 50?", thread_id="t")
    r = await ask(app, "aggressive", thread_id="t")
    assert r.meta["learned"]["profile"] == {"risk_appetite": "aggressive", "risk_source": "stated"}
    assert r.meta["learned"]["slots"] == {"monthly_contribution": 20000, "horizon_years": 10}
