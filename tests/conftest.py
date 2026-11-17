"""Shared test doubles for the Finance Q&A agent. No network, no API keys, no Chroma.

Why fakes instead of mocks: the agent's safety claims are about WHAT WAS NOT CALLED
("a self-harm message never reaches retrieval or the LLM"). A fake that records every call
makes that assertion one line:  assert retriever.calls == [] and llm.calls == [].

Reused by every later stage (glossary, no_source, citations): extend the fakes, don't replace them.
"""
import pytest
from langchain_core.messages import AIMessage

from src.agents.finance_qa_agent import FinanceQAAgent
from src.common.models import QASettings
from src.rag.common.models import RetrievalResult, RetrievedChunk


# ---------------------------------------------------------------- fake LLM
class FakeLLM:
    """Stands in for a LangChain chat model. Records every call; returns a canned reply.

    The agent only needs `await llm.ainvoke(messages)` returning an object with `.content`.
    """

    def __init__(self, reply: str = "A SIP invests a fixed amount at regular intervals [1]."):
        self.reply = reply
        self.calls: list[list] = []            # one entry per ainvoke: the list of messages sent
        self.error: Exception | None = None    # set to simulate an API failure

    async def ainvoke(self, messages, *args, **kwargs):
        self.calls.append(list(messages))
        if self.error:
            raise self.error
        return AIMessage(content=self.reply)

    # --- helpers for assertions
    def prompt_text(self, call: int = -1) -> str:
        """All message contents of one call, joined: what the model actually saw."""
        return "\n".join(str(getattr(m, "content", m)) for m in self.calls[call])


# ---------------------------------------------------------------- fake retriever
def make_chunk(n: int = 1, text: str = "A systematic investment plan (SIP) invests a fixed amount regularly.",
               title: str = "SIPs and Periodic Investing", score: float = 0.8, **meta) -> RetrievedChunk:
    metadata = {"doc_id": f"doc-{n}", "title": title, "last_verified_at": "2026-10-22",
                "source_urls": "https://example.org/sip", **meta}
    return RetrievedChunk(chunk_id=f"doc-{n}:0:abcd1234", text=text, score=score,
                          source=f"docs/knowledge-base/articles/doc-{n}.md", title=title, metadata=metadata)


class FakeRetriever:
    """Returns canned chunks and records every query it receives."""

    def __init__(self, chunks: list[RetrievedChunk] | None = None):
        self.chunks = [make_chunk()] if chunks is None else chunks
        self.calls: list = []                  # RetrievalQuery objects

    def retrieve(self, q):
        self.calls.append(q)
        return RetrievalResult(
            status="ok" if self.chunks else "no_source",
            chunks=list(self.chunks),
            best_score=max((c.score for c in self.chunks), default=None),
            query=q,
        )


# ---------------------------------------------------------------- fake glossary
class FakeGlossary:
    """lookup() returns whatever `match` you set (None = no glossary hit)."""

    def __init__(self, match=None):
        self.match = match
        self.calls: list[str] = []

    def lookup(self, question):
        self.calls.append(question)
        return self.match


# ---------------------------------------------------------------- fixtures
@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def retriever() -> FakeRetriever:
    return FakeRetriever()


@pytest.fixture
def glossary() -> FakeGlossary:
    return FakeGlossary()


@pytest.fixture
def settings() -> QASettings:
    return QASettings()


@pytest.fixture
def agent(llm, retriever, glossary, settings) -> FinanceQAAgent:
    # Passing retriever AND glossary means FinanceQAAgent never calls build_rag(),
    # so no Chroma, no Gemini key, no config file is touched.
    return FinanceQAAgent(llm=llm, retriever=retriever, glossary=glossary, settings=settings)


# ---------------------------------------------------------------- stub agents (for router / graph tests)
class StubAgent:
    """Satisfies the Agent protocol. Records every call; returns a canned AgentResult.

    Set `.raises` to simulate a crash, or pass `status="needs_login"` etc. to simulate other outcomes.
    Why: graph tests assert WHICH agent was called and WITH WHAT context, with no LLM, no network.
    """

    def __init__(self, name: str, text: str | None = None, status: str = "ok", data: dict | None = None,
                 meta: dict | None = None):
        self.name = name
        self.meta = meta or {}
        self.text = text or f"stub answer from {name}"
        self.status = status
        self.data = data
        self.raises: Exception | None = None
        self.calls: list[tuple] = []           # (query, ctx) per run()

    async def run(self, query, ctx=None):
        from src.core.contracts import AgentResult
        self.calls.append((query, ctx))
        if self.raises:
            raise self.raises
        return AgentResult(agent=self.name, status=self.status, text=self.text,
                           data=self.data, meta=self.meta, disclaimer=f"{self.name} disclaimer")


@pytest.fixture
def stub_agents() -> dict[str, StubAgent]:
    from src.workflow.state import AGENT_NAMES
    return {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
