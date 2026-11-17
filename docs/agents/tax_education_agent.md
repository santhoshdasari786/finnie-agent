# Tax Education Agent

**Status:** Implemented (2026-11-13) · **Files:** `src/agents/tax_education_agent.py`, `src/prompts/tax_prompts.py` · **Tests:** `tests/agents/taxagents/` (31)

## Purpose & scope

Explains tax concepts and how rules are structured (holding-period classification, why tax-loss harvesting exists). **Education only, never specific tax advice.** This is the highest regulatory-risk agent, so it has the strictest scoping.

## Design constraint: concepts, not numbers

Rates, slabs, limits and deadlines change with every Budget (the knowledge base itself notes a rate change in July 2024). The agent never states them as current fact and sends the user to the Income Tax Department or a tax professional. Three layers enforce this, because a prompt alone is a request, not a guarantee:

| Layer | What it does |
|---|---|
| Prompt | `TAX_SYSTEM_PROMPT` forbids stating rates, slabs, limits, thresholds and deadlines |
| Question check | `ASKS_FOR_NUMBER` matches rate / slab / limit / deadline / `%` and adds `NUMBERS_NOTE` to the user message |
| Answer check | `HAS_FIGURE` matches `12.5%`, `₹1.25`, `Rs. 1,50,000`, `$10,000`, `2 lakh`; if found, `FIGURES_CAUTION` is appended once. Citation markers such as `[1]` do not match |

## Architecture

The agent is a thin subclass of `FinanceQAAgent`. It reuses the guards, glossary, retrieval, citations and error handling, and overrides five class members:

| Member | Q&A value | Tax value |
|---|---|---|
| `name` | `finance_qa` | `tax_education` |
| `_system_prompt` | `SYSTEM_PROMPT` | `TAX_SYSTEM_PROMPT` |
| `_forced_category` | none (caller's hint) | `costs-taxes`, which a caller's hint cannot widen |
| `_disclaimer` | `settings.disclaimer` | `TAX_DISCLAIMER` ("not tax advice … tax professional") |
| `_extra_note` / `_check_answer` | do nothing | numbers note / figures caution |

One vector store serves both agents (backlog X6). `bootstrap.build_agents` calls `build_rag()` once and passes the same retriever, glossary and settings to both.

## Edge cases

| Case | Behaviour |
|---|---|
| Asks for a rate, limit or deadline | concept explained, no number, pointed to the official source |
| Model states a figure anyway | caution appended once |
| No tax article covers it | `no_source`, no LLM call, tax disclaimer |
| Guard block (self-harm, empty) | redirect, retriever and LLM never called |
| Caller hint for another topic | ignored, search stays on `costs-taxes` |

## Known limits

- **Thin content.** Only three articles carry `topic: costs-taxes`, one of them truly about tax. Tax-loss harvesting, ELSS and Section 80C currently answer "no reliable source". The fix is articles, not code (backlog T1).
- India only. The jurisdiction in `UserProfile` is not consulted yet.
- The figure check is regex based: it will miss a number written out in words ("twelve and a half percent").

## Definition of Done

- [x] Reuses the Q&A vector store with the `costs-taxes` filter
- [x] System prompt enforces "concepts, not numbers", backed by a question check and an answer check
- [x] Every response carries the tax-specific disclaimer
- [x] Routed by the existing `tax` rule; live in the graph
- [ ] More tax articles (T1)
