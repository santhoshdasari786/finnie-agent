"""Two agents, one answer: a goal question that also says "my portfolio".

The router already reports both intents ("goal" first, "portfolio" as a secondary intent). Here the portfolio agent runs
first and the goal agent then plans from the portfolio's value. Each agent keeps its own job: the portfolio agent prices
and totals the holdings, the goal agent does the projection in code. This module only passes one agent's number to the other
and says so in a line of its own, written by code, never by a model.

If the portfolio is not ready (not connected, login needed, no holdings, error) that reply is returned as it is: a
projection from a balance that was not read would be a made-up number.
"""
import logging

from src.core.contracts import AgentContext, AgentResult

log = logging.getLogger(__name__)

PORTFOLIO_QUERY = "Analyze my portfolio"


def wants_portfolio_and_goal(decision, agents: dict) -> bool:
    return (decision.intent == "goal" and "portfolio" in decision.secondary_intents
            and agents.get("portfolio") is not None and agents.get("goal_planning") is not None)


def _total_value(result: AgentResult) -> float | None:
    value = ((result.data or {}).get("metrics") or {}).get("total_value")
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else None


def _inr(x: float) -> str:
    return f"₹{x:,.0f}"


async def _plan_from(planner, query: str, ctx: AgentContext, total: float) -> AgentResult:
    plan = await planner.run(query, ctx.model_copy(update={"slots": {**ctx.slots, "starting_balance": total}}))
    used = plan.status == "clarify" or ((plan.data or {}).get("plan") or {}).get("start") == total
    if plan.status not in ("ok", "clarify") or not used:
        return plan                                     # the user gave their own balance, or the plan failed: say nothing extra
    note = (f"I'm using your portfolio's current value, {_inr(total)}, as the starting balance, "
            "and assuming it stays invested toward this goal.")
    meta = {**plan.meta, "collaboration": {"agents": ["portfolio", "goal_planning"], "starting_balance": total}}
    return plan.model_copy(update={"text": f"{note}\n\n{plan.text}", "meta": meta})


async def goal_from_portfolio(agents: dict, query: str, ctx: AgentContext, memory=None) -> AgentResult:
    """Portfolio first, then the goal plan. If the portfolio is not ready, show that and, when there is a memory,
    keep the goal question so it is answered once the portfolio connects (see goal_after_connect)."""
    try:
        held = await agents["portfolio"].run(PORTFOLIO_QUERY, ctx.model_copy(update={"slots": {}}))
    except Exception:
        log.exception("portfolio step of a goal question failed; planning without it")
        return await agents["goal_planning"].run(query, ctx)
    total = _total_value(held) if held.status == "ok" else None
    if total is None:
        if memory is not None and held.status in ("clarify", "needs_login"):
            memory.set_pending_goal(ctx.thread_id, query)
        return held                                     # connect first / log in / empty: show that, plan nothing
    return await _plan_from(agents["goal_planning"], query, ctx, total)


async def goal_after_connect(agents: dict, question: str, ctx: AgentContext, held: AgentResult) -> AgentResult | None:
    """The user connected a portfolio after asking a goal question: answer the goal question now, from that portfolio.
    None when the portfolio result has no value to start from."""
    total = _total_value(held) if held.status == "ok" else None
    if total is None:
        return None
    return await _plan_from(agents["goal_planning"], question, ctx, total)
