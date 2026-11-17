# Finance Q&A Agent: Backlog (deferred work and known gaps)

Single place for everything deliberately postponed while building the Q&A agent, the guardrails and the RAG
pipeline. Companion to [`agents/finance_qa_agent.md`](agents/finance_qa_agent.md) and
[`TECHNICAL_DESIGN.md`](TECHNICAL_DESIGN.md).

**Priority:** P1 = needed before the agent is trustworthy · P2 = quality / robustness · P3 = scale or nice-to-have.
**Status:** `open` · `verify` (believed done or broken, needs a check) · `decision` (needs a call, not code).

How items get here: when a test is marked `xfail` (see `tests/core/guardrails_layers_test.py`) or a build
step is skipped on purpose, add a row with the *why*. Delete the row when it ships.

---

## 1. Guardrails (`src/core/guardrails.py`)

Tests: `tests/core/guardrails_layers_test.py`. Gaps are `xfail`; when one is fixed it XPASSes, so remove its mark.

| # | Item | Why / evidence | Pri | Status |
|---|---|---|---|---|
| G1 | Fix `self.s` vs `self._s` mismatch | Empty input raises `AttributeError` (`_s` is never set) | P1 | done |
| G2 | Fix `from logging import log` | `logging.log` is a function; `_block` raises `AttributeError: 'function' object has no attribute 'info'`. Use `log = logging.getLogger(__name__)` | P1 | done |
| G3 | Collect flags instead of returning early | Distress and advice branches `return` immediately, so flags never combine ("lose my house, should I sell?") and injection is unreachable for them | P1 | done |
| G4 | Return the collected flags at the end | Final `return GuardVerdict()` discards every flag; advice and injection flags are lost | P1 | done |
| G5 | Typo `"Pleasekeep"` in the too-long reply; `catgegory` parameter name; stray `;` | Cosmetic, but user-visible | P2 | done |
| G6 | Wire the verdict into the agent | `blocked` → `QAResult(route="redirect")`; `advice_seeking` → `ADVICE_NOTE` in prompt; `financial_distress` → a calm-framing note + `finalize()` suffix; `injection_attempt` → log only | P1 | open |
| G7 | Self-harm check before the length gate | A long message ending in "I want to die" currently gets the "too long" reply, not the supportive one. Scan the first ~2000 chars for self-harm first | P1 | decision |
| G8 | Review the self-harm and distress message wording | Highest-stakes text in the system. No invented phone numbers; add numbers only from a verified source, with human review | P1 | decision |
| G9 | Accepted false positive: insurance "suicide clause" question | Broad self-harm matching blocks it. Revisit with real usage; consider a narrow allowlist | P3 | decision |
| G10 | Negation ("I'm *not* going to lose my house") still flags distress | Harmless (extra supportive line), but noisy | P3 | decision |
| G11 | Corporate "bankruptcy" (bond issuer risk) flags personal distress | Pattern is too literal | P3 | open |
| G12 | Normalize text before matching | NFKC, strip zero-width characters, collapse whitespace. Measure length on the RAW text, match on the normalized text | P2 | open |
| G13 | Advice-pattern gaps | "shall I", "do you recommend", "a good buy", "can I put all my money in..." | P2 | open |
| G14 | Typos ("shuld i buy") | Fuzzy step, or accept. Measure frequency in logs first | P3 | decision |
| G15 | Hinglish / Hindi (advice and self-harm) | Regexes cannot cover it. Evaluate an LLM classifier for self-harm only (cost vs recall) | P2 | open |
| G16 | Indirect self-harm phrasing ("I can't go on") | Not matched | P2 | open |
| G17 | Token-based length limit | 300 CJK characters pass a 500-character cap but cost far more tokens | P3 | open |
| G18 | Single-character input passes | Ends as `no_source`. Block or accept? | P3 | decision |
| G19 | Refactor to a rule table | A `Rule` dataclass already exists in `src/common/models.py`; replace repeated `if _X.search(...)` blocks once the layers settle | P3 | open |
| G20 | Patterns and messages into `rag.yaml` | So non-programmers can review wording | P3 | open |
| G21 | Count verdict categories in logs | Know how often each rule fires; feeds the eval set | P2 | open |
| G22 | Delete the stub `tests/core/guardrails_test.py` | Its assertion (`is not True`) can never fail and it has a module-level `print` that runs on import | P2 | open |
| G23 | Distress pattern misses common phrasing | Graded question #9 ("I lost my job and can't pay my credit card EMI") got **no** distress flag, so no supportive suffix. The pattern needs `can't pay my <anything> EMI`, "credit card", "lost my job", "laid off", "unemployed", "behind on payments". Add the cases to `TestDistress` first. Fixed with named pattern pieces; `TestDistress` extended (90 guardrail tests passing). | P1 | done |
| G24 | Curly apostrophes defeated the patterns | `I don’t want to live` (U+2019) was missed by the self-harm pattern and `can’t pay` by the distress pattern. `check()` now normalizes `’` and `‘` to `'` before matching. Pinned by tests (`TestSelfHarm`, distress) | P1 | **done 2026-11-03**: curly-apostrophe cases added to `guardrails_layers_test.py` (self-harm and distress) |
| G25 | Recorded decision: hypothetical job loss is not flagged | `"What happens to my SIP if I lose my job?"` is planning, not distress (the pattern uses `lost` / `losing`, not `lose`). Past loss (`"I lost my job last year…"`) is flagged and accepted. Pinned by tests; do not change without a decision | P3 | decision (pinned) |
| G26 | Remove the stale `@gap` mark on `TestInjection.test_should_flag` | The flag is returned now, so those 4 tests report XPASS. The `@gap` mark is commented out. | P3 | done |
| G27 | More distress phrasing | Future or ongoing hardship (`"I might lose my job"`, `"salary delayed"`, `"can't make ends meet"`, `"living paycheck to paycheck"`). Add as xfail cases first, then decide how alarmist to be | P3 | open |

