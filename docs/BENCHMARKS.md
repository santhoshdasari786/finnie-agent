# Performance benchmarks

**Measured 2026-11-18 (23:20) on a MacBook (Apple silicon, macOS), Python 3.12, from India, against the real services** (Gemini for the model and embeddings, Yahoo Finance for prices, Chroma on local disk). The Gemini project was on the **paid tier** for this run (an earlier run the same day was on the free tier, see the last section). Re-run any time with:

```bash
.venv/bin/python -m scripts.bench_latency --runs 10
```

Each cell is **median / 95th percentile**. "n" is how many times it was repeated; the model and whole-question rows use only 3 to 5 runs, so treat their tails as indicative, not precise. Nothing below is estimated.

## Where the time goes, stage by stage

| Stage | median / p95 | Notes |
|---|---|---|
| Input guard (empty, length, self-harm, flags) | 4 µs / 5 µs | pure Python, no model |
| Router rules (keyword routing) | 12 µs / 14 µs | pure Python |
| Glossary lookup (93 terms) | 1 µs / 2 µs | a dictionary |
| Chroma vector search, top 20 of 934 chunks | 1.2 ms / 1.5 ms | local, in process |
| One answer from ~4,000 characters of sources | 1.0 s / 1.4 s | Gemini, n=5 |
| A tiny model reply (classifier-sized) | 0.9 s / 1.2 s | Gemini, n=5 |
| Market quote, **cold** | 260 ms / 468 ms | Yahoo Finance, n=5 |
| Market quote, **cached** | 92 µs / 165 µs | the cache from Step 3 |
| Price history (1 year), cold | 33 ms (1 run) | |
| Price history, cached | 0.6 ms / 0.9 ms | |
| Query embedding (Gemini), cold | 535 ms / 573 ms | n=10, one text per call |
| Query embedding, repeated question (cache hit) | 2 µs / 3 µs | in-process cache |
| Whole retrieval (embed + search + filters), cold | 498 ms / 535 ms | n=5; the embedding call is almost all of it |

## Whole questions through the LangGraph

| Question type | median / p95 | What it does |
|---|---|---|
| A blocked message ("I want to die") | 2.2 ms / 2.4 ms | the guard answers; no model is called |
| A glossary question ("What is a margin call?") | 0.75 s / 0.87 s | one model call restates the definition |
| A price question ("TCS and Nifty price") | 1.0 s / 1.5 s | rules route it, the cached provider answers, one model call narrates |
| A goal question | **2.0 s** / 2.2 s (3 runs; an earlier 8-run measurement gave 3.5 s / 8.9 s) | an extraction call, the calculation in code, a narration call |
| A knowledge-base question ("How much of my bank deposit is insured in India?") | 1.8 s / 2.7 s (3 runs) | one embedding call, vector search, one model call to answer with citations |

The goal question has varied between runs: an earlier 3-run measurement gave a 26.7 s worst case and an 8-run one gave 3.5 s with one 7.2 s call that looked like a provider spike; this run, on the paid tier, gave 2.0 s. Each question makes 2 model calls (3 when the extractor retries). The free-tier and paid-tier runs are not directly comparable, and 3 runs is too few to claim the difference is the tier.

## What this means

1. **Latency is the number of model calls times about 1 to 2 seconds.** Everything else (guard, router, glossary, vector search, calculations, cached prices) together costs under 5 ms. A question's speed is decided by how many times it must call the model: 0 for a blocked message, 1 for a glossary or price question, 2 for a goal, and 1 plus an embedding (about 0.5 s) for a knowledge-base question.
2. **The model's tail is the user's tail.** On the free tier a single call had a p95 of about 4 s and occasional calls took 7 s or more; on this paid-tier run the p95 was about 1.4 s. Nothing in the application can shorten that; showing partial text sooner (streaming, backlog S1) is the fix users would notice.
3. **The caches work.** A cached quote is about 3,000 times faster than a cold one, and a cached history about 230 times.
4. **The cold-start cost the old note warned about (backlog C15: "first graded question took 20.8 s") did not reproduce** in this run. Every stage above was warm after the first call, and the first end-to-end question was ordinary.

## Embedding limits that shape behaviour

The Gemini free tier allows **100 embedding requests a minute and 1,000 a day**. Re-indexing the knowledge base for 100 articles (934 chunks) plus the retrieval evaluation (about 210 calls a run) used a whole day's quota, and the benchmark's embedding rows were skipped on the first run. The embedder now paces batches to a per-minute budget (`requests_per_minute` in `src/config/rag.yaml`, default 90), retries a per-minute limit for about a minute, caches query embeddings, and, when the daily quota is gone, tells the user plainly ("my knowledge base is busy") instead of failing. After the project moved to the paid tier the embedding rows above were measured. Check Google's current limits before raising `requests_per_minute`. See `docs/qa-agent-backlog.md` section 14.
