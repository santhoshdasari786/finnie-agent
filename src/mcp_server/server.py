import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field, StringConstraints

from src.api.app import to_response
from src.api.locks import ThreadLocks
from src.api.schemas import THREAD_ID_PATTERN
from src.workflow.graph import ask

log = logging.getLogger(__name__)

SERVER_ERROR = "Something went wrong on the server. Please try again."
INSTRUCTIONS = (
    "Finnie is a personal-finance EDUCATION assistant for Indian investors. It explains concepts, taxes, prices, "
    "goals, portfolios and news. Every answer is educational and is not financial advice. It is read-only: it "
    "cannot place, change or cancel any order. Use ask_finance for any question; the other tools are shortcuts "
    "for one capability. Each tool returns the answer text, citations, structured data and a disclaimer."
)
READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True}

Text = lambda n: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=n)]  # noqa: E731
Symbol = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z0-9&^.\-]{1,20}$")]
ThreadId = Annotated[str | None, Field(pattern=THREAD_ID_PATTERN, description="Optional: reuse a conversation id.")]
Money = Annotated[float, Field(gt=0, le=1e12)]
MoneyOrZero = Annotated[float, Field(ge=0, le=1e12)]


def build_goal_question(*, horizon_years: float, target_amount: float | None, monthly_contribution: float | None,
                        starting_balance: float | None, risk_appetite: str | None,
                        annual_return_pct: float | None) -> str:
    """Structured arguments, written as the sentence a person would say, for the Goal Planning agent."""
    head = ("New goal: " + (f"Can I reach {target_amount:.0f} rupees in {horizon_years:g} years" if target_amount
                           else f"What will I have in {horizon_years:g} years"))
    if monthly_contribution:
        head += f", saving {monthly_contribution:.0f} rupees a month"
    if starting_balance:
        head += f", starting with {starting_balance:.0f} rupees"
    parts = [head + "?"]
    if risk_appetite:
        parts.append(f"My risk appetite is {risk_appetite}.")
    if annual_return_pct is not None:
        parts.append(f"Assume {annual_return_pct:g}% returns.")
    return " ".join(parts)


INDEX_NAMES = {"^NSEI": "Nifty 50", "NIFTY": "Nifty 50", "NIFTY50": "Nifty 50", "^BSESN": "Sensex", "SENSEX": "Sensex"}


def build_quote_question(symbols: list[str]) -> str:
    """The Market agent understands two indexes, by name (Nifty 50, Sensex), and any stock by its ticker."""
    names: list[str] = []
    for symbol in symbols:
        if symbol.startswith("^") and symbol not in INDEX_NAMES:
            raise ToolError(f"The index {symbol} is not supported. Supported indexes: Nifty 50 and Sensex.")
        name = INDEX_NAMES.get(symbol, symbol)
        if name not in names:
            names.append(name)
    return "Quote for " + ", ".join(names)


def _default_build():
    from src.workflow.bootstrap import build_runtime        # imported lazily: it loads models and the vector store
    return build_runtime()


def create_server(runtime=None, build=None) -> FastMCP:
    state = {"runtime": runtime}
    locks = ThreadLocks()
    # stdio: one server process is one client, so one default conversation. A client that wants more passes thread_id.
    default_thread = f"mcp-{uuid.uuid4().hex[:12]}"

    @asynccontextmanager
    async def lifespan(server):
        if state["runtime"] is None:
            state["runtime"] = await asyncio.to_thread(build or _default_build)
        try:
            yield                                   # fastmcp enters this once and leaves it when the LAST client disconnects
        finally:
            await state["runtime"].close()

    mcp = FastMCP("Finnie", instructions=INSTRUCTIONS, lifespan=lifespan)

    async def converse(thread_id: str | None, work) -> dict:
        thread = thread_id or default_thread
        rt = state["runtime"]

        async def say(message: str, agent: str | None = None):
            return await ask(rt.graph, message, thread_id=thread, agent=agent)

        try:
            async with locks.hold(thread):
                result = await work(say)
        except Exception:
            log.exception("tool call failed")
            raise ToolError(SERVER_ERROR) from None
        return to_response(thread, result).model_dump()

    @mcp.tool(annotations=READ_ONLY)
    async def ask_finance(question: Text(2000), thread_id: ThreadId = None) -> dict:
        """Ask Finnie anything about investing, tax, prices, your portfolio, a savings goal or the news. The
        question goes through the safety checks and is routed to the right specialist."""
        return await converse(thread_id, lambda say: say(question))

    @mcp.tool(annotations=READ_ONLY)
    async def explain_term(term: Text(80)) -> dict:
        """Explain a finance term or concept in plain language, with a citation (for example 'expense ratio')."""
        return await converse(None, lambda say: say(f"What is {term}?", "finance_qa"))

    @mcp.tool(annotations=READ_ONLY)
    async def get_quote(symbols: Annotated[list[Symbol], Field(min_length=1, max_length=10)]) -> dict:
        """Get the latest price and change for up to 10 stocks or indexes (for example TCS, RELIANCE, NIFTY50,
        SENSEX), with the time and the data source. Only the Nifty 50 and Sensex indexes are supported."""
        question = build_quote_question(symbols)
        return await converse(None, lambda say: say(question, "market_analysis"))

    @mcp.tool(annotations=READ_ONLY)
    async def plan_goal(horizon_years: Annotated[float, Field(gt=0, le=60)],
                        target_amount: Money | None = None, monthly_contribution: MoneyOrZero | None = None,
                        starting_balance: MoneyOrZero | None = None,
                        risk_appetite: Literal["conservative", "moderate", "aggressive"] | None = None,
                        annual_return_pct: Annotated[float, Field(ge=0, le=30)] | None = None) -> dict:
        """Project a savings goal in three illustrative scenarios (amounts in rupees). Give the horizon in years
        and at least one of: a target amount, a monthly amount, a starting balance. Not a forecast or advice."""
        if target_amount is None and not monthly_contribution and not starting_balance:
            raise ToolError("Give a target amount, a monthly amount or a starting balance.")
        question = build_goal_question(
            horizon_years=horizon_years, target_amount=target_amount, monthly_contribution=monthly_contribution,
            starting_balance=starting_balance, risk_appetite=risk_appetite, annual_return_pct=annual_return_pct)
        return await converse(None, lambda say: say(question, "goal_planning"))

    @mcp.tool(annotations=READ_ONLY)
    async def analyze_portfolio(source: Literal["sample", "kite"] = "sample") -> dict:
        """Analyse a portfolio: allocation, diversification and risk. 'sample' is demo data; 'kite' is a live
        Zerodha account (read-only) and may answer needs_login with a link to open first."""
        async def work(say):
            connected = await say(f"connect {source}", "portfolio")
            return connected if connected.status != "ok" else await say("analyze my portfolio", "portfolio")
        return await converse(None, work)

    @mcp.tool(annotations=READ_ONLY)
    async def portfolio_login() -> dict:
        """Start (or check) the read-only Zerodha Kite login. Returns the link to open in a browser; call
        analyze_portfolio with source 'kite' after approving."""
        return await converse(None, lambda say: say("connect kite", "portfolio"))

    return mcp
