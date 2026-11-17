"""MCP server: Finnie as tools for Claude Desktop (or any MCP client).

Run:  .venv/bin/python -m pytest tests/mcp_server -v
No process, no network, no LLM: an in-memory FastMCP client talks to the server, which runs on stub agents.

Rules under test
  * a THIN ADAPTER over the same runtime as the HTTP API: every tool goes through the graph, so the guards,
    the disclaimer and the memory apply exactly as in the chat
  * read-only: the tool list is an exact allowlist; no trading tool, no raw Kite tool, no raw knowledge-base search
  * arguments are validated by the schema, with limits; a bad call is a clear error, not a stack trace
  * one server process is one conversation by default (stdio: Claude Desktop starts one process per connection);
    a client that wants separate conversations passes a thread_id
  * stdout belongs to the protocol: nothing may be printed during a tool call
"""
import asyncio
import contextlib
import io

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from src.core.contracts import AgentResult
from src.mcp_server.server import build_goal_question, create_server
from src.workflow.state import AGENT_NAMES

from tests.api.chat_api_test import FakeStore, make_runtime
from tests.conftest import StubAgent

pytestmark = pytest.mark.asyncio

TOOLS = {"ask_finance", "explain_term", "get_quote", "plan_goal", "analyze_portfolio", "portfolio_login"}
REPLY_KEYS = {"thread_id", "agent", "status", "text", "citations", "data", "meta", "disclaimer", "login_url"}


def stubs(**over):
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents.update(over)
    return agents

async def call(server, tool, args=None, client=None):
    if client:
        return (await client.call_tool(tool, args or {})).data
    async with Client(server) as c:
        return (await c.call_tool(tool, args or {})).data


# ================================================================ what is offered
async def test_the_tool_list_is_exactly_the_allowlist():
    async with Client(create_server(runtime=make_runtime())) as c:
        assert {t.name for t in await c.list_tools()} == TOOLS

@pytest.mark.parametrize("forbidden", ["place_order", "modify_order", "cancel_order", "place_gtt_order", "get_holdings",
                                       "get_positions", "login", "search_knowledge_base", "get_price_history"])
async def test_nothing_that_trades_or_leaks_raw_data_is_offered(forbidden):
    async with Client(create_server(runtime=make_runtime())) as c:
        assert forbidden not in {t.name for t in await c.list_tools()}

async def test_every_tool_is_marked_read_only():
    async with Client(create_server(runtime=make_runtime())) as c:
        for t in await c.list_tools():
            assert t.annotations is not None and t.annotations.read_only_hint is True, t.name
            assert t.annotations.destructive_hint is not True, t.name

async def test_every_tool_has_a_description():
    async with Client(create_server(runtime=make_runtime())) as c:
        assert all(t.description and len(t.description) > 20 for t in await c.list_tools())

async def test_the_server_says_what_it_is():
    async with Client(create_server(runtime=make_runtime())) as c:
        assert c.server_info.name == "Finnie"
        assert "education" in c.instructions.lower() and "not financial advice" in c.instructions.lower()
        assert "cannot place" in c.instructions.lower()

async def test_the_schema_carries_the_limits():
    async with Client(create_server(runtime=make_runtime())) as c:
        ask = next(t for t in await c.list_tools() if t.name == "ask_finance")
        q = ask.input_schema["properties"]["question"]
        assert q["minLength"] == 1 and q["maxLength"] == 2000
        assert ask.input_schema["required"] == ["question"]


# ================================================================ ask_finance
async def test_ask_finance_goes_through_the_graph_and_returns_the_api_shape():
    out = await call(create_server(runtime=make_runtime()), "ask_finance", {"question": "What is a SIP?"})
    assert set(out) == REPLY_KEYS and out["agent"] == "finance_qa" and out["status"] == "ok" and out["disclaimer"]

async def test_the_router_picks_the_agent():
    out = await call(create_server(runtime=make_runtime()), "ask_finance", {"question": "capital gains tax on shares"})
    assert out["agent"] == "tax_education"

