"""Portfolio analysis agent: connect flow + analysis, with fake sources / provider / LLM (no network).

Run:  .venv/bin/python -m pytest tests/agents/portfolioanalysis/portfolio_analysis_agent_test.py -v
Rules under test:
  * "connect to my portfolio" shows the menu (status clarify, options in data); nothing is fetched
  * "connect <source>" connects it; a source that needs a login answers needs_login + url, and the SAME
    command finishes the connection once the user has logged in
  * "analyze my portfolio" = holdings -> prices -> metrics (all CODE) -> the LLM only narrates
  * the agent never advises: descriptive wording only
"""
from datetime import datetime, timezone

import pytest

from src.agents.portfolio_analysis_agent import PortfolioAnalysisAgent, parse_command
from src.common.models import QASettings
from src.core.contracts import Agent, AgentContext, UserProfile
from src.data.market.models import Instrument, Quote
from src.data.portfolio.base import ConnectInfo, SessionExpired
from src.data.portfolio.models import Holding
from src.data.portfolio.sample import SampleSource
from src.data.portfolio.store import ConnectionStore
from tests.conftest import FakeLLM

pytestmark = pytest.mark.asyncio

T0 = datetime(2026, 11, 8, 8, 30, tzinfo=timezone.utc)          # 14:00 IST


# ---------------------------------------------------------------- fakes
class FakeProvider:
    name = "fake"

    def __init__(self, price=100.0, missing=(), error=None):
        self.price, self.missing, self.error = price, set(missing), error
        self.calls: list[list[Instrument]] = []

    async def quotes(self, instruments):
        self.calls.append(list(instruments))
        if self.error:
            raise self.error
        return [Quote(instrument=i, price=self.price, currency="INR", as_of=T0, source="yfinance")
                for i in instruments if i.symbol not in self.missing]


class FakeKite:
    """A login-first source (named kite so 'zerodha' resolves to it)."""
    name, label = "kite", "Zerodha Kite (live account, needs login)"

    def __init__(self):
        self.logged_in = False
        self.closed = 0

    async def close(self):
        self.closed += 1

    async def status(self):
        return "connected" if self.logged_in else "needs_login"

    async def connect(self, **params):
        if self.logged_in:
            return ConnectInfo(connected=True, message="Connected to Zerodha.")
        return ConnectInfo(connected=False, message="Open the link, log in, then say 'connect kite' again.",
                           login_url="https://kite.example/login")

    async def holdings(self):
        if not self.logged_in:
            raise SessionExpired("kite")
        return [Holding(instrument=Instrument(symbol="KITESTOCK"), quantity=10, asset_class="equity",
                        current_price=500.0)]


class EmptySource:
    name, label = "empty", "Empty account"
    async def status(self): return "available"
    async def connect(self, **params): return ConnectInfo(connected=True, message="Connected.")
    async def holdings(self): return []


class BrokenSource(EmptySource):
    name, label = "broken", "Broken"
    async def holdings(self): raise RuntimeError("source down")


def ctx(thread="t1", profile=None, flags=()):
    return AgentContext(thread_id=thread, profile=profile or UserProfile(), flags=frozenset(flags))


@pytest.fixture
def store():
    return ConnectionStore({"sample": SampleSource, "kite": FakeKite, "empty": EmptySource, "broken": BrokenSource})

@pytest.fixture
def provider():
    return FakeProvider()

@pytest.fixture
def llm():
    return FakeLLM("Your portfolio is spread across stocks, a fund and gold.")

@pytest.fixture
def agent(store, provider, llm):
    return PortfolioAnalysisAgent(store, provider, llm=llm, settings=QASettings())


# ---------------------------------------------------------------- command parsing
@pytest.mark.parametrize("text, expected", [
    ("connect to my portfolio", ("connect", None)),
    ("Connect my portfolio", ("connect", None)),
    ("connect sample", ("connect", "sample")),
    ("please connect to the SAMPLE portfolio", ("connect", "sample")),
    ("connect kite", ("connect", "kite")),
    ("connect zerodha", ("connect", "kite")),                  # alias
    ("connect robinhood", ("connect", "?robinhood")),          # unknown name is reported, not guessed
    ("disconnect sample", ("disconnect", "sample")),
    ("disconnect", ("disconnect", None)),
    ("analyze my portfolio", ("analyze", None)),
    ("how is my portfolio doing", ("analyze", None)),
    ("what are my holdings", ("analyze", None)),
])
async def test_parse_command(text, expected):
    assert parse_command(text, known={"sample", "kite"}) == expected

