---
article_id: cagr-vs-xirr
title: "CAGR vs. XIRR vs. Absolute Returns"
topic: growth-portfolio
summary: "Three different ways to measure investment return, when each one applies, and why picking the wrong one gives a misleading number."
source_urls:
  - https://zerodha.com/varsity/chapter/measuring-mutual-fund-returns/
claim_sources: {}
jurisdiction: global
risk_level: normal
last_verified_at: "2026-10-22"
review_due_at: null
version: 1
related_articles:
  - nominal-vs-real-returns
  - sips-and-periodic-investing
  - comparing-investment-products-fairly
---

# CAGR vs. XIRR vs. Absolute Returns

## Purpose

After reading this, the agent should be able to explain the difference between absolute return, CAGR, and XIRR, identify which one applies to a given situation (single lump sum vs. irregular cash flows), and walk through each formula with a worked example.

## Core Concepts

- **Absolute return**: simple total percentage gain/loss over the whole holding period, ignoring time. `(ending value − starting value) / starting value`. Doesn't account for *how long* it took.
- **CAGR (Compound Annual Growth Rate)**: the constant annual growth rate that would take a starting value to an ending value over a given number of years, assuming one lump-sum investment with no interim cash flows. `CAGR = (ending value / starting value)^(1/years) − 1`.
- **XIRR (Extended Internal Rate of Return)**: like CAGR, but built for *irregular cash flows at irregular dates* — multiple investments and/or withdrawals at different times (e.g. a SIP, or ad-hoc top-ups). It solves for the single annualized rate that makes the cash flow stream's net present value zero. Virtually always calculated with software/a tool, not by hand.
- **Decision rule** (confirmed against a worked industry reference, Zerodha Varsity): lump-sum held **under** a year → absolute return; SIP held under a year → absolute return; lump-sum held **over** a year → CAGR; SIP/staggered investments held over a year → XIRR. For a lump-sum held over a year, CAGR and XIRR give the *same* result — XIRR is only needed when cash flows happen on different dates.

## Worked Example

Examples below (with real formulas) are adapted from Zerodha Varsity's "Measuring Mutual Fund Returns" chapter:

**CAGR** (lump sum, >1 year): ₹25,000 invested, grows to ₹40,000 after 3 years:
`CAGR = (40,000 / 25,000)^(1/3) − 1 ≈ 16.96%`

**Absolute return** (same ₹25,000 → ₹40,000, but *if held under a year*): `(40,000 − 25,000) / 25,000 = 60%` — this is the total gain, not an annual rate. Zerodha Varsity makes the point directly: the right question is "what is the *growth rate*?", not just "what is the return?", since a 60% total gain alone doesn't show how it was spread over time.

**Why annualizing a short period can be misleading**: for a 5-month SIP (₹25,000 invested, ₹30,000 value), absolute return is a clean 20%. Technically computing XIRR on the same numbers gives roughly 106% — a number that's annualized far beyond what the short actual holding period justifies. This is exactly why the decision rule above says "use absolute return" for sub-1-year holdings, not XIRR or CAGR.

**XIRR** (SIP, >1 year): ₹5,000 invested on the 10th of each month from Dec 2018 to June 2020 (19 months, ₹95,000 total), worth ₹1,10,000 on 10 July 2020 → XIRR ≈ 18.79% (computed via Excel/Sheets' `XIRR()` function — there's no simple closed-form formula like CAGR's).

*(Figures above are from a third-party worked example for illustrating the calculation method, not real historical fund performance.)*

## Misconceptions

- Quoting a multi-year "total return" as if it were an annual rate (confusing absolute return with CAGR) is one of the most common ways investment performance gets misrepresented, even unintentionally.
- CAGR assumes a single lump-sum, uninterrupted holding period — applying it to a SIP or a portfolio with multiple contributions/withdrawals gives a misleading number. That's what XIRR is for.
- Neither CAGR nor XIRR tells you anything about *volatility* along the way — two investments can have the same CAGR with very different ride-quality (smooth vs. a rough path) in between.

## Source References

- [Measuring Mutual Fund Returns — Zerodha Varsity](https://zerodha.com/varsity/chapter/measuring-mutual-fund-returns/) — **directly fetched and read in full** (not just a search snippet); all formulas and worked examples above are taken from its actual text. This is a widely-used Indian financial education resource, but **not** a primary regulator — no official AMFI or SEBI page explaining CAGR/XIRR specifically was found despite searching for one.

**Flag for reviewer:** given how central CAGR/XIRR are to AMFI-regulated fund reporting, it's still worth a follow-up search specifically on amfiindia.com for a primary-source equivalent — the content here is accurate and directly verified, but from an industry site rather than a regulator.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-10-22 — directly fetched and read the full source page (not a search-engine summary); content confirmed accurate; still a reputable secondary (industry) reference, not a primary regulator |
| Reviewer | — (AI-assisted only) |
| Jurisdiction | Global concept (terminology is widely used in Indian mutual fund reporting specifically) |
| Next review due | Before production indexing — prioritize finding a primary AMFI/SEBI source as a secondary citation |