async def test_a_blocked_question_is_a_normal_reply_and_no_agent_runs():
    rt = make_runtime()
    out = await call(create_server(runtime=rt), "ask_finance", {"question": "I want to die"})
    assert out["agent"] == "guard" and out["status"] == "redirect"
    assert not [n for n, a in rt.agents.items() if a.calls]

async def test_only_safe_meta_leaves_the_server():
    agents = stubs(finance_qa=StubAgent("finance_qa", meta={"awaiting": "x", "learned": {"slots": {"a": 1}}, "summary": "s"}))
    out = await call(create_server(runtime=make_runtime(agents)), "ask_finance", {"question": "What is a SIP?"})
    assert out["meta"] == {"awaiting": "x"}

async def test_a_login_link_is_lifted_to_the_top_level():
    agents = stubs(portfolio=StubAgent("portfolio", status="needs_login", data={"login_url": "https://kite.example/l"}))
    out = await call(create_server(runtime=make_runtime(agents)), "ask_finance", {"question": "Analyze my portfolio"})
    assert out["status"] == "needs_login" and out["login_url"] == "https://kite.example/l"

@pytest.mark.parametrize("question", ["", "   ", "x" * 2001])
async def test_a_bad_question_is_a_clear_error(question):
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError):
            await c.call_tool("ask_finance", {"question": question})

async def test_a_missing_question_is_a_clear_error():
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError):
            await c.call_tool("ask_finance", {})

async def test_an_unknown_argument_is_refused():
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError):
            await c.call_tool("ask_finance", {"question": "hi there", "agent": "portfolio"})

async def test_the_question_is_trimmed():
    rt = make_runtime()
    await call(create_server(runtime=rt), "ask_finance", {"question": "   What is a SIP?   "})
    assert rt.agents["finance_qa"].calls[0][0] == "What is a SIP?"


# ================================================================ conversations
async def test_calls_on_one_server_are_one_conversation():
    rt = make_runtime()
    async with Client(create_server(runtime=rt)) as c:
        await call(None, "ask_finance", {"question": "What is a SIP?"}, client=c)
        await call(None, "ask_finance", {"question": "What is a SIP?"}, client=c)
    assert len(rt.agents["finance_qa"].calls[1][1].history) == 2

async def test_a_reconnecting_client_continues_the_same_conversation():
    rt = make_runtime()
    server = create_server(runtime=rt)
    async with Client(server) as c:
        await call(None, "ask_finance", {"question": "What is a SIP?"}, client=c)
    async with Client(server) as c:
        await call(None, "ask_finance", {"question": "What is a SIP?"}, client=c)
    assert len(rt.agents["finance_qa"].calls[1][1].history) == 2

async def test_two_server_processes_do_not_share_a_conversation():
    rt = make_runtime()
    await call(create_server(runtime=rt), "ask_finance", {"question": "What is a SIP?"})
    await call(create_server(runtime=rt), "ask_finance", {"question": "What is a SIP?"})
    assert rt.agents["finance_qa"].calls[1][1].history == []

async def test_a_client_can_keep_separate_conversations_with_thread_ids():
    rt = make_runtime()
    server = create_server(runtime=rt)
    async with Client(server) as c:
        await call(None, "ask_finance", {"question": "What is a SIP?", "thread_id": "conversation-a"}, client=c)
        await call(None, "ask_finance", {"question": "What is a SIP?", "thread_id": "conversation-b"}, client=c)
    assert rt.agents["finance_qa"].calls[1][1].history == []

async def test_a_given_thread_id_is_used():
    rt = make_runtime()
    server = create_server(runtime=rt)
    await call(server, "ask_finance", {"question": "What is a SIP?", "thread_id": "shared-thread-1"})
    out = await call(server, "ask_finance", {"question": "What is a SIP?", "thread_id": "shared-thread-1"})
    assert out["thread_id"] == "shared-thread-1" and len(rt.agents["finance_qa"].calls[1][1].history) == 2

