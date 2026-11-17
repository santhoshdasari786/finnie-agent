"""The goal agent hands the chart its data: data["paths"], computed by goal_math, never by the model or the browser.

Run:  .venv/bin/python -m pytest tests/agents/goalagents/goal_paths_test.py -v

Contract
  data["paths"] = [{"name", "annual_rate_pct", "points": [{"year", "value"}, ...]}]   one per scenario
  * present only when the horizon is known (not when the question is "how long will it take")
  * the last point of each path is that scenario's projected amount, so the chart and the table can never disagree
"""
import pytest

from tests.agents.goalagents.goal_planning_agent_test import FULL, Q, ctx, make

pytestmark = pytest.mark.asyncio


async def test_every_scenario_has_a_path():
    agent, _, _ = make(**FULL)
    data = (await agent.run(Q, ctx())).data
    assert [p["name"] for p in data["paths"]] == [s["name"] for s in data["plan"]["scenarios"]]
    assert [p["annual_rate_pct"] for p in data["paths"]] == [s["annual_rate_pct"] for s in data["plan"]["scenarios"]]


async def test_a_path_starts_at_year_zero_and_has_a_point_per_year():
    agent, _, _ = make(**FULL)
    path = (await agent.run(Q, ctx())).data["paths"][0]["points"]
    assert [p["year"] for p in path] == list(range(11))
    assert path[0] == {"year": 0, "value": 0}


async def test_the_last_point_equals_the_projection_in_the_table():
    agent, _, _ = make(**FULL)
    data = (await agent.run(Q, ctx())).data
    for path, scenario in zip(data["paths"], data["plan"]["scenarios"]):
        assert path["points"][-1]["value"] == pytest.approx(scenario["projected"], rel=1e-9)
        assert path["points"][-1]["year"] == 10


async def test_the_starting_balance_is_the_first_value():
    agent, _, _ = make(starting_balance=100_000, **FULL)
    assert (await agent.run(Q, ctx())).data["paths"][0]["points"][0]["value"] == 100_000


async def test_a_user_rate_gives_one_path():
    agent, _, _ = make(annual_return_pct=12, **FULL)
    data = (await agent.run("Assume 12% returns. " + Q, ctx())).data
    assert [p["name"] for p in data["paths"]] == ["your rate"]
    assert data["paths"][0]["annual_rate_pct"] == 12


async def test_a_question_about_time_has_no_paths():
    agent, _, _ = make(target_amount=5_000_000, monthly_contribution=20_000)       # no horizon: solve for the years
    result = await agent.run("How long to reach 50 lakh saving 20000 a month?", ctx())
    assert result.status == "ok" and "paths" not in result.data


async def test_a_clarifying_question_has_no_data_at_all():
    agent, _, _ = make(target_amount=5_000_000)
    result = await agent.run("I want 50 lakh", ctx())
    assert result.status == "clarify" and not (result.data or {}).get("paths")
