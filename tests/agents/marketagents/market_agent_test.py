"""Market agent behaviour with a fake provider and a fake LLM (no network).

Run:  .venv/bin/python -m pytest tests/agents/marketagents/market_agent_test.py -v
Rule under test: NUMBERS come from the provider and are built in code; the LLM only narrates.
"""
from datetime import datetime, timezone

import pytest

from src.agents.market_analysis_agent import MarketAnalysisAgent, facts_line
from src.common.models import QASettings
from src.core.contracts import Agent, AgentResult
from src.data.market.models import Instrument, Quote
from tests.conftest import FakeLLM

pytestmark = pytest.mark.asyncio


def quote(symbol="NIFTY50", exchange="INDEX", price=25030.35, change=2.01):
    return Quote(instrument=Instrument(symbol=symbol, exchange=exchange), price=price, change_pct=change,
                 currency="INR", as_of=datetime(2026, 11, 7, 8, 30, tzinfo=timezone.utc), source="yfinance")


class FakeProvider:
    name = "fake"

    def __init__(self, quotes=None, error=None):
        self.table = {q.instrument: q for q in (quotes or [])}
        self.error = error
        self.calls: list[list[Instrument]] = []

    async def quotes(self, instruments):
        self.calls.append(list(instruments))
        if self.error:
            raise self.error
        return [self.table[i] for i in instruments if i in self.table]


@pytest.fixture
def llm():
    return FakeLLM("The Nifty rose about 2%.")

@pytest.fixture
def provider():
    return FakeProvider([quote(), quote("RELIANCE", "NSE", 1320.0, 0.5), quote("TCS", "NSE", 2500.0, None)])

@pytest.fixture
def agent(provider, llm):
    return MarketAnalysisAgent(provider, llm=llm, settings=QASettings())


# ---------------------------------------------------------------- contract
async def test_satisfies_the_agent_protocol(agent):
    assert isinstance(agent, Agent) and agent.name == "market_analysis"

async def test_happy_path_is_an_ok_agent_result(agent, provider):
    r = await agent.run("Nifty close today")
    assert isinstance(r, AgentResult) and r.status == "ok" and r.agent == "market_analysis"
    assert r.disclaimer and r.meta["provider"] == "fake"
    assert provider.calls == [[Instrument(symbol="NIFTY50", exchange="INDEX")]]


# ---------------------------------------------------------------- numbers come from code
async def test_text_contains_the_providers_numbers_and_source(agent):
    r = await agent.run("Nifty close today")
    assert "25,030.35 INR" in r.text and "+2.01%" in r.text and "yfinance" in r.text and "IST" in r.text

async def test_llm_cannot_change_the_numbers(provider):
    liar = FakeLLM("The Nifty is at 99,999.")
    r = await MarketAnalysisAgent(provider, llm=liar).run("Nifty close today")
    assert "25,030.35" in r.text            # the fact line is built in code and always present

async def test_llm_only_sees_the_data_not_the_open_web(agent, llm):
    await agent.run("Nifty close today")
    prompt = llm.calls[0][-1].content
    assert "DATA" in prompt and "25,030.35" in prompt and "Nifty close today" in prompt

async def test_system_prompt_forbids_predictions_and_advice(agent, llm):
    await agent.run("Nifty close today")
    system = llm.calls[0][0].content.lower()
    assert "never predict" in system and "recommend" in system

async def test_structured_data_is_returned_for_the_ui(agent):
    r = await agent.run("RELIANCE and TCS price")
    assert [q["instrument"]["symbol"] for q in r.data["quotes"]] == ["RELIANCE", "TCS"] and r.data["missing"] == []

async def test_missing_change_pct_is_shown_as_not_available():
    assert "change n/a" in facts_line(quote(change=None))

async def test_time_is_shown_in_ist():
    assert "14:00 IST" in facts_line(quote())         # 08:30 UTC


# ---------------------------------------------------------------- partial / missing
async def test_partial_result_names_the_missing_symbols(agent):
    r = await agent.run("TCS and NOPEXYZ price")
    assert r.status == "ok" and "TCS" in r.text and "NOPEXYZ" in r.text and r.data["missing"] == ["NOPEXYZ"]

async def test_nothing_found_is_a_retryable_error_naming_the_symbols(agent):
    r = await agent.run("NOPEXYZ price")
    assert r.status == "error" and "NOPEXYZ" in r.text and r.meta["retryable"] is True

async def test_no_instrument_in_the_query_asks_which_one(agent, provider, llm):
    r = await agent.run("reliance share price")
    assert r.status == "clarify" and provider.calls == [] and llm.calls == []


# ---------------------------------------------------------------- failures
async def test_provider_crash_is_a_friendly_error_not_an_exception(llm):
    r = await MarketAnalysisAgent(FakeProvider(error=RuntimeError("yahoo 429")), llm=llm).run("Nifty today")
    assert r.status == "error" and "429" not in r.text and r.meta["retryable"] is True

async def test_llm_failure_still_returns_the_numbers(provider, llm):
    llm.error = RuntimeError("quota")
    r = await MarketAnalysisAgent(provider, llm=llm).run("Nifty close today")
    assert r.status == "ok" and "25,030.35" in r.text and "quota" not in r.text

async def test_blank_llm_reply_returns_just_the_facts(provider):
    r = await MarketAnalysisAgent(provider, llm=FakeLLM("   ")).run("Nifty close today")
    assert r.status == "ok" and r.text.startswith("- NIFTY50") and not r.text.endswith("\n")


# ---------------------------------------------------------------- the provider is public (the API's history route uses it)
async def test_the_agent_exposes_its_provider():
    provider = object()
    assert MarketAnalysisAgent(provider, llm=object()).provider is provider
