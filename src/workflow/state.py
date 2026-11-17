from typing import Literal, TypedDict, get_args
from pydantic import BaseModel, Field

from src.common.models import GuardVerdict
from src.core.contracts import AgentResult, Turn, UserProfile


AgentName = Literal["finance_qa", "tax_education", "portfolio",
                    "market_analysis", "goal_planning", "news_synthesizer"]
AGENT_NAMES: frozenset[str] = frozenset(get_args(AgentName))

Intent = Literal["concept_qa", "tax", "portfolio", "market", "goal", "news",
                 "profile", "clarify", "off_topic"]

INTENT_TO_AGENT: dict[str, AgentName] = {
    "concept_qa": "finance_qa",
    "tax": "tax_education",
    "portfolio": "portfolio",
    "market": "market_analysis",
    "goal": "goal_planning",
    "news": "news_synthesizer",
}   # clarify / off_topic / profile: the router answers, no agent


class RoutingDecision(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0, le=1)
    source: Literal["rules", "llm", "fallback", "hint", "awaiting"]  # which tier decided; invaluable when debugging
    normalized_question: str
    secondary_intents: list[Intent] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    clarification: str | None = None

class GraphState(TypedDict, total=False):
    text: str   # the raw user message
    thread_id: str
    agent: str | None # caller's hint; validated against AGENT_NAMES before use
    profile: UserProfile
    guard: GuardVerdict  # from input_guard
    standalone: str      # the question rewritten to stand alone (== text when it already does)
    history: list[Turn]  # this thread's recent turns
    decision: RoutingDecision
    result: AgentResult