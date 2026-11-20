import re
import asyncio
import logging
import logging
from src.common.models import QASettings
from src.core.contracts import AgentContext, AgentResult, UserProfile
from src.workflow.router import route_by_rules
from src.workflow.state import AGENT_NAMES, INTENT_TO_AGENT, GraphState, RoutingDecision
from src.workflow.classifier import CLARIFY_REPLY, OFF_TOPIC_REPLY, needs_classifier
from src.workflow.memory import looks_like_slot_answer
from src.workflow.compose import goal_after_connect, goal_from_portfolio, wants_portfolio_and_goal


log = logging.getLogger(__name__)
RERUN_AFTER_PROFILE = {"goal_planning"}      # agents whose last answer is recalculated when the risk appetite changes
_AGENT_TO_INTENT = {agent: intent for intent, agent in INTENT_TO_AGENT.items()}

def make_nodes(agents: dict, guardrails, settings: QASettings, memory=None,
               classifier=None, classifier_timeout: float = 8.0):
    
    def _error(agent: str, text: str) -> AgentResult:
        return AgentResult(agent=agent, status="error", text=text, disclaimer=settings.disclaimer)
    
    async def input_guard(state: GraphState) -> dict:
        return {"guard": guardrails.check(state["text"])}

    async def contextualize(state: GraphState) -> dict:
        text = " ".join(state["text"].split())
        if memory is None:
            return {"standalone": text, "history": [], "profile": UserProfile()}
        return {"standalone": await memory.standalone(state["thread_id"], text),
                "history": memory.history(state["thread_id"]),
                "profile": memory.profile(state["thread_id"])}


    async def route(state: GraphState) -> dict:
        text, hint = " ".join((state.get("standalone") or state["text"]).split()), state.get("agent")

        if hint:
            if hint not in AGENT_NAMES:
                raise ValueError(f"unknown agent {hint!r}")
            return {"decision": RoutingDecision(intent=_AGENT_TO_INTENT[hint], confidence=1.0,
                                                source="hint", normalized_question=text)}
        decision = route_by_rules(text)
        awaiting = memory.awaiting(state["thread_id"]) if memory else None
        if decision is None and awaiting in AGENT_NAMES and looks_like_slot_answer(text):
            decision = RoutingDecision(intent=_AGENT_TO_INTENT[awaiting], confidence=0.9, source="awaiting",
                                       normalized_question=text)

        if decision is None and classifier is not None and needs_classifier(text):
            try:
                decision = await asyncio.wait_for(classifier.classify(text), classifier_timeout)
            except Exception:
                log.exception("classifier failed or timed out; falling back")
        decision = decision or RoutingDecision(
            intent="concept_qa", confidence=0.5, source="fallback", normalized_question=text)
        log.info("route: %r -> %s (%s, %.2f)", text, decision.intent, decision.source, decision.confidence)
        return {"decision": decision}

    async def recalculate_after_profile(state, guard, fact: dict, level: str):
        """After a risk change, re-run the goal agent on its saved facts. Returns its AgentResult, or None to skip."""
        thread = state["thread_id"]
        last = memory.last_agent(thread) if memory else None
        if last not in RERUN_AFTER_PROFILE or agents.get(last) is None:
            return None
        slots = memory.slots(thread, last)
        if not slots:
            return None
        ctx = AgentContext(thread_id=thread, profile=(state.get("profile") or UserProfile()).model_copy(update=fact),
                           flags=guard.flags, history=state.get("history") or [], slots=slots)
        try:
            redo = await agents[last].run("Recalculate with my updated risk appetite", ctx)
        except Exception:
            log.exception("recalculating after a profile change failed")
            return None
        if redo.status != "ok":
            return None
        meta = {**redo.meta, "learned": {**redo.meta.get("learned", {}), "profile": fact}}
        return redo.model_copy(update={"text": f"Updated: risk appetite is now {level}.\n\n{redo.text}", "meta": meta})


    async def run_agent(state: GraphState) -> dict:
        decision, guard = state["decision"], state["guard"]
        if decision.intent == "off_topic":
            return {"result": AgentResult(agent="router", status="redirect", text=OFF_TOPIC_REPLY,
                                          disclaimer=settings.disclaimer)}
        if decision.intent == "clarify":
            return {"result": AgentResult(agent="router", status="clarify",
                                          text=decision.clarification or CLARIFY_REPLY,
                                          disclaimer=settings.disclaimer)}

        if decision.intent == "profile":
            m = re.search(r"\b(conservative|moderate|aggressive)\b", decision.normalized_question, re.I)
            if not m:
                return {"result": AgentResult(agent="router", status="clarify", text=CLARIFY_REPLY,
                                              disclaimer=settings.disclaimer)}
            level = m.group(1).lower()
            fact = {"risk_appetite": level, "risk_source": "stated"}
            recalculated = await recalculate_after_profile(state, guard, fact, level)
            if recalculated is not None:
                return {"result": recalculated}
            return {"result": AgentResult(
                agent="router", status="ok", disclaimer=settings.disclaimer,
                text=(f"Got it: I'll treat you as {'an' if level[0] in 'aeiou' else 'a'} {level} investor in projections "
                      "and portfolio comparisons. Tell me any time if that changes."),
                meta={"learned": {"profile": fact}})}


        name = INTENT_TO_AGENT.get(decision.intent)
        agent = agents.get(name)
        if agent is None:
            return {"result": _error(name or decision.intent, "That part of the assistant isn't available yet.")}
        ctx = AgentContext(thread_id=state["thread_id"], profile=state.get("profile") or UserProfile(),
                           flags=guard.flags, history=state.get("history") or [],
                           slots=memory.slots(state["thread_id"], name) if memory else {})
        try:
            if wants_portfolio_and_goal(decision, agents):
                return {"result": await goal_from_portfolio(agents, decision.normalized_question, ctx, memory)}
            if memory is not None and decision.intent != "portfolio":
                memory.take_pending_goal(state["thread_id"])        # the user moved on: forget the waiting goal question
            result = await agent.run(decision.normalized_question, ctx)
            if memory is not None and decision.intent == "portfolio" and result.status == "ok" and (result.data or {}).get("metrics") and agents.get("goal_planning"):
                waiting = memory.take_pending_goal(state["thread_id"])
                if waiting:
                    goal_ctx = ctx.model_copy(update={"slots": memory.slots(state["thread_id"], "goal_planning")})
                    answered = await goal_after_connect(agents, waiting, goal_ctx, result)
                    if answered is not None:
                        return {"result": answered}
            return {"result": result}
        except Exception:
            log.exception("agent %s failed", name)
            return {"result": _error(name, settings.error_message)}

    async def remember(state: GraphState) -> dict:
        if memory is not None:
            memory.remember(state["thread_id"], state.get("standalone") or state["text"], state["result"])
        return {}

    async def respond_blocked(state: GraphState) -> dict:
        g = state["guard"]
        return {"result": AgentResult(agent="guard", status="redirect", text=g.reply,
                                      meta={"category": g.category}, disclaimer=settings.disclaimer)}

    async def output_guard(state: GraphState) -> dict:
        r = state["result"]
        return {"result": r.model_copy(update={"text": guardrails.finalize(r.text, state["guard"])})}

    return {"input_guard": input_guard, "contextualize": contextualize, "remember": remember,
            "route": route, "run_agent": run_agent,
            "respond_blocked": respond_blocked, "output_guard": output_guard}  # name -> node, so graph.py can register them in a loop

