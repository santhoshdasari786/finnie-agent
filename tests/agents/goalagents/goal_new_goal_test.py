"""A message that says "new goal" AND gives numbers starts a fresh goal and plans it in the same turn.

Run:  .venv/bin/python -m pytest tests/agents/goalagents/goal_new_goal_test.py -v

Why: the Goals tab and the MCP plan_goal tool send a complete, self-contained statement. Without this, numbers remembered from an
earlier goal (a horizon, a target, a starting balance) leaked into it ("10 years (from earlier)").

Contract
  * "new goal" / "start over" / "reset" / "forget my numbers" WITH numbers: remembered numbers are ignored, the new goal is planned
    in this turn, and meta.learned.slots_reset tells memory to drop the old ones
  * the same phrases WITHOUT numbers still only clear (existing behaviour)
  * a message without those phrases still carries earlier numbers forward (follow-ups like "what if I save more?")
"""
import pytest

from tests.agents.goalagents.goal_planning_agent_test import FULL, ctx, make

pytestmark = pytest.mark.asyncio

OLD = {"target_amount": 10_000_000, "horizon_years": 5, "starting_balance": 100_000, "monthly_contribution": 1000}
Q = "New goal: Can I reach 5000000 rupees in 10 years, saving 20000 rupees a month?"


async def test_old_numbers_do_not_leak_into_a_new_goal():
    agent, _, _ = make(**FULL)
    result = await agent.run(Q, ctx(slots=OLD))
    plan = result.data["plan"]
    assert result.status == "ok"
    assert (plan["target"], plan["years"], plan["monthly"], plan["start"]) == (5_000_000, 10, 20_000, 0)
    assert "from earlier" not in result.text


async def test_the_old_horizon_does_not_stop_a_how_long_question():
    agent, _, _ = make(target_amount=5_000_000, monthly_contribution=20_000)            # no years in the new message
    result = await agent.run("New goal: How long will it take to reach 5000000 rupees, saving 20000 rupees a month?", ctx(slots=OLD))
    assert result.status == "ok" and result.data["plan"]["years"] is None and "paths" not in result.data


async def test_memory_is_told_to_drop_the_old_numbers_and_keep_the_new():
    agent, _, _ = make(**FULL)
    learned = (await agent.run(Q, ctx(slots=OLD))).meta["learned"]
    assert learned["slots_reset"] is True
    assert learned["slots"] == {"target_amount": 5_000_000, "horizon_years": 10, "monthly_contribution": 20_000}


async def test_a_question_back_also_drops_the_old_numbers():
    agent, _, _ = make(monthly_contribution=20_000)                                      # years missing: the agent has to ask
    result = await agent.run("Start over: I can save 20000 a month", ctx(slots=OLD))
    assert result.status == "clarify" and "horizon_years" in result.meta["missing"]
    assert result.meta["learned"]["slots_reset"] is True
    assert result.meta["learned"]["slots"] == {"monthly_contribution": 20_000}           # not the old target or horizon


@pytest.mark.parametrize("phrase", ["start over", "Start again", "reset", "new goal", "forget my numbers"])
async def test_every_reset_phrase_works_with_numbers(phrase):
    agent, _, _ = make(**FULL)
    result = await agent.run(f"{phrase}: can I reach 50 lakh in 10 years saving 20000 a month?", ctx(slots=OLD))
    assert result.status == "ok" and result.data["plan"]["start"] == 0 and result.meta["learned"]["slots_reset"] is True


async def test_without_numbers_it_still_only_clears():
    agent, extractor, _ = make(**FULL)
    result = await agent.run("new goal please", ctx(slots=OLD))
    assert result.status == "clarify" and result.meta["learned"] == {"slots_reset": True}
    assert extractor.calls == []


async def test_a_follow_up_without_the_phrase_still_carries_numbers_forward():
    agent, _, _ = make(monthly_contribution=30_000)
    result = await agent.run("what if I save 30000 a month?", ctx(slots=OLD))
    assert result.data["plan"]["target"] == 10_000_000 and result.data["plan"]["years"] == 5
    assert "slots_reset" not in result.meta["learned"]


async def test_a_failed_extraction_does_not_wipe_memory():
    agent, extractor, _ = make(**FULL)
    extractor.error = RuntimeError("model down")
    result = await agent.run(Q, ctx(slots=OLD))
    assert result.status == "error" and "slots_reset" not in (result.meta.get("learned") or {})


async def test_the_word_reset_inside_another_word_is_not_a_reset():
    agent, _, _ = make(monthly_contribution=30_000)
    result = await agent.run("what about the presets, saving 30000 a month?", ctx(slots=OLD))
    assert "slots_reset" not in (result.meta.get("learned") or {})
