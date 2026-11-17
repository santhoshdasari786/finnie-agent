# Finnie: project recap (end to end, as of 2026-11-16)

Finnie is a multi-agent personal-finance **education** assistant. All six agents in the spec are working. State of the tests: **1550 passed, 15 xfailed** (plus 173 in the web app). An HTTP API (`POST /chat` and friends, see `docs/API.md`) sits in front of the graph, an MCP server (`src/mcp_server/`, see `docs/agents/mcp_server.md`) exposes six read-only tools to Claude Desktop, and a React front end (`src/web_app/`, see `docs/WEB_APP.md`, 173 tests) talks to it.

## 1. The request path

```
                         one message from the user
                                   │
   ┌───────────────────────────────▼────────────────────────────────┐
   │ 1 INPUT GUARD     empty / too long / self-harm → blocked, no LLM │
   │                   flags: financial_distress, advice_seeking     │
   │ 2 CONTEXTUALIZE   follow-up? rewrite using history (LLM, gated)  │
   │ 3 ROUTE           hint → rules → awaiting agent → classifier     │
   │                   → fallback concept Q&A                         │
   │ 4 AGENT           one of five, each returns one AgentResult      │
   │ 5 OUTPUT GUARD    disclaimers, distress suffix appended once     │
   │ 6 REMEMBER        history, pending question, who is awaited      │
   └──────────────────────────────────────────────────────────────────┘
```

A LangGraph state graph in `src/workflow/` (`graph.py`, `nodes.py`, `state.py`). A blocked message goes straight to the reply and skips steps 2, 3, 4 and 6.

## 2. Layer by layer

| Layer | Where | What it does |
|---|---|---|
| Knowledge base | `src/rag/`, `docs/knowledge-base/` | 15 articles plus a glossary, Gemini embeddings, Chroma. Retrieval score below 0.66 means "no source" and the LLM is not called |
| Contracts | `src/core/contracts.py` | every agent: `run(query, ctx) → AgentResult` with status `ok / no_source / clarify / redirect / needs_login / error`, text, citations, data, meta and a mandatory disclaimer |
| Guardrails | `src/core/guardrails.py` | deterministic, no LLM. Blocks empty, over-long and self-harm messages; flags distress and advice-seeking, which change how agents answer |
| Router | `src/workflow/router.py`, `classifier.py` | rules (`goal > portfolio > tax > market > news`), then a gated LLM classifier (strict JSON, confidence floor 0.6, 8 s timeout), then fallback to concept Q&A. `off_topic` and `clarify` are answered by the router |
| Memory | `src/workflow/memory.py` | per-thread history (6 turns), follow-up detection and an LLM rewriter, `awaiting` (which agent asked a question), and the portfolio's pending question in `ConnectionStore` |

## 3. The agents

| Agent | How it works |
|---|---|
| **Finance Q&A** | glossary hit skips retrieval; otherwise retrieve, generate from numbered sources, map `[n]` to citations. An answer with no valid citation becomes "no source" (the ELSS lesson) |
| **Tax Education** | thin subclass of Q&A: topic forced to `costs-taxes`, its own prompt ("concepts, not numbers"), a stronger disclaimer, a note when the question asks for a rate, a caution if a figure still appears |
| **Market Analysis** | yfinance by default (no login) behind a provider registry. Quotes carry `as_of` and `source`. Resolves names such as Nifty and Reliance |
| **Portfolio** | sources behind a registry: a sample portfolio, or live Zerodha through Kite MCP with OAuth. Read-only through a `(tool, mode)` allowlist. One login per session until `disconnect`. Metrics (allocation, diversification, risk bucket) are pure Python; the LLM only narrates. A question asked before connecting is answered after |
| **Goal Planning** | the LLM turns words into numbers (lakh, crore, "k", "assuming 12%"); `goal_math` computes a projection, the monthly amount needed, or the time to reach a target, at three illustrative rates or the user's own |
| **News Synthesizer** | Google News RSS behind a swappable provider (no key); noise filter, relevance filter, near-duplicate clustering; the LLM writes a cited story that is vetted in code (cites real headlines, no trading signal, no invented numbers) |

## 4. The design rule behind it

**The LLM never calculates and never advises.** Numbers come from code. The LLM extracts, classifies or narrates, and every failure falls back to something safe.

## 5. How it was built

- Test first, then proved with a reference implementation, then mutation-checked (deliberately breaking the code to see the tests notice).
- Lessons worth keeping: Kite's server changed twice, so read it live, not from docs; models return `reply.content` as a list of parts, so always read replies through `AgentResponse.from_message`; run every LLM-touching step once on the live model, because a fake LLM cannot catch provider quirks.

## 6. Known weaknesses (found 2026-11-15 from a real session)

1. Memory is a transcript, not state. Facts such as "₹30,000 a month" live only in text and are re-derived by the LLM each turn.
2. A repeated vague question ("can I retire at 50?") asks the generic question again, ignoring what the thread already knows.
3. The original intent ("retire") is dropped after the first clarification.
4. Stated preferences are never saved: nothing assigns `risk_appetite`, and `profile` in the graph state is never filled.
5. Assistant turns are stored cut at 500 characters, so the numbers in a long answer are the part that is lost.
6. Memory is in one process; the CLI uses one fixed thread id.

**Fixed on 2026-11-15/16 by Memory v2:** the session now saves a profile and per-agent slots, answers are summarised in history, and narration is grounded. See `shared_contracts.md` section 9.

## 7. Not done yet

`csv` and `manual` portfolio sources · price cache · risk questionnaire · inflation and step-up SIPs · a phrasing eval for the goal agent · Q&A latency measurement (backlog C15).
