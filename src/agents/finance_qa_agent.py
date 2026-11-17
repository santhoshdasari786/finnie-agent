import asyncio
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.responses import AgentResponse
from src.prompts.qa_prompts import ADVICE_NOTE, SYSTEM_PROMPT, USER_TEMPLATE   # extend your existing import
from src.common.interfaces import QARequest, QAResult
from src.common.models import QASettings
from src.core.contracts import AgentContext, AgentResult
from src.core.guardrails import Guardrails
from src.core.llm import LLMFactory
from src.rag.common.models import ContextSource, RetrievalQuery
from src.rag.retrieval.citations import cite_chunk, cite_glossary, merge_by_source, renumber_markers, used_markers
from src.core.guardrails import GuardVerdict, Guardrails

log = logging.getLogger(__name__)

class FinanceQAAgent:
    name = "finance_qa"
    _system_prompt = SYSTEM_PROMPT
    _forced_category = None
    _disclaimer = None            # None: use settings.disclaimer


    def __init__(self, llm=None, retriever=None, glossary=None, settings=None):
        self._llm = llm or LLMFactory.get_default()

        if retriever is None or glossary is None:
            from src.rag.bootstrap import build_rag
            rag = build_rag()
            retriever, glossary = retriever or rag.retriever, glossary or rag.glossary
            settings = settings or rag.settings
        self._s = settings or QASettings()   
        self._guards = Guardrails(self._s)       # k, limits, messages
        self._retriever, self._glossary = retriever, glossary

    def _from_chunk(self, n, chunk):
        m = chunk.metadata
        return ContextSource(n,chunk.title, chunk.text,cite_chunk(chunk), m.get("last_verified_at"), m.get("risk_level"))

    def _build_user_prompt(self, question, sources, advice):
        blocks = []
        for s in sources:
            head = f"[{s.n}] {s.title}" + (f" (verified {s.verified})" if s.verified else "")
            blocks.append(f"{head}\n{s.text}")
        return USER_TEMPLATE.format(
            advice_note=(ADVICE_NOTE if advice else "") + self._extra_note(question),
            sources="\n\n".join(blocks),
            question=question
        )
    
    async def _generate(self, question, sources, advice):
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=self._build_user_prompt(question, sources, advice))
        ]
        reply = await self._llm.ainvoke(messages)
        return AgentResponse.from_message(reply).text

    async def run(self, query: str, ctx: AgentContext | None = None) -> AgentResult:
        """The shared Agent contract. ctx is optional so `await FinanceQAAgent().run(...)` works standalone.

        Only ctx.category_hint is read for now; honouring ctx.flags (skip our own guard) arrives with the router's guard nodes.
        """
        hint = ctx.category_hint if ctx else None
        flags = ctx.flags if ctx else None
        return (await self.ask(query, category_hint=hint, flags=flags)).to_result(self.name)

    async def ask(self, question, category_hint=None,flags: frozenset[str] | None = None) -> QAResult:
        req = QARequest(question=(question or "").strip(), category_hint=self._forced_category or category_hint)
        
        # 1. guardrails: a block stops everything; flags travel with the message
        # verdict = self._guards.check(question)
        # if verdict.blocked:
        #     return self._result(verdict.reply, "redirect")

        # 1. guardrails. Standalone: check here. Inside the graph already did, so trust its flags.
        if flags is None:
            verdict = self._guards.check(question)
            if verdict.blocked:
                return self._result(verdict.reply, "redirect")
        else:
            verdict = GuardVerdict(flags=frozenset(flags))

        try:
            # 2. glossary: an exact single-term question skips retrieval entirely
            match = self._glossary.lookup(req.question)
            if match and match.ambiguous:
                return self._clarify(match)
            if match:
                sources, route = [self._from_glossary(match.entries[0])], "glossary"
            else:
                # 3. retrieval (blocking embedding + Chroma calls run in a worker thread)
                res = await asyncio.to_thread(
                    self._retriever.retrieve,
                    RetrievalQuery(req.question, category=req.category_hint, k=self._s.k))
                # 4. nothing relevant: say so WITHOUT calling the LLM (it would answer from memory)
                if res.status == "no_source":
                    return self._no_source()
                sources = [self._from_chunk(i, c) for i, c in enumerate(res.chunks, 1)]
                route = "rag"

            # 5. generate from numbered sources, then map [n] markers to citations
            sources =self._fit_context(sources)
            advice = "advice_seeking" in verdict.flags
            text = await self._generate(req.question, sources, advice)
            if not text.strip():
                raise ValueError("empty answer from the model")      # becomes route="error" below; AgentResult forbids blank text
            result = self._finish(text, sources, route)

            result.answer = self._guards.finalize(result.answer, verdict) # distress suffix, appended once
            result.answer = self._check_answer(result.answer)
            return result
        except Exception:
            log.exception("finance_qa failed") # the cause is logged, never shown to the user
            return self._result(self._s.error_message, "error")

    def _extra_note(self, question):
        return ""

    def _check_answer(self, answer):
        return answer


    def _from_glossary(self,entry):
        return ContextSource(1, entry.term, entry.definition, cite_glossary(entry))

    def _result(self, answer, route, citations=None) -> QAResult:
        return QAResult(answer=answer, citations=citations or [],route=route, disclaimer=self._disclaimer or self._s.disclaimer)

    def _clarify(self, match) -> QAResult:
        options = " or ".join(f"{e.term} ({e.sense})" if e.sense else e.term for e in match.entries)
        return self._result(f"Do you mean {options}?", "clarify")

    def _no_source(self) -> QAResult:
        return self._result(self._s.no_source_message, "no_source")

    def _fit_context(self, sources):
        """Sources arrive best-first: keep as many as fit the budget, always at least one."""
        kept, used = [], 0
        for s in sources:
            if kept and used + len(s.text) > self._s.max_context_chars:
                break
            kept.append(s)
            used += len(s.text)
        return kept

    def _finish(self, text, sources, route) -> QAResult:
        by_n = {s.n: s for s in sources}
        used = used_markers(text, set(by_n)) # only real source numbers, in first-use order
        if not used:
            log.warning("uncited answer for route=%s", route)
            return self._no_source()        # an answer that cites nothing is not grounded: no borrowed citations
        text = renumber_markers(text, used, by_n)   # [n] in the text now matches the merged list
        citations = merge_by_source([by_n[n].citation for n in used])
        return self._result(text, route, citations)