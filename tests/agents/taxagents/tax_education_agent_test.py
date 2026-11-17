"""Tax Education agent: behaviour with fakes (no network, no Chroma, no LLM).

Run:  .venv/bin/python -m pytest tests/agents/taxagents/tax_education_agent_test.py -v

The agent REUSES the Finance Q&A pipeline (guards, glossary, retrieval, citations) and differs in four ways:
  1. it only retrieves articles with topic "costs-taxes"
  2. its system prompt says "concepts, never current numbers"
  3. its disclaimer is stronger ("not tax advice, ask a professional")
  4. two numbers checks: a note in the prompt when the question asks for a rate/limit/deadline,
     and a caution appended when the answer still contains a figure
"""
import pytest

from src.agents.finance_qa_agent import FinanceQAAgent
from src.agents.tax_education_agent import TaxEducationAgent
from src.core.guardrails import SELF_HARM_MESSAGE
from src.prompts.qa_prompts import SYSTEM_PROMPT
from src.prompts.tax_prompts import FIGURES_CAUTION, NUMBERS_NOTE, TAX_DISCLAIMER, TAX_SYSTEM_PROMPT

from tests.conftest import FakeGlossary, FakeLLM, FakeRetriever

pytestmark = pytest.mark.asyncio

CONCEPT_Q = "How are capital gains taxed?"
NUMBER_Q = "What is the LTCG tax rate on equity?"


@pytest.fixture
def tax(llm, retriever, glossary, settings) -> TaxEducationAgent:
    return TaxEducationAgent(llm=llm, retriever=retriever, glossary=glossary, settings=settings)


# ---------------------------------------------------------------- identity
async def test_the_agent_is_named_for_the_router(tax):
    assert tax.name == "tax_education"

async def test_run_labels_the_result_with_its_own_name(tax):
    r = await tax.run(CONCEPT_Q)
    assert r.agent == "tax_education" and r.status == "ok"


# ---------------------------------------------------------------- 1. only tax articles are retrieved
async def test_retrieval_is_limited_to_the_tax_topic(tax, retriever):
    await tax.ask(CONCEPT_Q)
    assert retriever.calls[0].category == "costs-taxes"

async def test_a_caller_hint_cannot_widen_the_search(tax, retriever):
    await tax.ask(CONCEPT_Q, category_hint="products")
    assert retriever.calls[0].category == "costs-taxes"

async def test_finance_qa_is_not_affected(llm, retriever, glossary, settings):
    qa = FinanceQAAgent(llm=llm, retriever=retriever, glossary=glossary, settings=settings)
    await qa.ask("What is a SIP?")
    assert retriever.calls[0].category is None


# ---------------------------------------------------------------- 2. the prompt
async def test_the_tax_system_prompt_is_what_the_model_sees(tax, llm):
    await tax.ask(CONCEPT_Q)
    assert llm.calls[0][0].content == TAX_SYSTEM_PROMPT

async def test_the_tax_prompt_differs_from_the_general_one_and_bans_numbers():
    assert TAX_SYSTEM_PROMPT != SYSTEM_PROMPT
    low = TAX_SYSTEM_PROMPT.lower()
    assert "rate" in low and "never" in low and "tax professional" in low

async def test_finance_qa_keeps_its_own_prompt(llm, retriever, glossary, settings):
    qa = FinanceQAAgent(llm=llm, retriever=retriever, glossary=glossary, settings=settings)
    await qa.ask("What is a SIP?")
    assert llm.calls[0][0].content == SYSTEM_PROMPT


# ---------------------------------------------------------------- 3. the disclaimer
async def test_every_answer_carries_the_tax_disclaimer(tax):
    r = await tax.run(CONCEPT_Q)
    assert r.disclaimer == TAX_DISCLAIMER

async def test_the_disclaimer_says_what_it_must():
    low = TAX_DISCLAIMER.lower()
    assert "not tax advice" in low and "professional" in low

