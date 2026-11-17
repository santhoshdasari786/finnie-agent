"""Where does the time go? Latency of each stage, then of whole questions, on the real stack.

Run from the project root:   .venv/bin/python -m scripts.bench_latency            (add --runs 10 for tighter numbers)
Needs GOOGLE_API_KEY and a built vector store. Uses real services: Gemini (LLM and embeddings), Chroma, Yahoo Finance.

What it measures
  per stage    guard · router rules · glossary lookup · Chroma search · query embedding · one LLM call · market quote and
               history, cold and cached
  end to end   the whole LangGraph for a glossary question, a knowledge-base question, a goal question, a price question
               and a blocked message

Notes
  * Each number is milliseconds, median (p50) and 95th percentile (p95) over --runs repetitions (LLM and end-to-end stages use
    fewer, to be kind to the free tier).
  * A stage that cannot run (for example the embedding quota is used up) is reported as SKIPPED with the reason, never faked.
  * LangSmith tracing is switched off so it cannot add network time of its own.
  * Prints a Markdown table, ready for docs/BENCHMARKS.md.
"""
import argparse
import asyncio
import math
import os
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

for _name in ("LANGCHAIN_TRACING_V2", "LANGCHAIN_TRACING", "LANGSMITH_TRACING", "LANGSMITH_TRACING_V2"):
    os.environ[_name] = "false"

from dotenv import load_dotenv  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from src.core.guardrails import Guardrails  # noqa: E402
from src.common.models import QASettings  # noqa: E402
from src.rag.glossary.yaml_glossary import YamlGlossary  # noqa: E402
from src.workflow.router import route_by_rules  # noqa: E402

ROWS: list[tuple[str, str, str]] = []                      # (group, stage, result text)


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1)]


def fmt(ms: float) -> str:
    return f"{ms * 1000:,.0f} µs" if ms < 0.5 else f"{ms:,.1f} ms"


def summarize(ms: list[float]) -> str:
    if len(ms) == 1:
        return f"{fmt(ms[0])} (1 run)"
    return f"{fmt(statistics.median(ms))} / {fmt(pct(ms, 0.95))}  (n={len(ms)})"


def record(group: str, stage: str, ms: list[float] | None, skipped: str | None = None) -> None:
    ROWS.append((group, stage, summarize(ms) if ms else f"SKIPPED: {skipped}"))
    print(f"  {stage:58} {ROWS[-1][2]}", flush=True)


def time_sync(fn, runs: int) -> list[float]:
    out = []
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t) * 1000)
    return out


async def time_async(fn, runs: int, pause: float = 0.0) -> list[float]:
    out = []
    for i in range(runs):
        t = time.perf_counter()
        await fn(i)
        out.append((time.perf_counter() - t) * 1000)
        if pause:
            await asyncio.sleep(pause)
    return out


def why(e: Exception) -> str:
    text = str(e)
    return text[:90] if text else type(e).__name__