## 2. Agent (`src/agents/finance_qa_agent.py`)

| # | Item | Why | Pri | Status |
|---|---|---|---|---|
| A1 | Fix imports | `from prompts.qa_prompts import ...` needs the `src.` prefix; `from logging import log` (same bug as G2) | P1 | done |
| A2 | Remove the duplicate Pydantic `Citation` in `src/common/interfaces.py` | Mismatch with the `rag.common.models.Citation` dataclass: passing the dataclass into the Pydantic version raises `ValidationError`. Import the dataclass instead. The Pydantic duplicate is gone; `interfaces.py` imports the one dataclass `Citation`. | P1 | done |
| A3 | Add `"error"` to `QAResult.route` | Needed to represent LLM / retrieval failures. Done 2026-11-02: `"error"` is in the route Literal and the stray field was removed; both suites green (129 passed). | P1 | done |
| A4 | Write `_generate`, `_clarify`, `_no_source`, `_finish`, `_fit_context` | `run()` calls them; they do not exist yet. `_from_chunk`, `_build_user_prompt`, `_generate` are written; `_clarify`, `_no_source`, `_finish`, `_fit_context` are not. All helpers exist: `_from_chunk`, `_build_user_prompt`, `_generate`, `_from_glossary`, `_result`, `_clarify`, `_no_source`, `_fit_context`, `_finish`. | P1 | done |
| A5 | Split `qa_prompts.py` into `SYSTEM_PROMPT` + `USER_TEMPLATE` | The current single template has literal placeholders for a variable-length source list. `SYSTEM_PROMPT` and `USER_TEMPLATE` exist and are used. | P1 | done |
| A6 | Wire the glossary after guardrails | Ambiguous term → clarify (no LLM call); single hit → one numbered source. Verified live: "What is an expense ratio?" now routes to `glossary` and returns the glossary definition with a citation. | P1 | done |
| A7 | `no_source` must skip the LLM | Prove with a fake LLM that records calls. Covered by `test_no_chunks_returns_fixed_message_without_calling_llm`. The *trigger* is still the untuned threshold (R14). | P1 | done |
| A8 | Citation flow in `_finish` | `used_markers` → `renumber_markers` → `merge_by_source`; log a warning when an answer is uncited. Verified live: `citations` is non-empty on all ten graded questions. Polish items A22 and A23 remain. | P1 | done |
| A9 | Error handling | Gemini 429 / timeouts / empty collection become `route="error"` with a friendly message, not a stack trace. The Q&A agent now returns `route="error"` on failure (once A3 is fixed). Portfolio, Market and the others still need it. | P2 | partial |
| A10 | Use stored metadata in answers | `risk_level: time-sensitive` → "verified {date}; check current rules". `jurisdiction: global` answering an India question → flag it | P2 | open |
| A11 | Follow-up questions | Needs `history` on `QARequest` and a "condense question" step. v1: each question is independent (document it) | P3 | decision |
| A12 | Rename `src/common/` | Easy to confuse with `src/rag/common/`; `interfaces.py` holds Pydantic models, not interfaces (e.g. `src/agents/schemas.py`) | P3 | decision |
| A13 | `POST /qa` FastAPI route | `QARequest` / `QAResult` already fit as request / response models; `main.py` only has `/health` | P3 | open |
| A14 | Latency and cost | One embedding + one LLM call per question; glossary hits skip the embedding. Consider caching | P3 | open |
| A15 | Streaming responses | Nice-to-have for the UI | P3 | open |
| A16 | Prompt injection via retrieved text | Covered by the "sources are not instructions" line today; re-check when URLs are ingested | P2 | open |
| A17 | Distress handling: confirm flag-not-block | Chosen from the agent doc ("stay in educational framing"). Revisit if reviewers prefer a hard stop | P3 | decision |
| A18 | Model pads after saying "no information" | Graded #10 (Nifty close): the model correctly said the sources have nothing, then appended unrelated mutual-fund definitions with citations. Add a prompt rule: if the sources do not answer, say so in one or two sentences and stop | P2 | open |
| A19 | Glossary answers beat retrieval for plain definitions | Graded #2 ("What is an expense ratio?") produced a one-line answer citing the factsheet article `[3]`, while the glossary has a precise definition. Evidence for wiring A6. Verified live (graded #2). | P1 | done |
| A20 | `citations` is `[]` although answers contain `[n]` markers | Seen on every graded question. Same work as A8; listed so the symptom is findable. Verified live. | P1 | done |
| A21 | Interactive CLI exists (`src/agents/cli.py`) but is minimal | Add `--category`, and a `--debug` flag that prints retrieval status, best score and the documents hit (what Rung 11 prints). Today you cannot see *why* an answer was produced | P3 | open |
| A22 | Duplicate adjacent markers after renumbering | Graded #5 produced `...higher rates [1][1].` because two chunks of one article, cited as `[1][2]`, both map to `[1]`. Collapse repeats after `renumber_markers`: `re.sub(r"(\[\d+\])(?:\s*\1)+", r"\1", text)` | P2 | **done 2026-11-03**: `renumber_markers` collapses adjacent repeats; pinned in `tests/rag/citations_test.py` |
| A23 | Stray space before punctuation after a marker is removed | An invented marker `[9]` is deleted, leaving `"great ."`. Tidy with `re.sub(r"\s+([.,;:!?])", r"\1", text)` in `renumber_markers` | P3 | **done 2026-11-03**: invented marker removed together with its preceding space; pinned in `citations_test.py` |
| A24 | Uncited fallback lists every source that was *given* to the model | It means "consulted", a weaker claim than "cited". Label it differently in the UI, or cap it | P3 | open |
| A25 | `_clarify` message lacks the trailing question mark | `"Do you mean Bond (fixed income) or Bond (legal)"` | P3 | **done 2026-11-03**: `_clarify` ends with `?`; asserted in `test_ambiguous_term_asks_to_clarify` |
| A26 | Add two agent tests | (1) an exception inside **retrieval** also returns `route="error"`; (2) distress + glossary hit still ends with the supportive suffix | P2 | **done 2026-11-03**: `test_retrieval_exception_returns_error_result_without_calling_llm` and `test_distress_suffix_survives_the_glossary_route` |
| A27 | Padding after "no information" is still present (graded #10) | After the no-source stop was wired, #10 still reaches the LLM (retrieval best score 0.581 > 0.55); the model says it has no data and then adds unrelated definitions with a citation. See A18 and R14 | P1 | open |

## 3. Retrieval (`src/rag/retrieval/`)

| # | Item | Why | Pri | Status |
|---|---|---|---|---|
| R1 | Tune `min_score` from data | `0.55` is a guess. Collect best-scores for ~20 questions (in-KB, borderline, off-topic) at `min_score: 0` and choose where they separate. The agent's honesty depends on it | P1 | **done 2026-11-03**: measured with `scripts/eval_retrieval.py` over `tests/eval/questions.yaml` (30 in_kb / 10 borderline / 10 off_topic): in_kb min 0.739, off_topic max 0.620; `min_score` set to 0.66 |
| R2 | Build the eval set | 30-50 answerable questions with expected article, plus 10-15 unanswerable; metrics: recall@k, MRR, false-positive rate on unanswerables | P1 | open |
| R3 | Capture the pre-filter best score | `best_score` is computed after post-processing, so it is `None` when the threshold removes everything - the number you most need for tuning | P2 | open |
| R4 | Fix `ChromaStore._to_where` | Defined without `self`, never called; multi-key filters will be rejected by Chroma. Make it a function / staticmethod and use `where=_to_where(filters)` | P2 | verify |
| R5 | Fail loudly on an empty / mismatched collection | `get_or_create_collection` silently creates an empty collection if the model changes; check `store.info().count > 0` at startup. Implemented in `build_rag`; the standalone retrieval CLI still has its own copy of the check. | P1 | done |
| R6 | Validate `category_hint` | Unknown topic filters to zero results and looks like `no_source`. Check against known topics or fall back to unfiltered | P2 | open |
| R7 | Show drops in debug logs | Log which chunk each post-processor removed | P3 | open |
| R8 | Validate `max_per_doc >= 1` in `PerDocCap` | `0` silently returns nothing | P3 | open |
| R9 | Better citation excerpts | Pick the sentence most relevant to the question; drop a leading heading to avoid "Heading Heading text" duplication | P3 | open |
| R10 | Reranker, neighbour-chunk expansion, MMR | Biggest quality jump after the basics | P3 | open |
| R11 | Hybrid search (BM25 + dense) | Tickers and exact terms. `retrievers/hybrid.py` is an empty placeholder | P3 | open |
| R12 | Resolve relative paths in `rag.yaml` against the project root | `./.vectorstore/...` and `./docs/...` depend on the current working directory. `bootstrap.py` anchors config, store and glossary paths to the project root; the ingestion, retrieval and glossary CLIs still use cwd-relative paths. | P2 | done (bootstrap) |
| R13 | `VectorStore` / `Manifest` protocols in `src/rag/common/interfaces.py` are stale | `ensure_collection` appears twice with different signatures; methods take collection names the real store does not | P2 | open |
| R14 | Threshold margin is too thin (evidence) | Off-topic "what is the weather" best score **0.537**; finance-adjacent but unanswerable "Nifty 50 closing value yesterday..." best score **0.581**, which passed `min_score: 0.55`. Genuinely on-topic questions score 0.66-0.86. A single global threshold may not separate "adjacent but unanswerable"; build the eval set (R2) and consider a second signal | P1 | **done 2026-11-03**: same evidence; Rung 11 #10 now `no_source`; live regression `tests/eval/retrieval_eval_test.py` (40 cases, skipped without a key) |
| R15 | Re-run the graded question set after the SIPs article was ingested | Questions 9 and 10 were measured without it. Re-run Rung 11 and replace the baseline table. Re-run on 2026-11-02 with the SIPs article ingested; second baseline is recorded in the rungs doc (Rung 11). | P2 | done |

## 4. Ingestion (`src/rag/ingestion/`)

| # | Item | Why | Pri | Status |
|---|---|---|---|---|
| I1 | Strip the `## Purpose` boilerplate | Authoring text ("the agent should be able to...") is embedded and retrievable. Add a cleaner and re-ingest (the manifest re-embeds only changed articles) | P1 | open |
| I2 | Confirm the Gemini batch really returns one vector per text | `gemini-embedding-2` may aggregate a plain list into one embedding. The pipeline asserts `len(vectors) == len(batch)`; make that an explicit `raise` so it survives `python -O` | P1 | verify |
| I3 | Retry with backoff + rate limiting | Decorator around any `Embedder` (429 / 5xx). Config keys exist as comments in YAML | P2 | open |
| I4 | Cross-document batching | Today each document is embedded separately (underfilled batches). Needs per-document completion tracking before writing the manifest | P3 | open |
| I5 | Async Batch API for large re-indexes | Cheaper at 100k+ chunks; changes the pipeline shape (submit, poll, collect) | P3 | open |
| I6 | Blue/green re-index with aliases | Alias table in the manifest DB; build a new physical collection, then flip the alias | P3 | open |
| I7 | PDF and web loaders | `loaders/pdf.py`, `loaders/web.py` are empty. Web needs main-content extraction, robots.txt, caching | P2 | open |
| I8 | Chunkers: `character`, `paragraph`, `markdown_header`, `semantic` | Files exist but are empty (semantic needs an injected embedder). Per-source chunker override in YAML | P2 | open |
| I9 | Other stores: FAISS, pgvector | Empty files. pgvector is the best test that the `VectorStore` abstraction holds | P3 | open |
| I10 | Cleaners (`whitespace`, `boilerplate`) | Listed in YAML comments, not implemented | P2 | open |
| I11 | Queue-based ingestion beyond ~100k chunks | Threads are enough for now; keep stages stateless so this stays possible | P3 | open |
| I12 | Dry-run mode with cost estimate | `pipeline.dry_run` / `concurrency` are commented out in YAML | P3 | open |
| I13 | `sips-and-periodic-investing` is not in the vector store | 15 articles on disk, 14 ingested and 14 manifest rows. The article loads and chunks (8 chunks), so a re-run of ingestion should add it. Find out why it was skipped the first time (check `failed` in the stats line). Re-ingested: 143 chunks, 15 docs. | P1 | done |
| I14 | KB content gaps shown by the graded questions | The capital-gains article does not state the current long-term rate (answer: "sources do not provide the exact rate"); nothing on gold or live market data. Content work, not code | P2 | open |

## 5. Glossary (`src/rag/glossary/`)

| # | Item | Why | Pri | Status |
|---|---|---|---|---|
| L1 | Curate `docs/knowledge-base/glossary.yaml` | Every definition must carry `source_urls`; shown to users as fact | P1 | open |
| L2 | Integrity test | Every `related_articles` id must exist in `docs/knowledge-base/articles/` | P2 | open |
| L3 | Staleness check | Glossary can drift from articles; use `last_verified_at` and flag old entries | P2 | open |
| L4 | `verified_at` on glossary citations | `cite_glossary` does not pass it; needs a field on `GlossaryEntry` | P3 | open |
| L5 | Warn on an alias shared by two different terms | Today they silently merge into an "ambiguous" result | P3 | open |
| L6 | Fuzzy matching (`fuzzy_cutoff`) | Off by default; enable only after seeing missed typos in logs, and log every fuzzy hit | P3 | decision |
| L7 | Relaxed matching ("what is SIP in mutual funds") | The 5-word rule falls through to RAG. Acceptable; revisit if too many misses | P3 | decision |

## 6. Cross-cutting

| # | Item | Why | Pri | Status |
|---|---|---|---|---|
| X1 | One shared wiring function | `src/rag/bootstrap.py::build_rag()`; the ingestion, retrieval and glossary CLIs each re-implement it. `build_rag()` exists and the agent uses it; the ingestion, retrieval and glossary CLIs still hand-wire. | P1 | partial |
| X2 | Rename `src/config/ingestion.yaml` references | Config is now `rag.yaml`; check CLI defaults (`--config`) still point to an existing file | P1 | verify |
| X3 | Test layout and runner | No pytest config; use `.venv/bin/python -m pytest`. Consider `asyncio_mode = "auto"` in `pyproject.toml` | P2 | open |
| X4 | Fake LLM / fake retriever fixtures | The Definition of Done requires a mocked retriever; share them in `tests/conftest.py` | P1 | open |
| X5 | Observability | Log per request: route, best score, source ids, cited or not, latency. Never log question text | P2 | open |
| X6 | Tax Education agent shares the vector store | Differentiated only by the `topic` filter; do not build a second store | P3 | done (2026-11-13) |
| X7 | Scripts living under `tests/` | `gemini_test.py` (calls the real API at import), `portfolio_agent_test.py`, `financeqaagent_tests.py`, `tests/kite/*_test.py` execute code at import. (see K1 for the Kite ones: they also fail now.) A bare `pytest tests/` is unsafe. Move them to `scripts/` or rename `scratch_*.py`, and add `testpaths` / `python_files` under `[tool.pytest.ini_options]` in `pyproject.toml` | P2 | open |
| X8 | Delete `src/agents/finance_qa_agent copy.py` | Stale backup with a space in its name and the old broken imports | P3 | **done 2026-11-03**: file deleted |
| X9 | The RAG layer imports from the agent layer | `src/rag/common/models.py` imports `QASettings` from `src.common.models` to type the `Rag` dataclass. Dependencies should flow agent → RAG only. Move `Rag` into `bootstrap.py` (the one module allowed to know both) or type `settings` as `object` | P2 | decision |
| X10 | Delete the stub `tests/core/guardrails_test.py` | Same as G22; still present next to `guardrails_layers_test.py` | P3 | **done 2026-11-03**: stub deleted |

---

## 7. Agent ideas (brainstorm, not committed)

Rule of thumb used to rank them: **if a problem can be solved with deterministic code (a regex, a dictionary, a threshold), do that first.**
Add an LLM agent only where the input is open-ended, and always keep a deterministic fallback. Evidence for each idea comes from the
graded question run (Rung 11) and from the items above.

| # | Idea | Weakness it addresses (evidence) | Where it sits | LLM? | Pri | Status |
|---|---|---|---|---|---|---|
| N1 | **Eval / red-team agent** (dev-time) | Threshold never tuned (R1, R14); no regression measurement (R2). Generates answerable, paraphrased, adversarial and unanswerable questions per article, runs the pipeline, reports recall@k, groundedness and refusal rate | offline script, not in the request path | yes (generation + judge) | P1 | idea |
| N2 | **Router / intent + normalizer agent** (the LangGraph router, README step 8) | Multi-intent questions (#9: distress + advice + gold + SIP), off-topic questions reaching retrieval (#10), Hinglish and typos (G13-G16). Returns a typed decision: intent, confidence, normalized English question, sub-questions, needs-clarification | after the hard guardrails, before glossary / retrieval | yes (small model, structured output) | P1 | idea |
| N3 | **Grounding verifier** (output critic) | "Cited is not supported" (stage 5 gap), padding after "no information" (A18, #10), recommendation language leaking into answers. Checks each claim against the cited sources; strips, regenerates or adds a caveat | after generation, before citations | yes (can be a cheaper model, or sampled) | P2 | idea |
| N4 | **KB curator** (dev / ops) | Content gaps (I14, #8 had no tax rate), glossary drift (L3), boilerplate in articles (I1). Lints articles against the template, proposes glossary entries from "Core Concepts", reports questions the KB could not answer | offline, human reviews the output | yes | P2 | idea |
| N5 | **Freshness watcher** (scheduled) | `risk_level: time-sensitive` articles (tax rates) go stale. Re-fetches the official source URLs, diffs against stored claims, opens a review task. Never edits the KB itself | scheduled job | yes (diff summary) | P3 | idea |
| N6 | **Follow-up condenser** | Multi-turn questions ("what about its tax?") have no meaning alone (A11). Fold into N2 | inside N2 | yes | P3 | idea |
| N7 | **Portfolio-aware explainer** | Connects Q&A to the Portfolio agent: explains a concept using the user's own allocation, descriptive not prescriptive | later, LangGraph level | yes | P3 | idea |

---

### Decisions (2026-11-02)

| Item | Decision | Where it is designed |
|---|---|---|
| Router / supervisor (N2) | **Required.** Rules first, LLM classifier second, fallback to Q&A | [`agents/router_agent.md`](agents/router_agent.md) |
| Shared contracts | **Required.** `AgentResult`, `AgentContext`, `UserProfile`, guard layer, `MarketDataProvider`, `PortfolioSource` | [`agents/shared_contracts.md`](agents/shared_contracts.md) |
| MCP server | **Required.** Thin adapter, read-only tools, stdio, no trading tools | [`agents/mcp_server.md`](agents/mcp_server.md) |
| yfinance | **Required**, in both Market and Portfolio, behind `MarketDataProvider`; Kite stays as another source | market + portfolio docs, `shared_contracts.md` |
| Risk profile | **Not a separate agent.** It is the Goal Planning agent's intake step, saved to `UserProfile` after user confirmation | `agents/goal_planning_agent.md` |
| Eval agent (N1), grounding verifier (N3), KB curator (N4) | **Undecided.** Revisit after the router exists | this section |
| Tax as a profile of the Q&A pipeline | **Undecided** | `shared_contracts.md`, open questions |

New implementation items from these docs:

| # | Item | Pri | Status |
|---|---|---|---|
| C1 | Create `src/core/contracts.py` (`AgentResult`, `AgentContext`, `UserProfile`); one canonical `Citation` | P1 | open |
| C2 | `QAResult.to_result()` adapter; later switch `run()` to `AgentResult` | P1 | open |
| C3 | Move shared guards to graph nodes; add `output_guard` (advice-leak scan) | P1 | open |
| C4 | `MarketDataProvider`: yfinance + Kite + cache + fallback; symbol mapping verified live | P1 | open |
| C5 | `PortfolioSource`: kite, csv, sample, manual; `compute_portfolio_metrics` in pure Python | P1 | open |
| C6 | Replace the Portfolio system prompt ("helpful trading assistant") with analysis-only wording | P1 | open (bug) |
| C7 | LangGraph router: rules-only first, then classifier, memory, pending actions | P1 | open |
| C8 | MCP server with the allowlisted read-only tools and a tested Claude Desktop config | P2 | open |
| C9 | Declare `fastmcp` and `cachetools` in `pyproject.toml`; add `langgraph-checkpoint-sqlite` when memory is persisted (the React UI is a separate npm project) | P2 | open |
| C10 | Risk questionnaire with deterministic scoring inside Goal Planning | P2 | open |
| C11 | Refresh `agents/finance_qa_agent.md` (status "Planned" is stale; `category` is `topic` in code; planned paths differ) | P3 | open |
| C12 | Shared agent contract test over every agent | P2 | open |
| C13 | `src/config/app.yaml` and `src/core/config.py` (typed, `extra="forbid"`) | Created 2026-11-02. **Missing:** `tests/core/config_test.py` (real file loads; misspelled key, unknown provider and out-of-range threshold are rejected) | P2 | **done 2026-11-03**: `tests/core/config_test.py` (8 cases); mutation-checked by removing `extra="forbid"` |
| C14 | Tests for `citations.py` | `used_markers`, `renumber_markers`, `merge_by_source`, `make_excerpt`, `primary_url` have no unit tests of their own (only exercised through the agent). Write them together with the A22 and A23 fixes | P2 | **done 2026-11-03**: `tests/rag/citations_test.py` (14 cases) |
| C15 | Rung 11 first-call latency | The first graded question took 20.8 s in one run and about 2 s in another; probably a cold connection. Warm the agent at startup in the app, and see whether it repeats | P3 | verify Update 2026-11-03: the whole Rung 11 batch took 18–42 s per LLM answer, so this is not only a cold start; measure LLM time vs retrieval time separately. **Next actions:** (1) time `retrieve` and `ainvoke` separately for one question; (2) check the model and any thinking/reasoning setting in `config.yaml`; (3) cap output length and prompt size; (4) record the before/after numbers here. |

## 8. Market, Portfolio and Kite (added 2026-11-12)

| # | Item | Why | Pri | Status |
|---|---|---|---|---|
| K1 | Delete the old Kite code | `src/agents/portfolio_agent.py` (LangChain `MCPAdapter`, connects without a token) and the scripts `tests/kite/kite_tools_test.py`, `tests/kite/scratch_kite_test.py`, `tests/agents/portifolioagents/portfolio_agent_test.py` all fail now that the server requires OAuth. Nothing in `src/` imports them except the old file itself. Folds into X7 | P2 | open |
| K2 | Verify the mutual-fund row keys | The test account holds no funds (`data: []`), so `tradingsymbol`, `fund`, `quantity`, `average_price`, `last_price` in `KiteSource._fund` are assumed from Kite Connect. Check `scripts/kite_shape.py` output once an account has funds | P2 | verify |
| K3 | Persist Kite tokens between runs? | Tokens live in memory, so every run needs a login (Kite sessions expire daily anyway). Storing brokerage credentials on disk needs a deliberate decision | P3 | decision |
| K4 | Login link only works on the app's machine | OAuth approval returns to a `localhost` callback. Fine for the CLI and a local demo; a deployed server needs a different arrangement | P3 | decision |
| K5 | `connect <bare unknown word>` reaches Q&A | The router rule needs a portfolio-like word (`portfolio`, `sample`, `kite`, `zerodha`, `csv`, `manual`) to avoid catching "connect the dots". `connect robinhood portfolio` works | P3 | decision |
| K6 | Sample portfolio's average prices are made up | HDFCBANK shows about -48 % and GOLDBEES about +105 %. Edit `_SAMPLE` in `src/data/portfolio/sample.py` to values near today's prices. Cosmetic; no test depends on them | P3 | open |
| K7 | `csv` and `manual` portfolio sources | The spec's baseline is "portfolio analysis of user input"; `sample` and `kite` exist, these two do not | P1 | open |
| K8 | `get_profile`-style details not used | The app calls only `session/status`, `portfolio/holdings`, `mutual_funds/holdings`. Positions, margins and profile are deliberately off the allowlist; add a pair only with a test that names it | P3 | decision |
| K9 | Market agent: names, not only tickers | `reliance share price` (lowercase) finds no symbol and asks "Which stock or index?". Resolve names with the provider's `search` | P2 | open |
| K10 | Router imports `extract_instruments` | The router keeps its own ticker regex and `_NOT_TICKERS`; `src/data/market/symbols.py` has the same idea. One source of truth | P3 | open |
| K11 | Price cache | The spec asks for a 30-minute TTL in front of live market data; yfinance is called on every question today | P2 | open |
| K12 | Declare dependencies | `fastmcp` is now declared; a persistent checkpointer is not yet | P2 | partial |

---

## 9. Tax Education (added 2026-11-13)

| # | Item | Detail | Priority | Status |
|---|---|---|---|---|
| T1 | Add tax articles | Only 3 articles have `topic: costs-taxes` (one truly on tax). Add tax-loss harvesting, ELSS / Section 80C concepts, tax-advantaged accounts, STCG vs LTCG classification. Concepts only, no current numbers | P2 | open |

## 10. News, Memory v2 and goal follow-ups (added 2026-11-16)

| # | Item | Detail | Priority | Status |
|---|---|---|---|---|
| N1 | More news noise entries | tune `is_noise` from live data (for example "...Growth Stocks To Own") | P3 | open |
| N2 | Second news provider | Yahoo Finance RSS works keyless; Alpha Vantage gives sentiment. One class plus `@register_news_provider` | P3 | open |
| N3 | Relevance by alias | "Eternal" is Zomato's parent; a name-to-aliases table would stop dropping such stories | P3 | open |
| M1 | Persist memory | `ConversationMemory` is in-process. SQLite behind the same interface; needs a session id per browser tab | P2 | open |
| M2 | Other agents write slots | market could remember the last symbol, Q&A the last topic (same `learned` contract) | P3 | open |
| G1 | Risk questionnaire | deterministic scoring, then save as `risk_source="questionnaire"` | P3 | open |
| G2 | Forget a saved return rate | "forget the rate" without clearing everything | P3 | open |
| G3 | Inflation and step-up SIPs | not covered by the maths yet | P3 | open |

## 11. API (added 2026-11-16)

| # | Item | Detail | Priority | Status |
|---|---|---|---|---|
| S1 | Token streaming | `POST /chat/stream` (SSE). Needs each agent to expose a stream; until then the UI shows a spinner | P2 | open |
| S2 | Authentication and rate limiting | the API trusts any caller and any `thread_id` | P2 | open |
| S3 | Evict idle sessions | memory and locks grow with threads; add a size cap or TTL to `ConversationMemory` (also M1) | P2 | open |
| S4 | Extraction reliability metric | the goal extractor sometimes returns nothing; it now retries 3 times. Log how often a retry is needed | P3 | open |

## 12. Web app (added 2026-11-16)

| # | Item | Detail | Priority | Status |
|---|---|---|---|---|
| U1 | Indian digit grouping | `₹50,00,000` everywhere. The backend text (`_inr` in the goal and portfolio agents) and the web formatter (`src/web_app/src/format.ts`) must change together | P3 | open |
| U2 | Streaming replies in the UI | pairs with S1; show tokens as they arrive | P2 | open |
| U3 | Commit a browser end-to-end test | the Playwright session used to verify the UI is a one-off script; keep a small version in CI | P3 | open |
| U4 | Wide tables on phones | add a scroll hint, or stack the goal table's columns under 400 px | P3 | open |
| U5 | News details panel | the citation chips duplicate the numbered list in the text; a card per story with publisher and date would read better | P3 | open |

## 13. MCP server (added 2026-11-17)

| # | Item | Detail | Priority | Status |
|---|---|---|---|---|
| M3 | More than two indexes | the Market agent knows Nifty 50 and Sensex only ("Nifty Bank" is read as Nifty 50). Add an index table to `symbols.py`, then relax `INDEX_NAMES` in the MCP server | P3 | open |
| M4 | `get_price_history` | the provider now has `history()` (2026-11-17, used by `GET /market/history`); exposing it as an MCP tool is the remaining step | P3 | open |
| M5 | `search_knowledge_base` | raw passages; expose only with the input guard and a clear "source text, not advice" label | P3 | open |
| M6 | HTTP transport for MCP | needs a per-client conversation id (the stdio default of one conversation per process would mix clients) | P3 | open |
| M8 | Negative cache for unknown tickers | a mistyped ticker asks Yahoo every time (0.6 to 1.2 s); remember "not found" for about a minute. Persisting the cache across restarts is a separate, optional step | P3 | open |
| M7 | Try it in Claude Desktop | manual: a concept question, a quote, a goal, the portfolio; screenshot for the demo | P2 | open |

## Suggested order

1. **Make guardrails correct:** G1-G4, G6, then the test suite is green apart from the `xfail` gaps.
2. **Dummy agent baseline:** A1-A5 (retrieve → generate), then confirm the answer reads sensibly.
3. **Add layers one at a time:** glossary (A6, L1) → retrieval threshold (R1, R5, I1) → citations (A8).
4. **Measure:** R2 (eval set) feeds back into G7-G18 and R1.
5. **Harden:** A9, X5, then the API route (A13).