@pytest.mark.parametrize("tid", ["short", "has space in it", "../../etc/passwd", "a" * 65])
async def test_a_malformed_thread_id_is_refused(tid):
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError):
            await c.call_tool("ask_finance", {"question": "hi there", "thread_id": tid})

async def test_the_reply_names_the_thread():
    out = await call(create_server(runtime=make_runtime()), "ask_finance", {"question": "What is a SIP?"})
    assert out["thread_id"].startswith("mcp-")

async def test_every_tool_uses_the_same_default_conversation():
    rt = make_runtime()
    server = create_server(runtime=rt)
    a = await call(server, "ask_finance", {"question": "What is a SIP?"})
    b = await call(server, "explain_term", {"term": "SIP"})
    assert a["thread_id"] == b["thread_id"]

# ================================================================ explain_term
async def test_explain_term_asks_the_qa_agent_what_it_is():
    rt = make_runtime()
    out = await call(create_server(runtime=rt), "explain_term", {"term": "expense ratio"})
    assert out["agent"] == "finance_qa" and rt.agents["finance_qa"].calls[0][0] == "What is expense ratio?"

async def test_explain_term_is_guarded_too():
    rt = make_runtime()
    out = await call(create_server(runtime=rt), "explain_term", {"term": "I want to die"})
    assert out["agent"] == "guard"

@pytest.mark.parametrize("term", ["", "  ", "x" * 81])
async def test_explain_term_validates(term):
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError):
            await c.call_tool("explain_term", {"term": term})

async def test_explain_term_always_uses_the_qa_agent_even_for_a_word_that_sounds_like_tax():
    rt = make_runtime()
    await call(create_server(runtime=rt), "explain_term", {"term": "capital gains tax"})
    assert rt.agents["finance_qa"].calls and not rt.agents["tax_education"].calls


# ================================================================ get_quote
async def test_get_quote_asks_the_market_agent():
    rt = make_runtime()
    out = await call(create_server(runtime=rt), "get_quote", {"symbols": ["TCS", "RELIANCE"]})
    assert out["agent"] == "market_analysis" and rt.agents["market_analysis"].calls[0][0] == "Quote for TCS, RELIANCE"

async def test_symbols_are_upper_cased_and_trimmed():
    rt = make_runtime()
    await call(create_server(runtime=rt), "get_quote", {"symbols": [" tcs ", "infy"]})
    assert rt.agents["market_analysis"].calls[0][0] == "Quote for TCS, INFY"

@pytest.mark.parametrize("symbol, name", [("^NSEI", "Nifty 50"), ("nifty", "Nifty 50"), ("NIFTY50", "Nifty 50"),
                                          ("^BSESN", "Sensex"), ("sensex", "Sensex")])
async def test_an_index_is_asked_for_by_name_because_that_is_what_the_agent_understands(symbol, name):
    rt = make_runtime()
    await call(create_server(runtime=rt), "get_quote", {"symbols": [symbol]})
    assert rt.agents["market_analysis"].calls[0][0] == f"Quote for {name}"

async def test_a_stock_and_an_index_can_be_mixed():
    rt = make_runtime()
    await call(create_server(runtime=rt), "get_quote", {"symbols": ["tcs", "^NSEI"]})
    assert rt.agents["market_analysis"].calls[0][0] == "Quote for TCS, Nifty 50"

async def test_the_same_index_written_two_ways_is_asked_once():
    rt = make_runtime()
    await call(create_server(runtime=rt), "get_quote", {"symbols": ["NIFTY", "^NSEI", "NIFTY50"]})
    assert rt.agents["market_analysis"].calls[0][0] == "Quote for Nifty 50"

@pytest.mark.parametrize("symbol", ["^GSPC", "^DJI", "^FTSE"])
async def test_an_index_the_agent_does_not_know_is_refused_with_the_supported_list(symbol):
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError, match="Nifty 50 and Sensex"):
            await c.call_tool("get_quote", {"symbols": [symbol]})

