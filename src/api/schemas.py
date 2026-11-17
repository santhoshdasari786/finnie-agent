from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.workflow.state import AgentName

THREAD_ID_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"
MAX_MESSAGE_CHARS = 2000
SAFE_META = ("retryable", "awaiting", "missing")


class ChatRequest(BaseModel):
    message: str = Field(max_length=MAX_MESSAGE_CHARS)
    thread_id: str | None = Field(default=None, pattern=THREAD_ID_PATTERN)
    agent: AgentName | None = None

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be blank")
        return v


class CitationOut(BaseModel):
    source: str
    title: str
    excerpt: str
    verified_at: str | None = None


class ChatResponse(BaseModel):
    thread_id: str
    agent: str
    status: str
    text: str
    citations: list[CitationOut]
    data: dict[str, Any] | None
    meta: dict[str, Any]
    disclaimer: str
    login_url: str | None


class AgentInfo(BaseModel):
    name: str
    ready: bool
