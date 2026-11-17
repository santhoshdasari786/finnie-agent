"""When the embedding service is unavailable (quota gone, rate limit), the Q&A agent says so plainly and does not call the LLM.

Run:  .venv/bin/python -m pytest tests/agents/financeqaagents/embedding_unavailable_test.py -v

Contract
  * retrieval raising EmbeddingUnavailable -> status error, a calm "knowledge base is busy, try again" message
  * no stack trace or quota detail reaches the user, and the LLM is never asked to answer from nothing
  * any other crash still gets the generic error message
  * a glossary hit never needs the embedding service, so it still answers
"""
import pytest

from src.agents.finance_qa_agent import FinanceQAAgent
from src.common.models import QASettings
from src.rag.common.models import GlossaryEntry, GlossaryMatch
from src.rag.ingestion.embedders.gemini import EmbeddingUnavailable

from tests.conftest import FakeGlossary, FakeLLM

pytestmark = pytest.mark.asyncio


class Down:
    def __init__(self, error):
        self.error, self.calls = error, 0

    def retrieve(self, q):
        self.calls += 1
        raise self.error


def agent_with(error, glossary=None, llm_text="should not be used"):
    llm, down = FakeLLM(llm_text), Down(error)
    return FinanceQAAgent(llm=llm, retriever=down, glossary=glossary or FakeGlossary(), settings=QASettings()), llm, down


async def test_an_unavailable_embedding_service_gets_the_busy_message():
    agent, llm, down = agent_with(EmbeddingUnavailable("The daily embedding quota is used up."))
    result = await agent.ask("What is a SIP?")
    assert result.route == "error" and result.answer == QASettings().busy_message
    assert down.calls == 1 and llm.calls == []


async def test_the_busy_message_is_calm_and_leaks_nothing():
    agent, _, _ = agent_with(EmbeddingUnavailable("quota 1000 exceeded for project 12345"))
    text = (await agent.ask("What is a SIP?")).answer
    assert "try again" in text.lower() and "quota" not in text.lower() and "12345" not in text


async def test_it_still_carries_the_disclaimer():
    agent, _, _ = agent_with(EmbeddingUnavailable("x"))
    assert (await agent.ask("What is a SIP?")).disclaimer == QASettings().disclaimer


async def test_the_agent_result_is_an_error_with_the_route_recorded():
    agent, _, _ = agent_with(EmbeddingUnavailable("x"))
    r = await agent.run("What is a SIP?")
    assert r.status == "error" and r.meta["route"] == "error"


async def test_any_other_crash_still_gets_the_generic_message():
    agent, _, _ = agent_with(RuntimeError("chroma exploded"))
    result = await agent.ask("What is a SIP?")
    assert result.answer == QASettings().error_message and "chroma" not in result.answer


async def test_the_two_messages_are_different():
    s = QASettings()
    assert s.busy_message != s.error_message


async def test_a_glossary_answer_needs_no_embedding_service():
    entry = GlossaryEntry("SIP", "A plan that invests a fixed amount regularly.", source_urls=("https://x.example/sip",))
    agent, llm, down = agent_with(EmbeddingUnavailable("x"), FakeGlossary(GlossaryMatch([entry], "exact", "sip")),
                                  llm_text="A SIP invests a fixed amount regularly [1].")
    result = await agent.ask("What is a SIP?")
    assert result.route == "glossary" and down.calls == 0 and result.citations