async def test_the_description_names_the_supported_indexes():
    async with Client(create_server(runtime=make_runtime())) as c:
        d = next(t for t in await c.list_tools() if t.name == "get_quote").description
        assert "NIFTY50" in d and "SENSEX" in d and "^NSEI" not in d

@pytest.mark.parametrize("symbols", [[], ["A"] * 11, [""], ["TCS; DROP TABLE"], ["X" * 21], ["TCS", "bad symbol"], ["<script>"]])
async def test_bad_symbols_are_refused(symbols):
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError):
            await c.call_tool("get_quote", {"symbols": symbols})

async def test_ten_symbols_are_allowed():
    rt = make_runtime()
    await call(create_server(runtime=rt), "get_quote", {"symbols": [f"S{i}" for i in range(10)]})
    assert rt.agents["market_analysis"].calls


# ================================================================ plan_goal
def goal(**kw):
    base = dict(horizon_years=10, monthly_contribution=20000, target_amount=5000000)
    return {**base, **kw}

async def test_plan_goal_asks_the_goal_agent():
    rt = make_runtime()
    out = await call(create_server(runtime=rt), "plan_goal", goal())
    assert out["agent"] == "goal_planning" and len(rt.agents["goal_planning"].calls) == 1

async def test_the_goal_sentence_carries_every_number():
    q = build_goal_question(horizon_years=10, target_amount=5000000, monthly_contribution=20000, starting_balance=100000,
                            risk_appetite="aggressive", annual_return_pct=12)
    for piece in ["5000000", "10 years", "20000", "100000", "aggressive", "12%"]:
        assert piece in q

async def test_the_sentence_starts_a_new_goal_so_earlier_numbers_do_not_leak_in():
    q = build_goal_question(horizon_years=10, target_amount=None, monthly_contribution=20000, starting_balance=None,
                            risk_appetite=None, annual_return_pct=None)
    assert q.startswith("New goal: ")

async def test_the_sentence_leaves_out_what_was_not_given():
    q = build_goal_question(horizon_years=10, target_amount=None, monthly_contribution=20000, starting_balance=None,
                            risk_appetite=None, annual_return_pct=None)
    assert "20000" in q and "%" not in q and "aggressive" not in q and "starting" not in q

async def test_a_fractional_horizon_is_written_plainly():
    assert "7.5 years" in build_goal_question(horizon_years=7.5, target_amount=1000000, monthly_contribution=None,
                                              starting_balance=None, risk_appetite=None, annual_return_pct=None)

async def test_the_goal_agent_receives_the_sentence():
    rt = make_runtime()
    await call(create_server(runtime=rt), "plan_goal", goal(risk_appetite="moderate", annual_return_pct=9))
    sent = rt.agents["goal_planning"].calls[0][0]
    assert "5000000" in sent and "moderate" in sent and "9%" in sent

@pytest.mark.parametrize("bad", [
    dict(horizon_years=0), dict(horizon_years=-1), dict(horizon_years=61), dict(monthly_contribution=-1),
    dict(target_amount=0), dict(target_amount=-5), dict(starting_balance=-1), dict(annual_return_pct=-1),
    dict(annual_return_pct=31), dict(risk_appetite="reckless"), dict(target_amount=10**13), dict(horizon_years="soon"),
])
async def test_plan_goal_refuses_unreasonable_numbers(bad):
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError):
            await c.call_tool("plan_goal", goal(**bad))

async def test_a_horizon_is_required():
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError):
            await c.call_tool("plan_goal", {"target_amount": 1000000})

async def test_at_least_one_amount_is_required():
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError, match="target amount"):
            await c.call_tool("plan_goal", {"horizon_years": 10})

async def test_a_starting_balance_alone_is_enough():
    out = await call(create_server(runtime=make_runtime()), "plan_goal", {"horizon_years": 10, "starting_balance": 500000})
    assert out["agent"] == "goal_planning"

async def test_plan_goal_keeps_the_plan_data():
    agents = stubs(goal_planning=StubAgent("goal_planning", data={"plan": {"years": 10, "scenarios": [{"name": "expected"}]}}))
    out = await call(create_server(runtime=make_runtime(agents)), "plan_goal", goal())
    assert out["data"]["plan"]["scenarios"][0]["name"] == "expected"


