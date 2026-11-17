import logging
import re
from zoneinfo import ZoneInfo

from langchain_core.messages import HumanMessage, SystemMessage

from src.common.models import QASettings
from src.core.contracts import AgentContext, AgentResult
from src.core.llm import LLMFactory
from src.core.responses import AgentResponse
from src.data.portfolio.base import SessionExpired
from src.data.portfolio.metrics import PortfolioMetrics, compute_portfolio_metrics
from src.data.portfolio.pricing import price_holdings
from src.data.portfolio.store import ConnectionStore
from src.core.grounding import is_grounded


log = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

_ALIASES = {"zerodha": "kite"}
_FILLER = {"to", "my", "the", "a", "an", "me", "please", "portfolio", "account", "with", "up", "and", "of", "it"}

SYSTEM = ("You describe a user's portfolio to a beginner in 3-5 plain sentences. Use ONLY the numbers in DATA. "
          "Describe, never advise: never tell the user to buy, sell, hold, rebalance or switch, and never predict "
          "returns. This is an analysis tool; it cannot place orders.")
ADVICE = (" The user is asking what to do. Do not answer with an action. Explain what the numbers show and "
          "which factors a person would weigh, and say the right choice depends on their situation.")


def parse_command(text: str, known: set[str]) -> tuple[str, str | None]:
    """('connect'|'disconnect'|'analyze', source name | None | '?unknown')."""
    t = text.lower()
    verb = "disconnect" if re.search(r"\bdisconnect\b", t) else "connect" if re.search(r"\bconnect\b", t) else None
    if verb is None:
        return "analyze", None
    after = re.findall(r"[a-z0-9_]+", t.split(verb, 1)[1])
    for w in after:
        name = _ALIASES.get(w, w)
        if name in known:
            return verb, name
    for w in after:
        if w not in _FILLER:
            return verb, "?" + w
    return verb, None

def _inr(x: float) -> str:
    return f"₹{x:,.2f}"


