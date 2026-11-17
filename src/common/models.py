
from dataclasses import dataclass, fields
import re
from typing import Literal

@dataclass(frozen=True)
class QASettings:
    k: int = 5                          # sources per answer
    max_question_chars: int = 500
    max_context_chars: int = 6000       # 5 chunks x ~800 chars = ~4000, so there is headroom for titles
    disclaimer: str = "Educational information only — not financial advice."
    no_source_message: str = (
        "I don't have a reliable source for that in my knowledge base, so I'd rather not guess. "
        "Try rephrasing, or ask about a core investing topic such as diversification, SIPs, fees or compound interest."
    )
    redirect_message: str = (
        "I can help with general investing and personal-finance education. "
        "Could you ask about a concept such as risk, returns, fees, taxes or asset allocation?"
    )
    error_message: str = "Sorry, I couldn't put an answer together just now. Please try again in a moment."


    @classmethod
    def from_config(cls, cfg: dict) -> "QASettings":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (cfg or {}).items() if k in known})

@dataclass(frozen=True)
class GuardVerdict:
    action: Literal["pass", "block"] = "pass"
    category: str | None = None          # which rule fired: "empty", "self_harm", ...
    reply: str | None = None             # message to show, only when blocked
    flags: frozenset[str] = frozenset()  # soft signals on a PASS: "advice_seeking", ...

    @property
    def blocked(self) -> bool:
        return self.action == "block"


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern
    kind: Literal["block", "flag"]
    reply: str | None = None