# ================================================================ analyze_portfolio and login
class Scripted(StubAgent):
    """A portfolio agent answering from a script, keyed by the message."""
    def __init__(self, script):
        super().__init__("portfolio")
        self.script = script

    async def run(self, query, ctx=None):
        self.calls.append((query, ctx))
        status, text, data = self.script.get(query, ("ok", "ok", None))
        return AgentResult(agent="portfolio", status=status, text=text, data=data, disclaimer="d")

async def test_a_sample_portfolio_is_connected_then_analysed():
    agent = Scripted({"connect sample": ("ok", "Connected.", None), "analyze my portfolio": ("ok", "Portfolio: 1", {"metrics": {}})})
    out = await call(create_server(runtime=make_runtime(stubs(portfolio=agent))), "analyze_portfolio", {})
    assert [c[0] for c in agent.calls] == ["connect sample", "analyze my portfolio"] and out["text"] == "Portfolio: 1"

async def test_the_default_source_is_the_sample():
    agent = Scripted({})
    await call(create_server(runtime=make_runtime(stubs(portfolio=agent))), "analyze_portfolio", {})
    assert agent.calls[0][0] == "connect sample"

async def test_kite_that_needs_a_login_stops_there_and_returns_the_link():
    agent = Scripted({"connect kite": ("needs_login", "Open the link.", {"login_url": "https://kite.example/l"})})
    out = await call(create_server(runtime=make_runtime(stubs(portfolio=agent))), "analyze_portfolio", {"source": "kite"})
    assert out["status"] == "needs_login" and out["login_url"] == "https://kite.example/l" and len(agent.calls) == 1

async def test_kite_that_is_connected_is_analysed():
    agent = Scripted({"connect kite": ("ok", "Connected.", None)})
    await call(create_server(runtime=make_runtime(stubs(portfolio=agent))), "analyze_portfolio", {"source": "kite"})
    assert [c[0] for c in agent.calls] == ["connect kite", "analyze my portfolio"]

@pytest.mark.parametrize("status", ["error", "clarify", "no_source"])
async def test_a_connection_that_did_not_work_is_returned_without_analysing(status):
    agent = Scripted({"connect sample": (status, "could not connect", None)})
    out = await call(create_server(runtime=make_runtime(stubs(portfolio=agent))), "analyze_portfolio", {})
    assert out["status"] == status and len(agent.calls) == 1

async def test_only_known_sources_are_accepted():
    async with Client(create_server(runtime=make_runtime())) as c:
        with pytest.raises(ToolError):
            await c.call_tool("analyze_portfolio", {"source": "robinhood"})

async def test_the_login_tool_connects_kite():
    agent = Scripted({"connect kite": ("needs_login", "Open the link.", {"login_url": "https://kite.example/l"})})
    out = await call(create_server(runtime=make_runtime(stubs(portfolio=agent))), "portfolio_login", {})
    assert agent.calls[0][0] == "connect kite" and out["login_url"] == "https://kite.example/l"

async def test_the_portfolio_stays_connected_for_the_conversation():
    agent = Scripted({})
    async with Client(create_server(runtime=make_runtime(stubs(portfolio=agent)))) as c:
        await call(None, "portfolio_login", {}, client=c)
        await call(None, "analyze_portfolio", {"source": "kite"}, client=c)
    assert {call_[1].thread_id for call_ in agent.calls} == {agent.calls[0][1].thread_id}


# ================================================================ failures
async def test_an_agent_crash_is_an_error_reply_not_a_protocol_error():
    agents = stubs()
    agents["finance_qa"].raises = RuntimeError("secret internal detail")
    out = await call(create_server(runtime=make_runtime(agents)), "ask_finance", {"question": "What is a SIP?"})
    assert out["status"] == "error" and "secret" not in out["text"]