async def test_disconnect_is_not_mistaken_for_connect():
    assert parse_command("disconnect kite", known={"kite"})[0] == "disconnect"

async def test_zerodha_alias_needs_kite_to_be_registered():
    assert parse_command("connect zerodha", known={"sample"}) == ("connect", "?zerodha")


# ---------------------------------------------------------------- contract
async def test_satisfies_the_agent_protocol(agent):
    assert isinstance(agent, Agent) and agent.name == "portfolio"

async def test_works_without_a_context(agent, store):
    r = await agent.run("connect sample")
    assert r.status == "ok" and store.connected("default") == ["sample"]


# ---------------------------------------------------------------- the menu
async def test_connect_without_a_name_shows_the_menu(agent, provider, llm):
    r = await agent.run("connect to my portfolio", ctx())
    assert r.status == "clarify" and provider.calls == [] and llm.calls == []
    assert [o["name"] for o in r.data["options"]] == ["sample", "kite", "empty", "broken"]
    assert "connect sample" in r.text and "connect kite" in r.text

async def test_menu_shows_each_label(agent):
    r = await agent.run("connect to my portfolio", ctx())
    assert "Sample portfolio" in r.text and "Zerodha Kite" in r.text

async def test_analyze_with_nothing_connected_shows_the_menu(agent, provider):
    r = await agent.run("analyze my portfolio", ctx())
    assert r.status == "clarify" and "haven't connected" in r.text and provider.calls == []

async def test_menu_also_reports_what_is_already_connected(agent):
    await agent.run("connect sample", ctx())
    r = await agent.run("connect to my portfolio", ctx())
    assert r.data["connected"] == ["sample"]

async def test_unknown_source_name_shows_the_menu_and_names_the_miss(agent):
    r = await agent.run("connect robinhood", ctx())
    assert r.status == "clarify" and "robinhood" in r.text and "connect sample" in r.text


# ---------------------------------------------------------------- connecting
async def test_connect_sample(agent, store):
    r = await agent.run("connect sample", ctx())
    assert r.status == "ok" and store.connected("t1") == ["sample"]
    assert "demo" in r.text.lower() and "analyze" in r.text.lower()

async def test_connect_sentence_form(agent, store):
    await agent.run("please connect to the sample portfolio", ctx())
    assert store.connected("t1") == ["sample"]

async def test_login_source_answers_needs_login_with_the_url(agent, store):
    r = await agent.run("connect kite", ctx())
    assert r.status == "needs_login" and r.data["login_url"] == "https://kite.example/login"
    assert r.data["source"] == "kite" and "log in" in r.text.lower()
    assert store.connected("t1") == []

async def test_zerodha_means_kite(agent):
    r = await agent.run("connect zerodha", ctx())
    assert r.status == "needs_login" and r.data["source"] == "kite"

async def test_same_command_finishes_the_connection_after_login(agent, store):
    await agent.run("connect kite", ctx())
    store._instances[("t1", "kite")].logged_in = True
    r = await agent.run("connect kite", ctx())
    assert r.status == "ok" and store.connected("t1") == ["kite"]

async def test_threads_are_isolated(agent):
    await agent.run("connect sample", ctx("t1"))
    assert (await agent.run("analyze my portfolio", ctx("t2"))).status == "clarify"


# ---------------------------------------------------------------- disconnecting
async def test_disconnect_one_source(agent, store):
    await agent.run("connect sample", ctx())
    r = await agent.run("disconnect sample", ctx())
    assert r.status == "ok" and store.connected("t1") == []
    assert (await agent.run("analyze my portfolio", ctx())).status == "clarify"

async def test_disconnect_everything(agent, store):
    await agent.run("connect sample", ctx())
    await agent.run("connect empty", ctx())
    await agent.run("disconnect", ctx())
    assert store.connected("t1") == []

async def test_disconnecting_something_not_connected_says_so(agent):
    r = await agent.run("disconnect sample", ctx())
    assert r.status == "ok" and "wasn't connected" in r.text


# ---------------------------------------------------------------- analysis: numbers come from code
async def connected_agent(agent, *names, thread="t1"):
    for n in names:
        await agent.run(f"connect {n}", ctx(thread))
    return agent

async def test_analysis_totals_come_from_the_provider_prices(agent):
    await connected_agent(agent, "sample")
    r = await agent.run("analyze my portfolio", ctx())
    assert r.status == "ok" and "₹35,500.00" in r.text            # 355 units in total x 100
    assert r.data["metrics"]["total_value"] == 35500.0
    assert r.data["sources"] == ["sample"] and r.meta["price_sources"] == ["yfinance"]

