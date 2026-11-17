# Performance benchmarks

**Measured 2026-11-18 on a MacBook (Apple silicon, macOS), Python 3.12, from India, against the real services** (Gemini for the model, Yahoo Finance for prices, Chroma on local disk). Re-run any time with:

```bash
.venv/bin/python -m scripts.bench_latency --runs 10
```

Each cell is **median / 95th percentile**. "n" is how many times it was repeated; the model and whole-question rows use only 3 to 5 runs to stay inside the free tier, so treat their tails as indicative, not precise. A row marked **PENDING** could not be measured on the day, and the reason is stated: nothing below is estimated.

## Where the time goes, stage by stage

| Stage | median / p95 | Notes |
|---|---|---|
| Input guard (empty, length, self-harm, flags) | 4 µs / 5 µs | pure Python, no model |
| Router rules (keyword routing) | 12 µs / 13 µs | pure Python |
| Glossary lookup (93 terms) | 2 µs / 2 µs | a dictionary |
| Chroma vector search, top 20 of 492 chunks | 1.2 ms / 1.5 ms | local, in process |
| One answer from ~4,000 characters of sources | 1.2 s / 4.3 s | Gemini, n=5 |
| A tiny model reply (classifier-sized) | 0.9 s / 1.2 s | Gemini, n=5 |
| Market quote, **cold** | 226 ms / 447 ms | Yahoo Finance, n=5 |
| Market quote, **cached** | 73 µs / 105 µs | the cache from Step 3 |
| Price history (1 year), cold | 117 ms (1 run) | |
| Price history, cached | 0.5 ms / 0.6 ms | |
| **Query embedding (Gemini), cold** | **PENDING** | the free tier's daily embedding quota was used up the day this was measured |
| **Whole retrieval (embed + search + filters)** | **PENDING** | same reason |

## Whole questions through the LangGraph

| Question type | median / p95 | What it does |
|---|---|---|
| A blocked message ("I want to die") | 2.4 ms / 4.7 ms | the guard answers; no model is called |
| A glossary question ("What is a margin call?") | 1.1 s / 2.2 s | one model call restates the definition |
| A price question ("TCS and Nifty price") | 1.2 s / 1.2 s | rules route it, the cached provider answers, one model call narrates |
| A goal question | **3.5 s** / 8.9 s (8 runs) | an extraction call, the calculation in code, a narration call |
| A knowledge-base question | **PENDING** | needs query embedding, see above |

The goal question was first measured with 3 runs, which gave a misleading 26.7 s worst case. Eight instrumented runs showed 2 model calls per question (3 when the extractor retries), each 1 to 2 s, with one 7.2 s call that looked like a provider spike.

## What this means

1. **Latency is the number of model calls times about 1 to 2 seconds.** Everything else (guard, router, glossary, vector search, calculations, cached prices) together costs under 5 ms. A question's speed is decided by how many times it must call the model: 0 for a blocked message, 1 for a glossary or price question, 2 for a goal, and 1 plus an embedding for a knowledge-base question.
2. **The model's tail is the user's tail.** A single call has a p95 of about 4 s, and occasional calls take 7 s or more. Nothing in the application can shorten that; showing partial text sooner (streaming, backlog S1) is the fix users would notice.
3. **The caches work.** A cached quote is about 3,000 times faster than a cold one, and a cached history about 230 times.
4. **The cold-start cost the old note warned about (backlog C15: "first graded question took 20.8 s") did not reproduce** in this run. Every stage above was warm after the first call, and the first end-to-end question was ordinary.

## Free-tier limits that shape behaviour

The Gemini free tier allows **100 embedding requests a minute and 1,000 a day**. Re-indexing the knowledge base uses about 500 calls, and the retrieval evaluation about 250 more; together they used the whole day's quota once. The embedder now retries a per-minute limit with backoff, caches query embeddings, and, when the daily quota is gone, tells the user plainly ("my knowledge base is busy") instead of failing. See `docs/qa-agent-backlog.md` section 14.

## To finish the pending rows

When the embedding quota has reset, run `.venv/bin/python -m scripts.bench_latency --runs 10` and paste the two embedding rows and the knowledge-base question row here.
