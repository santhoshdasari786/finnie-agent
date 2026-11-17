from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable
from pydantic import BaseModel, Field, model_validator

Status = Literal["ok", "no_source", "clarify", "redirect", "needs_login", "error"]


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    text: str

class UserProfile(BaseModel):
    risk_appetite: Literal["conservative", "moderate", "aggressive"] | None = None
    risk_source: Literal["questionnaire", "stated", "default"] | None = None
    knowledge_level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    jurisdiction: str = "india"
    currency: str = "INR"
    goals: list[str] = Field(default_factory=list)

@dataclass(frozen=True)
class Citation:
    source: str                 # URL a user can open, else the article title
    title: str
    excerpt: str
    verified_at: str | None = None

class AgentResult(BaseModel):
    agent: str
    status: Status
    text: str
    data: dict[str, Any] | None = None
    citations: list[Citation] = Field(default_factory=list)
    disclaimer: str
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _invariants(self):
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if not self.disclaimer.strip():
            raise ValueError("disclaimer must not be empty")
        if self.status == "needs_login" and not (self.data or {}).get("login_url"):
            raise ValueError("needs_login requires data.login_url")
        return self

class AgentContext(BaseModel):
    thread_id: str
    profile: UserProfile = Field(default_factory=UserProfile)
    history: list[Turn] = Field(default_factory=list)
    category_hint: str | None = None
    flags: frozenset[str] = frozenset()
    slots: dict[str, Any] = Field(default_factory=dict)   # this agent's saved facts for the thread


@runtime_checkable
class Agent(Protocol):
    name: str
    async def run(self, query: str, ctx: AgentContext | None = None) -> AgentResult: ...