async def test_the_llm_cannot_change_the_numbers(store, provider):
    a = PortfolioAnalysisAgent(store, provider, llm=FakeLLM("Your portfolio is worth ₹9,99,999."))
    await connected_agent(a, "sample")
    assert "₹35,500.00" in (await a.run("analyze my portfolio", ctx())).text

async def test_text_shows_holdings_allocation_and_asset_classes(agent):
    await connected_agent(agent, "sample")
    t = (await agent.run("analyze my portfolio", ctx())).text
    assert "GOLDBEES" in t and "%" in t and "gold" in t and "Diversification" in t

async def test_text_states_the_risk_profile_and_price_freshness(agent):
    await connected_agent(agent, "sample")
    t = (await agent.run("analyze my portfolio", ctx())).text
    assert "yfinance" in t and "14:00 IST" in t and ("aggressive" in t or "moderate" in t or "conservative" in t)

async def test_sample_data_is_labelled_as_demo_in_the_answer(agent):
    await connected_agent(agent, "sample")
    assert "demo" in (await agent.run("analyze my portfolio", ctx())).text.lower()

async def test_llm_sees_the_computed_facts_not_raw_holdings(agent, llm):
    await connected_agent(agent, "sample")
    await agent.run("analyze my portfolio", ctx())
    prompt = llm.calls[0][-1].content
    assert "DATA" in prompt and "₹35,500.00" in prompt

async def test_system_prompt_is_analysis_only(agent, llm):
    await connected_agent(agent, "sample")
    await agent.run("analyze my portfolio", ctx())
    system = llm.calls[0][0].content.lower()
    assert "never" in system and "buy" in system and "sell" in system and "trading assistant" not in system

async def test_advice_flag_adds_an_extra_instruction(agent, llm):
    await connected_agent(agent, "sample")
    await agent.run("analyze my portfolio", ctx())
    plain = llm.calls[0][0].content
    await agent.run("should I sell my portfolio?", ctx(flags={"advice_seeking"}))
    assert len(llm.calls[1][0].content) > len(plain)

async def test_two_sources_are_merged_in_one_analysis(agent):
    await connected_agent(agent, "sample", "empty")
    r = await agent.run("analyze my portfolio", ctx())
    assert r.data["sources"] == ["sample", "empty"] and r.data["metrics"]["total_value"] == 35500.0

async def test_logged_in_kite_holdings_keep_their_own_price(agent, store, provider):
    await agent.run("connect kite", ctx())
    store._instances[("t1", "kite")].logged_in = True
    await agent.run("connect kite", ctx())
    r = await agent.run("analyze my portfolio", ctx())
    assert r.data["metrics"]["total_value"] == 5000.0 and provider.calls == []     # 10 x 500, nothing to look up


# ---------------------------------------------------------------- profile comparison (descriptive, never advice)
async def test_mismatch_with_the_stated_risk_appetite_is_described(agent):
    await connected_agent(agent, "sample")
    r = await agent.run("analyze my portfolio", ctx(profile=UserProfile(risk_appetite="conservative")))
    assert "stated risk appetite" in r.text and "conservative" in r.text
    assert "should" not in r.text.split("stated risk appetite")[1][:200].lower()

async def test_matching_risk_appetite_adds_no_comparison(agent):
    await connected_agent(agent, "sample")
    m = (await agent.run("analyze my portfolio", ctx())).data["metrics"]["risk_assessment"]
    r = await agent.run("analyze my portfolio", ctx(profile=UserProfile(risk_appetite=m)))
    assert "stated risk appetite" not in r.text

async def test_no_stated_risk_appetite_adds_no_comparison(agent):
    await connected_agent(agent, "sample")
    assert "stated risk appetite" not in (await agent.run("analyze my portfolio", ctx())).text


# ---------------------------------------------------------------- gaps and failures
async def test_unpriced_holdings_are_named_not_hidden(store, llm):
    a = PortfolioAnalysisAgent(store, FakeProvider(missing={"GOLDBEES"}), llm=llm)
    await connected_agent(a, "sample")
    r = await a.run("analyze my portfolio", ctx())
    assert r.status == "ok" and "GOLDBEES" in r.text and "couldn't price" in r.text
    assert r.data["metrics"]["unpriced"] == ["GOLDBEES"]

async def test_nothing_priced_is_a_retryable_error(store, llm):
    a = PortfolioAnalysisAgent(store, FakeProvider(missing={h for h in
                               ["RELIANCE", "TCS", "INFY", "HDFCBANK", "NIFTYBEES", "LIQUIDBEES", "GOLDBEES"]}), llm=llm)
    await connected_agent(a, "sample")
    r = await a.run("analyze my portfolio", ctx())
    assert r.status == "error" and r.meta["retryable"] is True
    assert "couldn't price any" in r.text and len(r.meta["unquoted"]) == 7         # specific, not the generic message