class PortfolioAnalysisAgent:
    name = "portfolio"

    def __init__(self, store: ConnectionStore, provider, llm=None, settings=None):
        self._store, self._provider = store, provider
        self._llm = llm or LLMFactory.get_default()
        self._s = settings or QASettings()

    def _result(self, status, text, **kw):
        return AgentResult(agent=self.name, status=status, text=text, disclaimer=self._s.disclaimer, **kw)

    async def run(self, query: str, ctx: AgentContext | None = None) -> AgentResult:
        thread = ctx.thread_id if ctx else "default"
        try:
            verb, source = parse_command(query, {n for n, _ in self._store.options()})
            if verb == "connect":
                return await self._connect(thread, source, ctx)
            if verb == "disconnect":
                return await self._disconnect(thread, source)
            return await self._analyze(thread, query, ctx)
        except Exception:
            log.exception("portfolio agent failed")
            return self._result("error", self._s.error_message, meta={"retryable": True})

    def _menu(self, thread: str, lead: str = "") -> AgentResult:
        options = self._store.options()
        lines = [f"- {label}: say `connect {name}`" for name, label in options]
        text = (lead + "I can analyze a portfolio from these sources:\n" + "\n".join(lines)).lstrip()
        return self._result("clarify", text, data={
            "options": [{"name": n, "label": l} for n, l in options],
            "connected": self._store.connected(thread)})

    async def _connect(self, thread: str, source: str | None, ctx: AgentContext | None = None) -> AgentResult:
        if source is None:
            return self._menu(thread)
        if source.startswith("?"):
            return self._menu(thread, f"I don't know a source called '{source[1:]}'.\n\n")
        info = await self._store.connect(thread, source)
        if info.connected:
            pending = self._store.take_pending(thread)
            if pending:
                return await self._resume(thread, info.message, pending, ctx)
            return self._result("ok", f"{info.message} Say 'analyze my portfolio' to see it.")
        if info.login_url:
            return self._result("needs_login", info.message, data={"login_url": info.login_url, "source": source})
        return self._result("clarify", info.message)

    async def _resume(self, thread: str, connected_msg: str, question: str, ctx: AgentContext | None) -> AgentResult:
        try:
            r = await self._analyze(thread, question, ctx, resuming=True)
        except Exception:
            log.exception("answering the pending question failed")
            r = None
        if r is not None and r.status == "ok":
            return r.model_copy(update={"text": f"{connected_msg}\n\n{r.text}"})
        return self._result("ok", f"{connected_msg} I couldn't finish the analysis just now; "
                                  "say 'analyze my portfolio' to try again.")


    async def _disconnect(self, thread: str, source: str | None) -> AgentResult:
        self._store.clear_pending(thread)
        if source and source.startswith("?"):
            return self._menu(thread, f"I don't know a source called '{source[1:]}'.\n\n")
        targets = [source] if source else self._store.opened(thread)      # connected AND half-finished logins
        if not targets:
            return self._result("ok", "Nothing was connected.")
        said = []
        for name in targets:
            instance = self._store.disconnect(thread, name)
            if instance is None:
                said.append(f"{name} wasn't connected.")
            else:
                await self._close(instance)
                said.append(f"Disconnected {name}.")
        return self._result("ok", " ".join(said))

    @staticmethod
    async def _close(instance) -> None:
        close = getattr(instance, "close", None)
        if close:
            try:
                await close()
            except Exception:
                log.exception("closing a portfolio source failed")



    async def _analyze(self, thread: str, query: str, ctx: AgentContext | None,
                       resuming: bool = False) -> AgentResult:
        connected = self._store.connected(thread)
        if not connected:
            self._store.set_pending(thread, query)
            return self._menu(thread, "You haven't connected a portfolio yet.\n\n")
        try:
            holdings = await self._store.holdings(thread)
        except SessionExpired as e:                         # e.g. the Kite session timed out: ask for a fresh login
            if resuming:
                return self._result("error", "I couldn't open your account just now. Please try again.",
                                    meta={"retryable": True})
            self._store.set_pending(thread, query)
            return await self._connect(thread, e.source, ctx)

        if not holdings:
            return self._result("ok", "Your connected portfolio has no holdings yet.", data={"sources": connected})
        priced = await price_holdings(holdings, self._provider)
        try:
            m = compute_portfolio_metrics(priced.holdings)
        except ValueError:
            return self._result("error", "I couldn't price any of your holdings right now.",
                                meta={"retryable": True, "unquoted": priced.unquoted})
        facts = self._facts(m, connected, priced, ctx)
        text = facts
        advice = bool(ctx and "advice_seeking" in ctx.flags)
        try:
            reply = await self._llm.ainvoke([SystemMessage(content=SYSTEM + (ADVICE if advice else "")),
                                             HumanMessage(content=f"DATA\n{facts}\n\nQUESTION\n{query}")])
            story = AgentResponse.from_message(reply).text
            if story and not is_grounded(story, facts, query):
                log.warning("narration added numbers that are not in the facts; dropped it")
                story = ""
            if story:
                text = f"{facts}\n\n{story}"

        except Exception:
            log.exception("narration failed; returning the numbers only")
        return self._result("ok", text, data={"metrics": m.model_dump(mode="json"), "sources": connected},
                            meta={"price_sources": priced.sources})

    def _facts(self, m: PortfolioMetrics, connected: list[str], priced, ctx) -> str:
        demo = " (demo data)" if "sample" in connected else ""
        if priced.as_of:
            when = priced.as_of.astimezone(IST).strftime("%d %b %H:%M IST")
            prices = f"Prices: {', '.join(priced.sources)}, fetched {when}"
        else:
            prices = "Prices: from your broker"
        lines = [f"Portfolio: {_inr(m.total_value)} across {len(m.holdings)} holdings · "
                 f"source: {', '.join(connected)}{demo}", prices]
        for h in m.holdings:
            pnl = f"  ({h.pnl_pct:+.2f}%)" if h.pnl_pct is not None else ""
            lines.append(f"- {h.symbol:<12}{h.allocation_pct:>6.2f}%  {_inr(h.value)}{pnl}")
        lines.append("Allocation by class: " + " · ".join(
            f"{k.replace('_', ' ')} {v:.1f}%" for k, v in sorted(m.by_asset_class.items(), key=lambda kv: -kv[1])))
        lines.append(f"Diversification score: {m.diversification_score:.2f} (0 = a single holding, 1 = very spread out)"
                     f" · Risk profile: {m.risk_assessment}")
        stated = ctx.profile.risk_appetite if ctx else None
        if stated and stated != m.risk_assessment:
            lines.append(f"Your stated risk appetite is {stated}; this portfolio looks {m.risk_assessment}.")
        if m.unpriced:
            lines.append(f"I couldn't price: {', '.join(m.unpriced)} (left out of the totals).")
        if m.unclassified:
            lines.append(f"No asset class for: {', '.join(m.unclassified)} (treated as higher risk).")
        return "\n".join(lines)


