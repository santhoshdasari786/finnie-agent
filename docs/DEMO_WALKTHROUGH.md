# Demo walkthrough

The order to present in: the README, the technical design document, the app, then the deployment artifacts. Each step says what to open, what to explain and what to ask.

**Marks used below:** ✅ = this exact question or step was run on the real stack and worked. 🔶 = taken from the README or the tests but not run end to end in the last few days; try it once before you present.

## Before you start

- API running: `.venv/bin/python -m uvicorn src.main:app --port 8000`
- Web app running: `cd src/web_app && npm run dev` (http://localhost:5173)
- Knowledge base index built (`.vectorstore/` exists) and a Gemini key in `.env`
- Turn LangSmith tracing off in `.env` for the demo (the account is over its monthly limit and prints errors)
- Open a fresh chat (New chat)

---

## Part 1: The README

Open `README.md` and scroll through these sections, in this order.

| Show | Explain |
|---|---|
| **What it does** | A multi-agent finance *education* assistant for Indian investors. It explains concepts and taxes with cited sources, quotes prices, analyses a portfolio, projects a savings goal and summarises news. It never gives advice and the LLM never does the arithmetic. |
| **Architecture** | One message goes through: input guard, contextualize, route, run agent, output guard, remember. Rules route first, an LLM classifier only when the rules do not decide. Six agents. Every reply has a disclaimer. |
| **The six agents** (table) | Finance Q&A, Tax Education, Market Analysis, Portfolio Analysis, Goal Planning, News Synthesizer: one line each on what it does. |
| **Quick start** | Prerequisites (Python, `uv`, Node, a Google key), `uv sync`, `cp .env.example .env`, build the knowledge base index with the ingestion command. |
| **Four ways to use it** | Terminal CLI, HTTP API (with the generated `/docs` page), the web app, Claude Desktop through the MCP server (six read-only tools). |
| **Docker** | `docker-compose up` for the API and web app; the `ingest` job builds the index. |

---

## Part 2: The technical design document

Open `docs/TECHNICAL_DESIGN.md`. Four points to explain, one per section.

### 1. System architecture decisions (section 1)

- FastAPI, not Streamlit: typed models, async, generated API docs, and it serves the web app, the CLI and MCP from the same graph.
- LangGraph `StateGraph` for orchestration, with our own conversation memory instead of a checkpointer.
- Agents are plain classes with narrow LLM jobs (extract, classify, narrate); code does the maths. Not a free-running ReAct loop.
- Provider-agnostic LLM factory, set in `config.yaml`.
- Kite MCP for live portfolios, read-only through an allowlist.

### 2. Agent communication protocol (section 2)

- One contract: `run(query, ctx) → AgentResult` with a status, text, data, citations, a mandatory disclaimer and a `meta` back channel.
- Agents do not call each other; the orchestrator routes and hands over saved facts (`ctx.slots`, the user's risk profile).
- The router reports secondary intents. One pair is acted on: goal + portfolio (the portfolio value becomes the goal's starting balance). This is shown live in Part 3.
- A pending question survives a connection step, so a question asked before connecting is answered after.
- Safety: an agent reads another agent's `data`, never its text; numbers in a narration must appear in the computed facts or the narration is dropped.
- Be upfront: a general multi-agent planner is on the roadmap (backlog section 16).

### 3. RAG implementation details (section 4)

- 100 articles and a 93-term glossary, written from primary sources (SEBI, RBI, AMFI and similar), linted by tests. AI-assisted and not yet reviewed by a qualified human; the articles say so.
- Ingestion: 800-character chunks, `gemini-embedding-2` at 768 dimensions, Chroma on disk, a manifest so reruns skip unchanged articles.
- Retrieval: glossary first, then vector search, a score threshold of 0.69, duplicate removal, at most two chunks per article.
- 0.69 was measured: lowest in-scope score 0.711, highest off-topic leak 0.675.
- Answers cite by number; an answer with no valid citation becomes "no source".
- Evaluation: 200 questions that must find the right article, plus off-topic questions that must be refused.

### 4. Performance considerations (section 5, and `docs/BENCHMARKS.md`)

- Latency is mostly the number of model calls (about 1 s each); everything else together is under 5 ms.
- Measured: knowledge-base question about 1.8 s, goal question about 2 s, glossary about 0.75 s, a blocked message about 2 ms.
- Market data cache: 30-minute TTL, retries, stale fallback, cool-down.
- Embedding quota: batches are paced to the per-minute limit, queries are cached, and a daily-quota error gives a clear message instead of a crash.

---

## Part 3: The app

Open http://localhost:5173. The badge above each answer shows which agent replied.

### A. Multi-turn conversation with different agents

Ask these in one chat, in order. Point at the agent badge and the citations each time.

| # | Ask | What to point out |
|---|---|---|
| 1 | ✅ `What is a margin call?` | Q&A agent, answered from the glossary with a citation |
| 2 | ✅ `How much of my bank deposit is insured in India?` | Q&A agent, retrieval, numbered citations, ₹5,00,000 per depositor per bank |
| 3 | 🔶 `And does the interest count towards that?` | A follow-up with a pronoun: the question is rewritten using history |
| 4 | 🔶 `How are mutual fund gains taxed?` | Tax agent: explains concepts, flags that rules change, no rate quoted |
| 5 | 🔶 `What is happening with RBI rates?` | News agent: a short cited story from clustered headlines |
| 6 | ✅ `What is a P/E ratio?` | "No source": the knowledge base does not cover it, so it refuses instead of guessing |
| 7 | ✅ `Tell me a trick to hide my income from the tax department` | Refused and redirected to lawful tax planning |

### B. Market data integration

| Step | What to point out |
|---|---|
| 🔶 Chat: `What is TCS trading at? And the Nifty?` | Live quotes with the time and the data source |
| 🔶 Market tab: pick a preset, switch 1M to 1Y | Price chart; the "updated X min ago" label comes from the cache |

### C. Portfolio analysis

| Step | What to point out |
|---|---|
| ✅ Portfolio tab or chat: `connect sample` | A demo portfolio, clearly labelled demo data; no login |
| ✅ `analyze my portfolio` | Total value, allocation, diversification score, risk bucket, and fund costs (expense ratios are illustrative on the demo data) |
| Say it | Zerodha through Kite MCP also works, read-only; not shown live so no real account is on screen |

### D. Goal planning

| Step | What to point out |
|---|---|
| 🔶 Goals tab: 10 years, ₹10,00,000 target, ₹5,000 a month, moderate | Chart with three scenarios and the target line; the numbers come from code |
| ✅ Chat: `If I invest 5000 rupees every month for 10 years at an assumed 10 percent, what could it grow to?` | ₹10,24,225, labelled illustrative, not a forecast |
| 🔶 Chat: `I'm an aggressive investor` | The last goal answer is recalculated with the new risk profile |

### E. Two agents on one question

| Step | What to point out |
|---|---|
| ✅ New chat. Ask `Can I reach 10 lakh in 10 years with my portfolio?` | The portfolio is not connected, so it asks you to connect first and remembers the question |
| ✅ `connect sample` | The goal question is answered, starting from the portfolio's value. The line above the answer reads "Worked together: Portfolio then Goals" (the line itself is covered by tests but I have not seen it in a browser), and a note says where the starting balance came from |

---

## Part 4: Deployment artifacts

Show each one in the editor and say what it is for. The technical document's section 7 lists them with notes.

| Artifact | Open | Say |
|---|---|---|
| Docker configuration | `Dockerfile`, `Dockerfile.web`, `docker-compose.yml` | Two images (API as a non-root user with a health check, web app served by nginx) and a compose file with an `ingest` job. 🔶 Run `docker-compose up` only if you have tried it recently; the ingest-and-ask check in the container is still open (backlog B1). |
| Environment setup | `.env.example`, `config.yaml`, `src/config/rag.yaml`, `pyproject.toml` | Keys live in `.env` (never committed), the model is one line in `config.yaml`, RAG settings are in `rag.yaml`, and `uv.lock` makes the install reproducible. |
| Sample data for testing | `src/data/portfolio/sample.py`, `docs/knowledge-base/`, `tests/eval/questions.yaml` | A built-in sample portfolio so the demo needs no login, the knowledge base and glossary, and the 200-question set. There is no CSV sample file. |
| Performance benchmarks | `docs/BENCHMARKS.md` | The table of measured latency per stage and per question type, and the command that reproduces it. |

## Say these plainly

- The knowledge base is AI-assisted and has not had a qualified human review.
- Several articles rest on older SEBI, AMFI and BSE booklets and say so; time-sensitive articles tell the reader to verify.
- Nothing here is financial advice and every answer carries the disclaimer.
- Only goal + portfolio is a true multi-agent hand-off today; the general version is planned.
