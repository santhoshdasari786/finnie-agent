# Technical Design Document

This is the technical design document called for in the capstone submission guidelines ([`../../README.md`](../../README.md) → *Documentation*). It covers system architecture decisions, the agent communication protocol, a design doc for each of the six agents, RAG implementation details, performance considerations (with measured numbers), testing, and the deployment artifacts. Sections 1, 2, 4 and 5 were rewritten on 2026-11-20 to describe what is built; where an older design note was kept, it says so. For setup/run instructions, see [`../README.md`](../README.md).

---

## Table of Contents

- [1. System Architecture Decisions](#1-system-architecture-decisions)
- [2. Agent Communication Protocol](#2-agent-communication-protocol)
- [3. Agents](#3-agents)
- [4. RAG Implementation Details](#4-rag-implementation-details)
- [5. Performance Considerations](#5-performance-considerations)
- [6. Testing Strategy](#6-testing-strategy)
- [7. Deployment Artifacts](#7-deployment-artifacts)

---

## 1. System Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Web framework | **FastAPI**, not Streamlit | Spec FAQ explicitly allows substituting the suggested stack if documented ("*you could use FastAPI instead of Streamlit, but explain your reasoning*"). FastAPI gives typed request/response models, native async (needed for MCP's async client), and auto-generated OpenAPI docs — a better fit for a system meant to expose both an orchestrated workflow and independently-callable agents as an API. |
| Orchestration | **LangGraph** `StateGraph`: `input_guard → contextualize → route → run_agent → output_guard → remember` (`src/workflow/`) | The spec weights the LangGraph workflow at 10% of the grade. A graph gives explicit routing and a place for every guard. Conversation memory is **our own** `ConversationMemory` (per-thread history, saved facts, who is waiting for an answer), not a LangGraph checkpointer, because the agents need to read and write specific facts, not whole graph state. A blocked message goes straight to the reply and skips the agents. |
| Agent implementation | A plain Python class per agent with `async run(query, ctx) -> AgentResult` (`src/agents/`). The LLM is called directly through `LLMFactory`, not through a LangChain `create_agent` ReAct loop | The first design used `create_agent`. The built agents are **deterministic pipelines with narrow LLM jobs** (extract numbers, classify, narrate) because arithmetic and money facts must come from code. A ReAct loop would let the model decide which tool to call and when; here the code decides and the LLM never calculates or advises. |
| Dependency management | **uv** | Single tool for venv + lockfile + dependency groups; fast; `uv sync` is reproducible via `uv.lock`. |
| LLM provider | **Provider-agnostic from day one** (`LLMFactory`, config-driven via `config.yaml`) | The spec recommends Gemini for cost but doesn't mandate it, and grading rewards documented technology choices. Centralizing provider selection in one factory means swapping Gemini ↔ OpenAI ↔ Claude is a one-line config change, never a code change inside an agent. |
| Live portfolio data | **Kite MCP** (`https://mcp.kite.trade/mcp`) instead of only synthetic sample data | The spec's baseline is "portfolio analysis of user input" (synthetic/manual data). Wiring a real brokerage account in via Zerodha's official MCP server is a deliberate reach beyond the base requirement — it's the kind of thing the **Innovation & Future Outlook** bonus rubric rewards, while the read-only tool allowlist (below) keeps it safe. |
| Observability | **LangSmith** tracing via env vars, no code changes | Chosen over Langfuse for now because it's literally three environment variables with LangChain auto-instrumenting every call — the fastest way to see where an agent run is spending time. Langfuse (self-hostable, vendor-neutral) is deferred until the full multi-agent graph exists, where tracing handoffs across agents matters more. |

---

## 2. Agent Communication Protocol

Agents never talk to each other directly, except in one declared case (below). They talk through **one typed contract and one orchestrator**, so any agent can run standalone in a script, as a LangGraph node, behind the HTTP API, or as an MCP tool without its code changing. Source: `src/core/contracts.py`; long form: [`agents/shared_contracts.md`](agents/shared_contracts.md) and [`agents/router_agent.md`](agents/router_agent.md).

### The contract

```python
class Agent(Protocol):
    name: str
    async def run(self, query: str, ctx: AgentContext | None = None) -> AgentResult: ...

class AgentContext(BaseModel):          # what the orchestrator gives an agent
    thread_id: str
    profile: UserProfile                # risk appetite, knowledge level, jurisdiction
    history: list[Turn]                 # the last few turns
    flags: frozenset[str]               # from the input guard: advice_seeking, financial_distress
    slots: dict                         # THIS agent's saved facts for the thread (e.g. the goal numbers)

class AgentResult(BaseModel):           # what every agent returns, and the only thing that crosses a boundary
    agent: str
    status: "ok" | "no_source" | "clarify" | "redirect" | "needs_login" | "error"
    text: str                           # what the user reads; never empty
    data: dict | None                   # machine-readable (chart data, metrics); never parsed back out of text
    citations: list[Citation]
    disclaimer: str                     # mandatory
    meta: dict                          # routing and memory hints, see below
```

Invariants every agent keeps (one shared contract test checks them): `run()` does not raise, failures become `status="error"` with a plain message; `needs_login` always carries `data.login_url`; the disclaimer is never empty; numbers in `text` come from code (an LLM narration whose numbers are not all in the computed facts is dropped, `src/core/grounding.py`).

### How a message travels

| Step | Who | What it hands on |
|---|---|---|
| 1. Input guard | deterministic code | a verdict: blocked (empty, too long, self-harm) or allowed with **flags** |
| 2. Contextualize | `ConversationMemory` + an LLM rewriter, only for follow-ups | the question rewritten to stand alone, the thread's history and profile |
| 3. Route | rules, then the agent that is waiting for an answer, then an LLM classifier (strict JSON, confidence floor 0.6, 8 s timeout), then fallback to concept Q&A | a `RoutingDecision`: intent, confidence, source, **secondary intents**, symbols |
| 4. Run agent | one agent, or two (see below) | an `AgentResult` |
| 5. Output guard | deterministic code | disclaimer and distress note appended once |
| 6. Remember | `ConversationMemory` | history, the agent's `meta.learned` facts, who is awaiting an answer |

### What agents say to the orchestrator: `meta`

`meta` is the back channel. Agents put hints there and the workflow acts on them; the API exposes only a safe subset (`retryable`, `awaiting`, `missing`, `collaboration`).

| Key | Meaning | Who reads it |
|---|---|---|
| `awaiting` | "I asked the user a question; send the next short reply to me" | router (the `awaiting` route) |
| `learned` | `slots` (facts to remember for this agent) and `profile` (a stated risk appetite) | `ConversationMemory` |
| `summary` | a one-line version of the answer for the history | memory |
| `collaboration` | `{agents, starting_balance}`: two agents answered this one | the web UI |

### Agents working together

There are three mechanisms, and it is worth being exact about which is which:

1. **Shared state, between turns.** An agent's saved facts (`slots`) and the stated risk appetite (`profile`) live in memory. When the user says "make me an aggressive investor" after a goal answer, the workflow re-runs the goal agent on its saved facts with the new profile (`recalculate_after_profile`).
2. **A pending question across a connection step.** The portfolio agent keeps a question until a source connects, then answers it. The workflow does the same for a goal question: "Can I reach 10 lakh in 10 years with my portfolio?" shows the connect menu, remembers the question, and answers it after `connect sample` or the Kite login.
3. **Two agents on one question (built 2026-11-20, `src/workflow/compose.py`).** The router already reports `goal` first and `portfolio` as a secondary intent. The portfolio agent runs first; its `data.metrics.total_value` becomes the goal agent's `starting_balance` (passed through `ctx.slots`); the reply is the goal agent's, with a one-line note written by code and `meta.collaboration`. If the portfolio is not ready the user sees that, and no projection is made. It is a hand-wired pair, not a general mechanism: the general planner is backlog section 16 (M1 to M8).

The rule that keeps this safe: an agent reads another agent only through `AgentResult.data`, never by parsing its text, and the orchestrator, not an agent, decides who calls whom. Backlog M2 turns the hand-wired pair into a table of allowed hand-offs.

### Entry points and the MCP boundary

The CLI (`src/agents/cli.py`), the HTTP API (`POST /chat`, `docs/API.md`), the React app and the MCP server (`src/mcp_server/`, six read-only tools) all call the same graph or the same agents. Outbound, the portfolio agent reaches Zerodha only through Kite MCP behind a `(tool, mode)` allowlist, so even a bug cannot place an order. Two requests on the same conversation never interleave: the API holds one lock per thread (`src/api/locks.py`).

### Connection-holding agents

The portfolio agent keeps one Kite MCP session open for the whole login-and-query lifecycle (`async with`), because Kite's login state belongs to the session that performed it; see section 5.

---

## 3. Agents

Each agent has its own dedicated design doc — purpose/scope, a detailed architecture diagram, typed I/O, draft system prompt, edge cases, open questions, and a "Definition of Done" checklist tied to the grading rubric. This section is just the index; go to the linked doc for the real brainstorm.

| Agent | Status | Rubric tie | Doc |
|---|---|---|---|
| Finance Q&A | **Implemented** | Educational Content (8%), RAG Implementation (8%) | [`docs/agents/finance_qa_agent.md`](agents/finance_qa_agent.md) |
| Portfolio Analysis | **Implemented** (live Kite and sample) | Portfolio Analysis (7%) | [`docs/agents/portfolio_agent.md`](agents/portfolio_agent.md) |
| Market Analysis | **Implemented** | Real-time Data Integration (7%), Market Intelligence (5%) | [`docs/agents/market_analysis_agent.md`](agents/market_analysis_agent.md) |
| Goal Planning | **Implemented** | Deliverables — goal planning w/ risk appetite | [`docs/agents/goal_planning_agent.md`](agents/goal_planning_agent.md) |
| News Synthesizer | **Implemented** | none named — build last among core+1 | [`docs/agents/news_synthesizer_agent.md`](agents/news_synthesizer_agent.md) |
| Tax Education | **Implemented** | none named — build last | [`docs/agents/tax_education_agent.md`](agents/tax_education_agent.md) |

**Cross-agent notes worth remembering while building the rest:**
- Market Analysis uses yfinance behind a provider registry, wrapped in a cache (see section 5); Kite and Alpha Vantage can be registered behind the same interface.
- Finance Q&A and Tax Education share one vector store, differentiated only by a `category` metadata filter — don't build two knowledge bases.
- Goal Planning gets its starting balance from the Portfolio agent when the question says "my portfolio", but the hand-off is made by the **workflow** (`src/workflow/compose.py`), not by the goal agent calling the portfolio agent, so the goal agent stays a leaf. See section 2.
- Portfolio Analysis computes its metrics (total value, allocation, diversification, risk bucket, fund costs) in pure Python and asks the LLM only to narrate them; the same "compute in code, narrate with the LLM" pattern applies to every agent that does arithmetic.

---

## 4. RAG Implementation Details

Implemented in `src/rag/`, configured by `src/config/rag.yaml`. Every stage is a registered component (`@register("chunker", "recursive")` and so on), so a loader, chunker, embedder, store or post-processor is swapped in the config, not in code. Content plan and article template: [`knowledge-base/content-backlog.md`](knowledge-base/content-backlog.md).

### What is in the knowledge base

100 Markdown articles in `docs/knowledge-base/articles/` (7 topics: foundations, products, growth-portfolio, costs-taxes, safety-regulation, behaviour-risk, worked-examples) plus a 93-term glossary (`glossary.yaml`). Each article has front matter (id, title, topic, summary, source URLs, claim-to-source notes, jurisdiction, risk level, last-verified date, related articles) and fixed sections (Purpose, Core Concepts, Worked Example, Misconceptions, Source References, Review Metadata). A lint (`tests/kb/`) enforces the structure, a word range, working links, no advice wording, a "verify" reminder and no quoted rates on time-sensitive articles, and at least one retrieval question per article. Articles are AI-assisted drafts from primary sources; none has had a qualified human review, and each says so.

### Ingestion (`python -m src.rag.ingestion.cli`)

| Stage | Choice |
|---|---|
| Loader | Markdown files with front matter; the front matter becomes chunk metadata |
| Chunker | recursive character split, 800 characters with 100 overlap, splitting on headings first, then paragraphs, lines and sentences. Chunk id = `doc:index:hash` |
| Embedder | Gemini `gemini-embedding-2`, 768 dimensions, with a document prefix (`title: … | text: …`) and a different query prefix (`task: search result | query: …`). Batches of up to 64, paced to a per-minute budget, retried with doubling waits, and a daily-quota error is raised at once instead of retried |
| Store | Chroma, embedded and persisted on disk. The collection name includes the model and size (`finance_kb__gemini-embedding-2__768`), so changing the embedder creates a new index instead of mixing vectors |
| Manifest | SQLite: per document, the hash of its body and the model id. A rerun skips unchanged articles, so ingestion is **incremental**. Metadata alone is not hashed (known gap KB7: a front-matter-only edit is not re-indexed) |

### Retrieval (`src/rag/retrieval/`)

1. **Glossary first.** An exact term or alias match answers a "What is X?" question without retrieval (`glossary/matching.py`: short definition-shaped questions only).
2. **Vector search** for the top 4×k chunks (k = 5), optionally filtered by the `topic` metadata field (the Tax agent forces `costs-taxes`).
3. **Post-processors**, in order: a **score threshold of 0.69** (below it a chunk is dropped; if nothing survives the answer is "no source" and the LLM is not called), **near-duplicate removal** (similarity 0.9), and a **cap of two chunks per article**.
4. **Why 0.69:** it was measured, not guessed. On 2026-11-18, over 200 in-scope questions the lowest best score was 0.711, and the highest off-topic question that leaked through scored 0.675, so the cut-off sits in that gap. The gap is narrow (about 0.015 below, 0.02 above), so `tests/eval/` re-checks it against the live index after any change to articles, chunking or the embedder.

### Answering (`src/agents/finance_qa_agent.py`)

Retrieved chunks are numbered `[1]…[n]` and capped at 6,000 characters of context. The prompt tells the model to answer only from the sources and cite by number. The answer's `[n]` markers are mapped back to citations (title, source URL, excerpt, verified date), with two chunks from one article merged into one reference. **An answer with no valid citation becomes "no source"**, which is how an off-topic question that scraped past the threshold is still caught. The Tax agent is the same pipeline with the topic forced, a "concepts, not numbers" prompt and a stronger disclaimer. All answers carry the disclaimer.

### Evaluation

`tests/eval/questions.yaml` has 200 in-scope questions (each with the article that should answer it), off-topic questions that must be refused, and borderline ones tracked but not asserted. `tests/eval/retrieval_eval_test.py` runs them live: the expected article must be in the top three, and off-topic questions must come back as "no source". Last run: 2026-11-18, all passing after one threshold change and two corrected expectations. `scripts/kb_live_check.py` asks a dozen end-to-end questions and prints the answers for a human to read.

---

## 5. Performance Considerations

**Measured numbers** (2026-11-18, real services, paid Gemini tier; full table and method in [`BENCHMARKS.md`](BENCHMARKS.md)):

| Question | median / p95 |
|---|---|
| a blocked message (guard only) | 2.2 ms / 2.4 ms |
| a glossary question | 0.75 s / 0.87 s |
| a price question (cached after the first) | 1.0 s / 1.5 s |
| a goal question | 2.0 s / 2.2 s (3 runs; an earlier 8-run measurement gave 3.5 s / 8.9 s) |
| a knowledge-base question (embed, search, answer) | 1.8 s / 2.7 s |

Findings: latency is the number of model calls times about 1 second (guard, router, glossary lookup, vector search over 934 chunks at 1.2 ms, and calculations together cost under 5 ms); a query embedding is about 0.5 s; a cached quote is about 3,000 times faster than a cold one. The measurements are from a few runs on one laptop, and the benchmark script (`python -m scripts.bench_latency --runs 10`) reproduces them.

Other decisions, each with its reason:

- **Embedding quota and pacing (2026-11-18).** The free tier's 100 requests a minute and 1,000 a day were used up by one re-index plus one eval. The embedder now counts every text in a batch against a per-minute budget (`requests_per_minute: 90`), waits for the window instead of being refused, retries a refused call for about a minute, and caches query embeddings; when the daily quota is gone the user gets "my knowledge base is busy" instead of an error. The project now runs on the paid tier.
- **Two requests on one conversation are serialised** by a per-thread lock, so memory is never written by two answers at once.
- **A composed question costs more.** Goal + portfolio runs the portfolio agent (prices, metrics, a narration call) before the goal agent (extract, narrate); a follow-up that still says "my portfolio" repeats the portfolio step. A per-turn cache and parallel steps are backlog M5/M7.

- **One LLM instance per process.** `LLMFactory.get_default()` caches its instance — every agent that doesn't explicitly inject its own LLM shares one client, avoiding redundant provider SDK initialization.
- **Market data caching (built 2026-11-17, `src/data/market/cache.py`).** `CachedProvider` wraps any `MarketDataProvider`: a 30-minute TTL cache per instrument (history: per instrument and range), exponential backoff (0.5 s, 1 s) on temporary failures only, a stale fallback (an older copy, marked `stale`, when a refresh fails), a 30 s cool-down so an outage is not hammered, and one shared fetch for identical concurrent requests. "Not found" is never cached or retried. All of it is configured in `src/config/app.yaml` under `market_data`. See [`agents/market_analysis_agent.md`](agents/market_analysis_agent.md).
- **MCP connection reuse is not optional — it's required for correctness, not just speed.** Early iterations of the Portfolio Agent called `login()` and the next tool call on what turned out to be two different implicit sessions, which didn't just waste a connection — it silently hung, because Kite's login state is bound to the session that performed it. The fix was holding one `MCPAdapter`/`fastmcp.Client` connection open (via `async with`) across the entire login-and-query lifecycle. Any future connection-holding agent (e.g. Market Analysis, if it also talks to Kite MCP) should follow the same pattern. **Update 2026-11-12:** the hosted server has since moved to OAuth (an unauthenticated client gets `401 no bearer token`) and regrouped its tools (`portfolio`, `session`, `mutual_funds`, … with a `mode` argument, no `login` tool). The held-connection rule still applies, now implemented in `src/data/portfolio/kite.py` (see [`agents/portfolio_agent.md`](agents/portfolio_agent.md)); the old `MCPAdapter` code in `src/agents/portfolio_agent.py` no longer connects.
- **Never block the event loop while a connection is open.** A plain `input()` call (e.g. "press Enter after you've logged in") freezes the whole event loop, including any open MCP connection's ability to service itself. Use `await asyncio.to_thread(input, ...)` for any blocking wait that happens while a connection-holding agent is active.
- **Timeouts around agent calls.** Every `agent.run(...)` call in a connection-holding agent should be wrapped in `asyncio.wait_for(..., timeout=...)` so a server-side hang fails loudly and fast instead of hanging the whole process indefinitely.
- **Tracing over guesswork.** LangSmith is wired up via env vars specifically so questions like "is this slow because of the LLM or the tool call?" are answered by looking at a trace, not by adding print statements.

---

## 6. Testing Strategy

- **Today:** 2,952 automated Python tests (98% line coverage) and 477 web-app tests. No test needs the network or a login: LLMs, providers and the Kite client are replaced by recording fakes. Live checks are separate scripts in `scripts/`. Every change was also mutation-checked (the code deliberately broken to confirm a test notices).
- **Original plan (now done):** an automated suite that mocks `fastmcp.Client` / `MCPAdapter` / `create_agent` so agent logic (tool filtering, response normalization, error handling) is tested without any real network call or login, using `pytest-asyncio` with `asyncio_mode = "auto"` (see `pyproject.toml`). Target: 80%+ coverage per the grading rubric, including edge cases like malformed queries and tool/timeout failures.
- Pure-calculation agents (Goal Planning) are the easiest to hit high coverage on — no mocking required, just assert on the math.

---

## 7. Deployment Artifacts

| Artifact | Where | Notes |
|---|---|---|
| Docker (optional) | `Dockerfile` (API, non-root, health check), `Dockerfile.web` (React build served statically), `docker-compose.yml` (api, web, and an `ingest` job in the `tools` profile), `.dockerignore` | `docker-compose up` gives a healthy API and web app; the API starts with an empty index and answers everything except knowledge-base questions until `docker-compose --profile tools run --rm ingest` is run. The ingest-and-ask check inside the container is still open (backlog B1). Details: README → Docker |
| Environment setup | `.env.example` (keys and tracing flags, no secrets), `config.yaml` (LLM provider and model), `src/config/app.yaml` (router, memory, timeouts, market cache, portfolio default), `src/config/rag.yaml` (RAG), `pyproject.toml` + `uv.lock` (reproducible install), `requirements.txt` (pip fallback) | README → Quick start and Configuration |
| Sample data for testing | the built-in **sample portfolio** (`src/data/portfolio/sample.py`, 7 holdings, demo expense ratios labelled illustrative; `connect sample` needs no login), the knowledge base and glossary, the 200-question retrieval set (`tests/eval/questions.yaml`), and recorded fakes in `tests/` | There is no CSV sample file. Only two portfolio sources are built, `sample` and `kite`; `csv` and `manual` are named in `src/config/app.yaml` (with an unused `sample_path`) but not implemented |
| Performance benchmarks | [`BENCHMARKS.md`](BENCHMARKS.md) and `scripts/bench_latency.py` | measured 2026-11-18 |
| Live check scripts | `scripts/` (`kb_live_check`, `market_live`, `portfolio_live`, `graph_live`, `mcp_check`, `bench_latency`, `eval_retrieval`) | each needs a key or network and says so at the top |

