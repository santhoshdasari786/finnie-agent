import logging
from zoneinfo import ZoneInfo

from langchain_core.messages import HumanMessage, SystemMessage

from src.common.models import QASettings
from src.core.contracts import AgentContext, AgentResult
from src.core.llm import LLMFactory
from src.core.responses import AgentResponse
from src.data.market.symbols import extract_instruments

log = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
SYSTEM = ("You explain market data to a beginner in 2-4 plain sentences. Use ONLY the numbers in DATA. "
          "Never predict, never recommend buying or selling, never call a move a signal.")


def facts_line(q) -> str:
    chg = f"{q.change_pct:+.2f}%" if q.change_pct is not None else "change n/a"
    when = q.as_of.astimezone(IST).strftime("%d %b %H:%M IST")
    note = " · could not refresh, may be out of date" if q.stale else ""
    return f"- {q.instrument.symbol}: {q.price:,.2f} {q.currency} ({chg}) · {q.source}, fetched {when}{note}"


class MarketAnalysisAgent:
    name = "market_analysis"

    def __init__(self, provider, llm=None, settings=None):
        self._provider = provider
        self._llm = llm or LLMFactory.get_default()
        self._s = settings or QASettings()

    @property
    def provider(self):
        return self._provider


    def _result(self, status, text, **kw):
        return AgentResult(agent=self.name, status=status, text=text, disclaimer=self._s.disclaimer, **kw)

    async def run(self, query, ctx: AgentContext | None = None) -> AgentResult:
        wanted = extract_instruments(query)
        if not wanted:
            return self._result("clarify", "Which stock or index? For example: RELIANCE, TCS, Nifty or Sensex.")
        try:
            quotes = await self._provider.quotes(wanted)
        except Exception:
            log.exception("market data failed")
            return self._result("error", self._s.error_message, meta={"retryable": True})
        got = {q.instrument for q in quotes}
        missing = [i.symbol for i in wanted if i not in got]
        if not quotes:
            return self._result("error", f"I couldn't get prices for {', '.join(missing)} right now.",
                                meta={"retryable": True, "missing": missing})
        facts = "\n".join(facts_line(q) for q in quotes)
        text = facts
        try:
            reply = await self._llm.ainvoke([SystemMessage(content=SYSTEM),
                                             HumanMessage(content=f"DATA\n{facts}\n\nQUESTION\n{query}")])
            story = AgentResponse.from_message(reply).text
            if story:
                text = f"{facts}\n\n{story}"
        except Exception:
            log.exception("narration failed; returning the numbers only")
        if missing:
            text += f"\n\nI couldn't find prices for: {', '.join(missing)}."
        return self._result("ok", text,
                            data={"quotes": [q.model_dump(mode="json") for q in quotes], "missing": missing},
                            meta={"provider": getattr(self._provider, "name", "?")})