async def test_a_graph_crash_is_a_generic_tool_error():
    rt = make_runtime()

    class Broken:
        async def ainvoke(self, *a, **k):
            raise RuntimeError("database password is hunter2")
    rt.graph = Broken()
    async with Client(create_server(runtime=rt)) as c:
        with pytest.raises(ToolError) as e:
            await c.call_tool("ask_finance", {"question": "What is a SIP?"})
    assert "hunter2" not in str(e.value) and "went wrong" in str(e.value).lower()

async def test_a_failure_in_the_second_step_of_analysis_is_generic_too():
    rt = make_runtime(stubs(portfolio=Scripted({"connect sample": ("ok", "Connected.", None)})))
    calls = {"n": 0}
    real = rt.graph.ainvoke

    async def flaky(state, *a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom with a secret")
        return await real(state, *a, **k)
    rt.graph = type("G", (), {"ainvoke": staticmethod(flaky)})()
    async with Client(create_server(runtime=rt)) as c:
        with pytest.raises(ToolError) as e:
            await c.call_tool("analyze_portfolio", {})
    assert "secret" not in str(e.value)


# ================================================================ stdout belongs to the protocol
async def test_nothing_is_printed_to_stdout_during_a_call():
    buf = io.StringIO()
    server = create_server(runtime=make_runtime())
    with contextlib.redirect_stdout(buf):
        async with Client(server) as c:
            for tool, args in [("ask_finance", {"question": "What is a SIP?"}), ("explain_term", {"term": "SIP"}),
                               ("get_quote", {"symbols": ["TCS"]}), ("plan_goal", goal()), ("analyze_portfolio", {}),
                               ("portfolio_login", {})]:
                await c.call_tool(tool, args)
    assert buf.getvalue() == ""


# ================================================================ startup and shutdown
async def test_the_runtime_is_built_once_when_the_first_client_connects():
    built = []
    rt = make_runtime()
    server = create_server(build=lambda: built.append(1) or rt)
    assert built == []
    async with Client(server) as c:
        await c.call_tool("ask_finance", {"question": "What is a SIP?"})
        await c.call_tool("ask_finance", {"question": "What is a SIP?"})
    assert built == [1]

async def test_connections_are_closed_at_shutdown():
    store = FakeStore()
    async with Client(create_server(runtime=make_runtime(store=store))) as c:
        await c.call_tool("ask_finance", {"question": "What is a SIP?"})
    assert store.closed_all == 1


# ================================================================ one request at a time per conversation
class Slow(StubAgent):
    active = peak = 0

    async def run(self, query, ctx=None):
        Slow.active += 1
        Slow.peak = max(Slow.peak, Slow.active)
        await asyncio.sleep(0.05)
        Slow.active -= 1
        return await super().run(query, ctx)

async def test_calls_in_one_conversation_run_one_after_the_other():
    Slow.active = Slow.peak = 0
    server = create_server(runtime=make_runtime(stubs(finance_qa=Slow("finance_qa"))))
    async with Client(server) as c:
        await asyncio.gather(*[c.call_tool("ask_finance", {"question": "What is a SIP?"}) for _ in range(3)])
    assert Slow.peak == 1

async def test_different_conversations_run_side_by_side():
    Slow.active = Slow.peak = 0
    server = create_server(runtime=make_runtime(stubs(finance_qa=Slow("finance_qa"))))
    async with Client(server) as c:
        await asyncio.gather(c.call_tool("ask_finance", {"question": "What is a SIP?", "thread_id": "conversation-a"}),
                             c.call_tool("ask_finance", {"question": "What is a SIP?", "thread_id": "conversation-b"}))
    assert Slow.peak == 2


async def test_connections_stay_open_while_another_client_is_still_connected():
    store = FakeStore()
    server = create_server(runtime=make_runtime(store=store))
    async with Client(server) as first:
        async with Client(server) as second:
            await second.call_tool("ask_finance", {"question": "What is a SIP?"})
        assert store.closed_all == 0
        await first.call_tool("ask_finance", {"question": "What is a SIP?"})
    assert store.closed_all == 1
