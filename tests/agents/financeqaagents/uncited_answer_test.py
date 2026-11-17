"""An answer that cites nothing is not grounded: it must not be shown with borrowed citations.

Real case (2026-11-13): "What is ELSS?" retrieved an unrelated capital-gains chunk (score 0.666, threshold 0.66).
The model honestly said "no mention of ELSS", but the agent saw no [n] marker and listed the consulted
article as a citation. Rule now: no valid marker -> the standard no-source message, no citations, and the
model's text is dropped.

Run:  .venv/bin/python -m pytest tests/agents/financeqaagents/uncited_answer_test.py -v
"""
import pytest

from src.agents.finance_qa_agent import FinanceQAAgent
from src.agents.tax_education_agent import TaxEducationAgent

from tests.conftest import FakeLLM

pytestmark = pytest.mark.asyncio

REFUSAL = "Based on the provided sources, there is no mention or definition of ELSS."


@pytest.fixture(params=[FinanceQAAgent, TaxEducationAgent], ids=["finance_qa", "tax_education"])
def make(request, retriever, glossary, settings):
    return lambda reply: request.param(llm=FakeLLM(reply), retriever=retriever, glossary=glossary, settings=settings)


async def test_a_reply_with_no_marker_becomes_no_source(make, settings):
    r = await make(REFUSAL).run("What is ELSS?")
    assert r.status == "no_source" and r.text == settings.no_source_message

async def test_no_citations_are_attached_to_it(make):
    r = await make(REFUSAL).run("What is ELSS?")
    assert r.citations == []

async def test_the_models_refusal_text_is_not_shown(make):
    r = await make(REFUSAL).run("What is ELSS?")
    assert "ELSS" not in r.text

async def test_only_invented_markers_count_as_uncited(make):
    r = await make("ELSS is a tax-saving fund [9].").run("What is ELSS?")      # only source 1 exists
    assert r.status == "no_source" and r.citations == []

async def test_a_cited_answer_is_unchanged(make):
    r = await make("A SIP invests a fixed amount regularly [1].").run("What is a SIP?")
    assert r.status == "ok" and len(r.citations) == 1 and r.meta["route"] == "rag"

async def test_the_disclaimer_is_kept(make):
    r = await make(REFUSAL).run("What is ELSS?")
    assert r.disclaimer.strip()
