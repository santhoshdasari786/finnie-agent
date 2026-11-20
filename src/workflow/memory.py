import logging
import re
from collections import defaultdict
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError
from src.core.contracts import AgentResult, Turn, UserProfile
from src.core.responses import AgentResponse


log = logging.getLogger(__name__)

_STARTS = re.compile(r"^(and|also|then|so|but|ok|okay|what about|how about|what if|why|how come)\b", re.I)
_PRONOUN = re.compile(r"\b(it|its|that|this|those|these|they|them|their|same)\b", re.I)
_NOT_REMEMBERED = {"error", "redirect", "needs_login"}
_ANSWER = re.compile(r"\d|\b(lakh|lac|crore|cr|thousand|million|conservative|moderate|aggressive)\b", re.I)


def looks_like_slot_answer(text: str) -> bool:
    """A short reply that carries a number, an amount word or a risk word: likely the answer to a question we asked."""
    t = (text or "").strip()
    return bool(t) and len(t.split()) <= 25 and bool(_ANSWER.search(t))



def looks_like_followup(text: str) -> bool:
    t = text.strip()
    words = t.split()
    if _STARTS.search(t):
        return True
    if len(words) <= 2 and t.endswith("?"):
        return True
    return bool(_PRONOUN.search(t)) and len(words) <= 12


class ConversationMemory:
    def __init__(self, rewriter=None, max_turns: int = 6, max_chars: int = 500):
        self._rewriter, self._max_turns, self._max_chars = rewriter, max_turns, max_chars
        self._turns: dict[str, list[Turn]] = defaultdict(list)
        self._profiles: dict[str, UserProfile] = {}
        self._slots: dict[tuple[str, str], dict] = {}
        self._last_agent: dict[str, str] = {}      # thread -> the last real agent that answered
        self._awaiting: dict[str, str] = {}      # thread -> the agent whose question is waiting for an answer
        self._pending_goal: dict[str, str] = {}  # thread -> a goal question waiting for the portfolio to be connected

    def history(self, thread_id: str) -> list[Turn]:
        return list(self._turns.get(thread_id, []))

    def profile(self, thread_id: str) -> UserProfile:
        return self._profiles.get(thread_id, UserProfile()).model_copy(deep=True)

    def slots(self, thread_id: str, agent: str) -> dict:
        return dict(self._slots.get((thread_id, agent), {}))

    def _learn(self, thread_id: str, result: AgentResult) -> None:
        learned = result.meta.get("learned")
        if not isinstance(learned, dict):
            return
        prof = learned.get("profile")
        if isinstance(prof, dict):
            clean = {k: v for k, v in prof.items() if v is not None}
            if clean:
                current = self._profiles.get(thread_id, UserProfile())
                try:
                    self._profiles[thread_id] = UserProfile(**{**current.model_dump(), **clean})
                except (ValidationError, TypeError):
                    log.warning("ignored an invalid profile update: %r", clean)
        key = (thread_id, result.agent)
        if learned.get("slots_reset"):
            self._slots.pop(key, None)
        slots = learned.get("slots")
        if isinstance(slots, dict):
            self._slots.setdefault(key, {}).update({k: v for k, v in slots.items() if v is not None})

    def set_pending_goal(self, thread_id: str, question: str) -> None:
        self._pending_goal[thread_id] = question

    def take_pending_goal(self, thread_id: str) -> str | None:
        return self._pending_goal.pop(thread_id, None)

    def last_agent(self, thread_id: str) -> str | None:
        return self._last_agent.get(thread_id)

    def awaiting(self, thread_id: str) -> str | None:
        return self._awaiting.get(thread_id)

    def remember(self, thread_id: str, question: str, result: AgentResult) -> None:
        if result.status in _NOT_REMEMBERED:
            return
        if result.status == "clarify" and result.meta.get("awaiting"):
            self._awaiting[thread_id] = result.meta["awaiting"]
        elif result.agent != "router":          # the router's own replies never cancel an agent's pending question
            self._awaiting.pop(thread_id, None)
        if result.agent != "router":
            self._last_agent[thread_id] = result.agent
        self._learn(thread_id, result)
        summary = result.meta.get("summary")
        said = summary if isinstance(summary, str) and summary.strip() else result.text
        cut = lambda s: s[: self._max_chars]  # noqa: E731
        turns = self._turns[thread_id]
        turns += [Turn(role="user", text=cut(question)), Turn(role="assistant", text=cut(said))]
        del turns[: -self._max_turns]

    def clear(self, thread_id: str) -> None:
        self._turns.pop(thread_id, None)
        self._awaiting.pop(thread_id, None)
        self._pending_goal.pop(thread_id, None)
        self._profiles.pop(thread_id, None)
        self._last_agent.pop(thread_id, None)
        for key in [k for k in self._slots if k[0] == thread_id]:
            del self._slots[key]


    async def standalone(self, thread_id: str, text: str) -> str:
        history = self.history(thread_id)
        if not (self._rewriter and history and looks_like_followup(text)):
            return text
        try:
            out = (await self._rewriter.rewrite(text, history)).strip()
        except Exception:
            log.exception("rewrite failed; using the original question")
            return text
        if not out or len(out) > 300 or "\n" in out:
            return text
        if out != text:
            log.info("rewrote follow-up %r -> %r", text, out)
        return out




REWRITE_PROMPT = """Rewrite the user's last message as ONE standalone question, using the conversation for context.
If it already stands alone, return it unchanged. Do not answer it. Do not add facts that are not in the conversation.
Output only the question."""


class LLMRewriter:
    def __init__(self, llm):
        self._llm = llm

    async def rewrite(self, text: str, history: list[Turn]) -> str:
        convo = "\n".join(f"{t.role}: {t.text}" for t in history)
        reply = await self._llm.ainvoke([SystemMessage(content=REWRITE_PROMPT),
                                         HumanMessage(content=f"CONVERSATION\n{convo}\n\nLAST MESSAGE\n{text}")])
        return AgentResponse.from_message(reply).text.strip('"').strip()


