# News Synthesizer Agent

**Status:** Implemented (2026-11-16) · **Files:** `src/agents/news_synthesizer_agent.py`, `src/data/news/` · **Tests:** `tests/agents/newsagents/`, `tests/data/news_test.py` (about 175)

## Purpose and scope

Turns recent headlines about a company, sector or the general market into one short, **cited** roundup instead of a link dump. Out of scope, and enforced in code: anything that reads as a trading signal.

## How it works

```
"latest news on Infosys this week"
  → topic_from  → "Infosys"        lookback_from → 7 days        (both pure Python)
  → NewsProvider.search(topic, days)       (default: Google News RSS, India edition, no key)
  → drop noise → keep the window → keep stories that mention the topic
  → cluster near-duplicates (same story, different outlet) → newest 5
  → the LLM writes 3-5 sentences from the numbered headlines, citing [n]
  → vet the story → numbered list + story + one Citation per story
```

## Decisions

| Decision | Why |
|---|---|
| **Google News RSS is the default provider** | no key, dated, has a publisher on every item and a `when:7d` window. Checked live. yfinance's news endpoint was unreachable when tested, and the shape of its reply was never confirmed |
| **Providers are swappable** (`register_news_provider`) | same pattern as market data and portfolio sources: another provider is one class |
| **Clustering is pure Python** | token-set Jaccard similarity on normalised titles (publisher suffix and punctuation removed), threshold 0.6 |
| **The story is vetted in code**, not trusted | it must cite at least one real `[n]`, invented markers are removed, it may not give a trading signal (`you should buy`, `price target`, `we recommend`...), and every number in it must appear in the headlines. A story that fails is dropped; the headline list stays |
| **Noise is filtered before clustering** | aggregator pages (`Stock Price, News, Quote & History`), tips and predictions (`price prediction`, `target price`, `stocks to buy`), and social posts (Instagram, YouTube, Reddit...) |
| **Relevance filter** | a story must contain at least one word of the topic. The general market is not filtered |
| **A question is not a topic** | "Should I buy Zomato after this news?" falls back to the saved topic, with the advice-safe instruction |
| **Generic market phrases mean India** | "news on the stock market" searches "Indian stock market" |
| **Memory v2 slots** | `topic` and `days` are saved, so "and last month?" works. A carried topic is labelled "(from earlier)" |

## Edge cases

| Case | Behaviour |
|---|---|
| No news in the window, only noise, or nothing mentions the topic | `no_source`, no LLM call, never a stretched old article |
| Provider fails | friendly retryable error, the cause is logged only |
| The model fails or its story is rejected | the numbered headline list is still returned |
| Same story from several outlets | one entry, "(also: Mint, Hindu)" |
| Very long headline | shortened to 160 characters in the list; the citation keeps the full title |

## Known limits

- It works from **headlines only** (Google News gives no article text), so the story can say what was reported, not why.
- Links are Google News redirect URLs; they open the original article.
- No sentiment score: the source does not provide one. A provider that does can fill it in later.
- Relevance is by name. A story about "Eternal" will not match a search for "Zomato" unless the title also says Zomato.
- Some stock-tip pages still get through (for example "...Growth Stocks To Own"); the noise list is tuned from live data and will need more entries.

## Definition of Done

- [x] A news source behind a provider interface, with no API key
- [x] Dedup and clustering before the model sees anything
- [x] Source links, publisher and date on every story
- [x] No trading signals, no invented numbers or citations (checked in code)
- [x] Honest "no news" instead of stretching old articles
- [x] Follow-ups through Memory v2 (`and for the last 3 days?`)
- [ ] Sentiment (needs a provider that returns it)
- [ ] A pointer back to the Q&A explanation of a concept mentioned in a story