async def test_no_source_still_has_the_tax_disclaimer_and_skips_the_llm(llm, glossary, settings):
    tax = TaxEducationAgent(llm=llm, retriever=FakeRetriever(chunks=[]), glossary=glossary, settings=settings)
    r = await tax.run(CONCEPT_Q)
    assert r.status == "no_source" and r.disclaimer == TAX_DISCLAIMER and llm.calls == []


# ---------------------------------------------------------------- 4a. a question that asks for a number
@pytest.mark.parametrize("q", [
    "What is the LTCG tax rate on equity?",
    "What is the 80C limit?",
    "What are the income tax slabs?",
    "What is the deadline to file my ITR?",
    "What is the exemption threshold for capital gains?",
    "How much tax will I pay on 5 lakh profit?",
])
async def test_number_seeking_questions_get_the_numbers_note(tax, llm, q):
    await tax.ask(q)
    assert NUMBERS_NOTE in llm.prompt_text()

@pytest.mark.parametrize("q", [CONCEPT_Q, "What is tax loss harvesting?", "Why does holding period matter for tax?"])
async def test_concept_questions_do_not_get_it(tax, llm, q):
    await tax.ask(q)
    assert NUMBERS_NOTE not in llm.prompt_text()


# ---------------------------------------------------------------- 4b. an answer that still contains a figure
@pytest.mark.parametrize("reply", [
    "Long-term gains are taxed at 12.5% [1].",
    "Gains up to ₹1.25 lakh are exempt [1].",
    "You can claim Rs. 1,50,000 under 80C [1].",
    "The limit is $10,000 [1].",
    "Exempt up to 2 lakh [1].",
])
async def test_an_answer_with_a_figure_gets_the_caution(llm, retriever, glossary, settings, reply):
    tax = TaxEducationAgent(llm=FakeLLM(reply), retriever=retriever, glossary=glossary, settings=settings)
    r = await tax.run(CONCEPT_Q)
    assert FIGURES_CAUTION in r.text
    assert r.text.count(FIGURES_CAUTION) == 1

async def test_a_clean_answer_is_left_alone(llm, retriever, glossary, settings):
    tax = TaxEducationAgent(llm=FakeLLM("Gains are classed by holding period [1]."),
                            retriever=retriever, glossary=glossary, settings=settings)
    r = await tax.run(CONCEPT_Q)
    assert FIGURES_CAUTION not in r.text

async def test_a_citation_number_is_not_mistaken_for_a_figure(llm, retriever, glossary, settings):
    tax = TaxEducationAgent(llm=FakeLLM("Holding period decides the class [1][2]. Section 112A applies."),
                            retriever=retriever, glossary=glossary, settings=settings)
    r = await tax.run(CONCEPT_Q)
    assert FIGURES_CAUTION not in r.text

async def test_the_caution_points_to_an_official_source():
    assert "incometax.gov.in" in FIGURES_CAUTION or "tax professional" in FIGURES_CAUTION.lower()


# ---------------------------------------------------------------- inherited safety still holds
async def test_a_blocked_message_reaches_neither_retriever_nor_llm(tax, retriever, llm):
    r = await tax.run("I want to die")
    assert r.status == "redirect" and r.text.startswith(SELF_HARM_MESSAGE[:20])
    assert retriever.calls == [] and llm.calls == []

async def test_graph_flags_are_trusted_and_the_guard_is_not_run_twice(tax, retriever):
    from src.core.contracts import AgentContext
    ctx = AgentContext(thread_id="t", flags=frozenset({"advice_seeking"}))
    await tax.run(CONCEPT_Q, ctx)
    assert len(retriever.calls) == 1

async def test_an_llm_failure_becomes_a_friendly_error(llm, retriever, glossary, settings):
    bad = FakeLLM(); bad.error = RuntimeError("boom")
    tax = TaxEducationAgent(llm=bad, retriever=retriever, glossary=glossary, settings=settings)
    r = await tax.run(CONCEPT_Q)
    assert r.status == "error" and "boom" not in r.text
