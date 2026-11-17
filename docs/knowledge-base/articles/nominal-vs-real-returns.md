---
article_id: nominal-vs-real-returns
title: "Nominal Returns vs. Real Returns"
topic: foundations
summary: "Why the return rate quoted on a product isn't the same as the wealth you actually gain, once inflation is accounted for."
source_urls:
  - https://www.investor.gov/introduction-investing/investing-basics/what-risk
  - https://www.investor.gov/introduction-investing/investing-basics/glossary/purchasing-power
claim_sources: {}
jurisdiction: global
risk_level: normal
last_verified_at: "2026-10-22"
review_due_at: null
version: 1
related_articles:
  - compound-interest
  - inflation-and-purchasing-power
  - cagr-vs-xirr
---

# Nominal Returns vs. Real Returns

## Purpose

After reading this, the agent should be able to explain the difference between a nominal (stated) return and a real (inflation-adjusted) return, and compute a real return from a nominal return and an inflation rate.

## Core Concepts

- **Nominal return** is the return as stated — e.g. "this fixed deposit pays 7% per year." It says nothing about inflation.
- **Real return** is the return after subtracting the effect of inflation — it approximates what the investor actually gained in purchasing power.
- Approximate formula: `real return ≈ nominal return − inflation rate` (a close approximation for small values; the exact formula is `(1 + nominal) / (1 + inflation) − 1`).
- A **positive nominal return can still be a negative real return** if inflation exceeds it — the account balance grows, but what it can buy shrinks.
- Comparing two investment products only by their nominal headline rate, without a common inflation assumption, is comparing incomplete numbers.

## Worked Example

Assume (illustrative only) a fixed deposit with a nominal rate of **7% per year**, and assumed inflation of **5% per year**:

- Approximate real return ≈ 7% − 5% = **2%**
- Exact real return = (1.07 / 1.05) − 1 ≈ **1.9%**

So while the statement shows 7% growth, the investor's actual gain in purchasing power is closer to 2% — not 7%.

*(Both the 7% and 5% figures above are illustrative assumptions for the calculation method, not current rates for any specific product or current inflation data.)*

## Misconceptions

- A high nominal rate is not automatically a "good" return — it must be weighed against inflation over the same period.
- Real return is an *approximation* of purchasing-power change; it doesn't account for taxes or fees, which further reduce what an investor actually keeps (see "Pre-Tax vs. Post-Tax Returns" and "Expense Ratios and the Impact of Fees").
- Inflation used in a real-return calculation should reflect the *relevant* time period and context — a single year's inflation figure may not represent a 10-year holding period well.

## Source References

- [What Is Risk? — Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/what-risk) — **not independently fetch-confirmed**: returns 403 Forbidden to automated fetches. A web search surfaced what appears to be a direct quote matching this article's "4% gain, 5% inflation = real loss" framing almost exactly, which is reassuring, but that quote has not been verified against the actual rendered page.
- [Purchasing Power — Investor.gov glossary](https://www.investor.gov/introduction-investing/investing-basics/glossary/purchasing-power) — same caveat, not independently fetched.

The real-return formula itself is standard financial mathematics and isn't jurisdiction-specific; any live example using a specific current inflation figure must be sourced from RBI's published data at the time, not assumed.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-10-22 — AI-assisted via web search only; neither source independently fetch-confirmed (investor.gov blocks automated access); no qualified human reviewer yet |
| Reviewer | — (AI-assisted only) |
| Jurisdiction | Global concept |
| Next review due | Before production indexing |