async def test_provider_crash_is_a_friendly_error(store, llm):
    a = PortfolioAnalysisAgent(store, FakeProvider(error=RuntimeError("yahoo 429")), llm=llm)
    await connected_agent(a, "sample")
    r = await a.run("analyze my portfolio", ctx())
    assert r.status == "error" and "429" not in r.text and r.meta["retryable"] is True

async def test_a_broken_source_is_an_error_not_a_partial_portfolio(agent):
    await connected_agent(agent, "sample", "broken")
    r = await agent.run("analyze my portfolio", ctx())
    assert r.status == "error" and "source down" not in r.text

async def test_empty_account_is_a_message_not_an_error(agent, provider):
    await connected_agent(agent, "empty")
    r = await agent.run("analyze my portfolio", ctx())
    assert r.status == "ok" and "no holdings" in r.text.lower() and provider.calls == []

async def test_llm_failure_still_returns_the_numbers(store, provider, llm):
    llm.error = RuntimeError("quota")
    a = PortfolioAnalysisAgent(store, provider, llm=llm)
    await connected_agent(a, "sample")
    r = await a.run("analyze my portfolio", ctx())
    assert r.status == "ok" and "₹35,500.00" in r.text and "quota" not in r.text

async def test_every_result_carries_a_disclaimer(agent):
    for q in ["connect to my portfolio", "connect sample", "analyze my portfolio"]:
        assert (await agent.run(q, ctx())).disclaimer


# ---------------------------------------------------------------- live-connection behaviour (Kite)
async def test_disconnect_closes_the_underlying_connection(agent, store):
    await agent.run("connect kite", ctx())
    kite = store._instances[("t1", "kite")]
    await agent.run("disconnect kite", ctx())
    assert kite.closed == 1

async def test_disconnect_also_closes_a_login_that_was_never_finished(agent, store):
    await agent.run("connect kite", ctx())                    # login pending: not 'connected', but a connection is open
    kite = store._instances[("t1", "kite")]
    r = await agent.run("disconnect kite", ctx())
    assert r.status == "ok" and "Disconnected" in r.text and kite.closed == 1 and store.opened("t1") == []

async def test_disconnect_everything_also_closes_pending_logins(agent, store):
    await agent.run("connect sample", ctx())
    await agent.run("connect kite", ctx())
    kite = store._instances[("t1", "kite")]
    await agent.run("disconnect", ctx())
    assert kite.closed == 1 and store.opened("t1") == [] and store.connected("t1") == []

async def test_expired_session_during_analysis_asks_for_a_fresh_login(agent, store):
    await agent.run("connect kite", ctx())
    store._instances[("t1", "kite")].logged_in = True
    await agent.run("connect kite", ctx())
    store._instances[("t1", "kite")].logged_in = False         # Kite session expires mid-conversation
    r = await agent.run("analyze my portfolio", ctx())
    assert r.status == "needs_login" and r.data["login_url"] == "https://kite.example/login"
    assert r.data["source"] == "kite" and store.connected("t1") == []

async def test_after_an_expiry_the_same_command_reconnects(agent, store):
    await agent.run("connect kite", ctx())
    kite = store._instances[("t1", "kite")]
    kite.logged_in = True
    await agent.run("connect kite", ctx())
    kite.logged_in = False
    await agent.run("analyze my portfolio", ctx())
    kite.logged_in = True                                      # the user logs in again
    assert (await agent.run("connect kite", ctx())).status == "ok"
    assert (await agent.run("analyze my portfolio", ctx())).status == "ok"


# ================================================================ narration may not add numbers
async def test_a_story_with_an_invented_number_is_dropped(store, provider):
    agent = PortfolioAnalysisAgent(store, provider, llm=FakeLLM("Your portfolio will be worth ₹9,87,65,432 soon."),
                                   settings=QASettings())
    await agent.run("connect sample", ctx())
    r = await agent.run("analyze my portfolio", ctx())
    assert r.status == "ok" and "9,87,65,432" not in r.text and "Portfolio:" in r.text

async def test_a_story_without_numbers_is_kept(store, provider):
    agent = PortfolioAnalysisAgent(store, provider, llm=FakeLLM("A mix of stocks, a fund and gold."), settings=QASettings())
    await agent.run("connect sample", ctx())
    r = await agent.run("analyze my portfolio", ctx())
    assert "A mix of stocks, a fund and gold." in r.text
