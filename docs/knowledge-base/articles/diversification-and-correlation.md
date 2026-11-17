---
article_id: diversification-and-correlation
title: "Diversification and Correlation"
topic: growth-portfolio
summary: "Why spreading investments across assets that don't move in lockstep can reduce overall portfolio risk, and the limits of that effect."
source_urls:
  - https://www.investor.gov/introduction-investing/getting-started/asset-allocation
  - https://www.sec.gov/files/investor/pubs/assetallocation.htm
claim_sources: {}
jurisdiction: global
risk_level: normal
last_verified_at: "2026-10-22"
review_due_at: null
version: 1
related_articles:
  - asset-allocation
  - risk-vs-return
  - mutual-funds-and-etfs
---

# Diversification and Correlation

## Purpose

After reading this, the agent should be able to explain what diversification is, why *correlation* (not just "owning more things") is the mechanism behind it, and where diversification's benefits stop.

## Core Concepts

- **Diversification** means spreading money across multiple investments, sectors, or asset classes rather than concentrating it in one. The SEC's own Beginners' Guide defines it directly: "the practice of spreading money among different investments to reduce risk."
- **Correlation** measures how two investments' prices move relative to each other — from +1 (move perfectly together) to −1 (move perfectly opposite). *(Note: the SEC guide cited below describes this mechanism in plain language — "the returns of the three major asset categories have not moved up and down at the same time" — but doesn't use the technical term "correlation" or give coefficient numbers; the ±1/−1 framing here is standard portfolio theory added for precision, not a direct quote.)*
- Diversification reduces portfolio-level risk most effectively when combined assets have **low or negative correlation** — simply owning many stocks in the same sector can still leave a portfolio highly correlated (and therefore not well diversified). The SEC guide makes this concrete: a stock portfolio of only four or five holdings is **not** considered diversified — it suggests **at least a dozen carefully chosen stocks** across different companies/sectors as a starting point for within-asset-class diversification.
- Diversification reduces *unsystematic risk* (risk specific to one company/sector) but does **not** eliminate *systematic/market risk* (broad market-wide movements affect almost everything to some degree) — the SEC guide is explicit that diversification "won't necessarily" eliminate risk, only limit losses and reduce fluctuation.
- Over-diversification (too many overlapping holdings, or too many narrowly-focused funds) can dilute returns and add fees without meaningfully reducing risk further.

## Worked Example

Illustrative only — not real historical data:

| Scenario | Holding A | Holding B | Combined behavior |
|---|---|---|---|
| High correlation (≈ +0.9) | −10% | −9% | Both fall together — limited diversification benefit |
| Low/negative correlation (≈ −0.3) | −10% | +4% | B partially offsets A's decline — diversification benefit realized |

This is why "I own 20 different stocks" isn't automatically diversified — if those 20 stocks are all in the same sector and move together, correlation is high and the diversification benefit is weak.

## Misconceptions

- Owning more securities isn't the same as being diversified — correlation between those securities is what matters.
- Diversification reduces volatility/concentration risk; it does not guarantee positive returns or protect against broad market downturns.
- Correlation is not fixed — it can rise during market stress (assets that normally move independently can become more correlated in a crisis), which is a real limitation of relying on historical correlation figures.

## Source References

- [Beginners' Guide to Asset Allocation, Diversification, and Rebalancing — SEC](https://www.sec.gov/files/investor/pubs/assetallocation.htm) — **directly fetched and read in full**; source of all direct quotes above (the diversification definition, the "four or five holdings isn't diversified" / "at least a dozen stocks" guidance, and the "won't necessarily" risk-elimination framing).
- [Asset Allocation and Diversification — Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) — this is the same content mirrored on investor.gov, but that specific URL returns 403 Forbidden to automated fetches; the sec.gov mirror above was used instead and successfully fetched.

No dedicated SEBI page specifically on cross-asset correlation was found — the SEC guide covers the diversification concept at the level this article needs; the ±1/−1 correlation-coefficient framing is standard portfolio theory added for precision, not from this specific source (flagged inline above).

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-10-22 — directly fetched and read the full SEC source page (not a search-engine summary) |
| Reviewer | — (AI-assisted only) |
| Jurisdiction | Global concept |
| Next review due | Before production indexing |