async def main(runs: int) -> None:
    llm_runs = max(3, runs // 2)
    e2e_runs = max(3, runs // 3)
    print(f"Finnie latency benchmark · {datetime.now():%Y-%m-%d %H:%M} · {platform.platform()} · Python {platform.python_version()}")
    print("median / p95\n")

    # -------------------------------------------------------------- deterministic stages (no network)
    print("[no network]")
    guards = Guardrails(QASettings())
    record("No network", "input guard (empty / length / self-harm / flags)", time_sync(lambda: guards.check("What is a SIP and how does it work?"), 2000))
    record("No network", "router rules (keyword routing)", time_sync(lambda: route_by_rules("Can I reach 50 lakh in 10 years saving 20000 a month?"), 2000))
    glossary = YamlGlossary(ROOT / "docs" / "knowledge-base" / "glossary.yaml")
    record("No network", "glossary lookup (93 terms)", time_sync(lambda: glossary.lookup("What is a margin call?"), 2000))

    # -------------------------------------------------------------- vector store and embeddings
    print("\n[knowledge base]")
    from src.rag.bootstrap import build_rag
    rag = build_rag()
    store = rag.retriever.store
    col = store._col
    sample = col.get(limit=1, include=["embeddings"])["embeddings"][0]
    record("Knowledge base", f"Chroma vector search, top 20 of {store.info().count} chunks (no embedding)",
           time_sync(lambda: store.search(list(sample), k=20), 200))

    embedder = rag.retriever.embedder
    embedder._cache.clear()
    queries = [f"{q} {i}" for i, q in enumerate(["What is a bond?", "How does a SIP work?", "Explain deposit insurance", "What is inflation?",
                                                  "What is an expense ratio?", "How are dividends taxed?", "What is a margin call?",
                                                  "Why diversify?", "What is a Ponzi scheme?", "What is CAGR?"] * 3)][:runs]
    try:
        record("Knowledge base", "query embedding (Gemini, one text, cold)",
               await time_async(lambda i: asyncio.to_thread(embedder.embed_query, queries[i]), len(queries), pause=0.8))
        record("Knowledge base", "query embedding again (cache hit)", time_sync(lambda: embedder.embed_query(queries[0]), 500))
        full = []
        for q in queries[:llm_runs]:
            t = time.perf_counter()
            await asyncio.to_thread(rag.retriever.retrieve, __import__("src.rag.common.models", fromlist=["RetrievalQuery"]).RetrievalQuery(q + " tax"))
            full.append((time.perf_counter() - t) * 1000)
        record("Knowledge base", "whole retrieval (embed + search + filters), cold", full)
    except Exception as e:                                       # noqa: BLE001
        reason = "embedding quota used up for the day" if "daily" in str(e).lower() else why(e)
        for stage in ("query embedding (Gemini, one text, cold)", "query embedding again (cache hit)",
                      "whole retrieval (embed + search + filters), cold"):
            record("Knowledge base", stage, None, reason)

    # -------------------------------------------------------------- the language model
    print("\n[language model]")
    from langchain_core.messages import HumanMessage, SystemMessage
    from src.core.llm import LLMFactory
    llm = LLMFactory.get_default()
    context = " ".join(["Compound interest means earning returns on both the original amount and on earlier returns."] * 40)
    messages = [SystemMessage(content="Answer only from the sources. Cite as [1]."),
                HumanMessage(content=f"[1] Compound interest\n{context}\n\nQUESTION: What is compounding?")]
    try:
        record("Language model", f"one answer from ~4,000 characters of sources ({os.getenv('LLM_LABEL', 'config.yaml model')})",
               await time_async(lambda i: llm.ainvoke(messages), llm_runs, pause=1.0))
        short = [HumanMessage(content="Reply with the single word: ready")]
        record("Language model", "a tiny reply (classifier-sized call)", await time_async(lambda i: llm.ainvoke(short), llm_runs, pause=1.0))
    except Exception as e:                                       # noqa: BLE001
        record("Language model", "one answer from ~4,000 characters of sources", None, why(e))

    # -------------------------------------------------------------- market data
    print("\n[market data, Yahoo Finance]")
    from src.data.market.base import PROVIDERS
    import src.data.market.yfinance_provider  # noqa: F401  (importing registers "yfinance")
    from src.data.market.cache import build_market_provider
    from src.core.config import load_app_config
    from src.data.market.symbols import resolve_instrument as resolve
    provider = build_market_provider(PROVIDERS["yfinance"](), load_app_config().market_data)
    tcs, nifty = resolve("tcs"), resolve("nifty")
    try:
        cold_q = []
        for sym in ("tcs", "infy", "reliance", "wipro", "itc")[:max(3, runs // 2)]:
            t = time.perf_counter()
            await provider.quotes([resolve(sym), nifty] if sym == "tcs" else [resolve(sym)])
            cold_q.append((time.perf_counter() - t) * 1000)
        record("Market data", "quote, cold (a different symbol each time)", cold_q)
        record("Market data", "quote, cached", await time_async(lambda i: provider.quotes([tcs, nifty]), 200))
        h = time.perf_counter()
        await provider.history(tcs, "1y")
        record("Market data", "price history, 1 year, cold", [(time.perf_counter() - h) * 1000])
        record("Market data", "price history, cached", await time_async(lambda i: provider.history(tcs, "1y"), 200))
    except Exception as e:                                       # noqa: BLE001
        record("Market data", "quote and history", None, why(e))

    # -------------------------------------------------------------- whole questions through the graph
    print("\n[end to end through the LangGraph]")
    from src.workflow.bootstrap import build_runtime
    from src.workflow.graph import ask
    rt = build_runtime()
    cases = [
        ("a blocked message (guard only, no model)", "I want to die"),
        ("a glossary question (\"What is a margin call?\")", "What is a margin call?"),
        ("a price question (\"TCS and Nifty price\", cached after the first)", "TCS and Nifty price"),
        ("a goal question (extract, calculate, narrate)", "Can I reach 50 lakh in 10 years saving 20000 a month?"),
        ("a knowledge-base question (retrieve, then answer)", "How much of my bank deposit is insured in India?"),
    ]
    for label, question in cases:
        try:
            ms = []
            statuses = set()
            for i in range(e2e_runs):
                t = time.perf_counter()
                r = await ask(rt.graph, question, thread_id=f"bench-{abs(hash(question)) % 10**6:06d}-{i:03d}")
                ms.append((time.perf_counter() - t) * 1000)
                statuses.add(r.status)
                await asyncio.sleep(1.0)
            if statuses == {"error"}:
                record("End to end", label, None, "every run ended in an error reply (see the stage above for the cause)")
            else:
                record("End to end", label, ms)
        except Exception as e:                                   # noqa: BLE001
            record("End to end", label, None, why(e))
    await rt.close()

    print("\n\n### Markdown\n")
    print("| Group | Stage | median / p95 |\n|---|---|---|")
    for group, stage, text in ROWS:
        print(f"| {group} | {stage} | {text} |")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", type=int, default=10, help="repetitions for the cheap stages (default 10)")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.runs)) or 0)
