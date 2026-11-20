"""The portfolio answer states what the funds cost, and says plainly where that is not known.

Run:  .venv/bin/python -m pytest tests/agents/portfolioanalysis/expense_ratio_test.py -v
Contract
  * the facts block (code, not the model) carries the weighted ratio, the yearly cost in rupees and how much of the portfolio it covers
  * demo data says its ratios are illustrative
  * a fund without a known ratio is named, never guessed
  * the model's story may not add figures that are not in the facts (the grounding check still applies)
"""
from datetime import datetime, timezone

import pytest

from src.agents.portfolio_analysis_agent import PortfolioAnalysisAgent
from src.common.models import QASettings
from src.core.contracts import AgentContext, UserProfile
from src.data.market.models import Instrument, Quote
from src.data.portfolio.base import ConnectInfo
from src.data.portfolio.models import Holding
from src.data.portfolio.sample import SampleSource
from src.data.portfolio.store import ConnectionStore
from tests.conftest import FakeLLM

pytestmark = pytest.mark.asyncio
T0 = datetime(2026, 11, 8, 8, 30, tzinfo=timezone.utc)


class Provider:
    name = "fake"

    async def quotes(self, instruments):
        return [Quote(instrument=i, price=100.0, currency="INR", as_of=T0, source="yfinance") for i in instruments]


class FundsOnly:
    """A broker that reports funds but no expense ratios (like Kite)."""
    name, label = "broker", "A broker"

    async def status(self): return "available"
    async def connect(self, **p): return ConnectInfo(connected=True, message="Connected.")

    async def holdings(self):
        return [Holding(instrument=Instrument(symbol="BIGFUND"), quantity=100, asset_class="equity_fund", current_price=100.0),
                Holding(instrument=Instrument(symbol="TCS"), quantity=10, asset_class="equity", current_price=100.0)]


def ctx():
    return AgentContext(thread_id="t1", profile=UserProfile(), flags=frozenset())


async def analyse(source, llm=None):
    store = ConnectionStore({"sample": SampleSource, "broker": FundsOnly})
    agent = PortfolioAnalysisAgent(store, Provider(), llm=llm or FakeLLM("Spread across a few things."), settings=QASettings())
    await agent.run(f"connect {source}", ctx())
    return await agent.run("analyze my portfolio", ctx())


async def test_the_answer_states_the_weighted_ratio_the_yearly_cost_and_the_coverage():
    t = (await analyse("sample")).text
    assert "0.55%" in t and "₹168.25" in t and "85.9%" in t


async def test_each_fund_line_shows_its_own_ratio_and_stocks_show_none():
    lines = {l.split()[1]: l for l in (await analyse("sample")).text.splitlines() if l.startswith("- ")}
    assert "0.80%" in lines["GOLDBEES"] and "0.05%" in lines["NIFTYBEES"] and "fee" not in lines["TCS"]


async def test_demo_ratios_are_called_illustrative():
    t = (await analyse("sample")).text
    assert "illustrative" in t.lower()


async def test_a_fund_with_no_known_ratio_is_named_and_not_guessed():
    t = (await analyse("broker")).text
    assert "Expense ratio not known for: BIGFUND" in t and "Fund costs" not in t and "illustrative" not in t.lower()


async def test_the_data_carries_the_numbers_for_the_screen():
    m = (await analyse("sample")).data["metrics"]
    assert (m["weighted_expense_ratio_pct"], m["annual_fund_cost"], m["expense_covered_pct"], m["expense_unknown"]) == (0.55, 168.25, 85.92, [])


async def test_the_model_cannot_invent_a_different_cost():
    r = await analyse("sample", FakeLLM("Your funds cost ₹9,999 a year."))
    assert "₹168.25" in r.text and "9,999" not in r.text


async def test_the_model_sees_the_cost_facts():
    llm = FakeLLM("ok")
    await analyse("sample", llm)
    assert "Fund costs" in llm.calls[0][-1].content


async def test_the_wording_describes_and_does_not_advise():
    t = (await analyse("sample")).text.lower()
    assert "switch" not in t and "you should" not in t and "cheaper fund" not in t
