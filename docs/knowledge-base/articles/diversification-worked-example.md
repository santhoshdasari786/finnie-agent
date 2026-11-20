---
article_id: diversification-worked-example
title: "Diversification: A Worked Portfolio Example"
topic: worked-examples
summary: "A numerical comparison of a concentrated and a spread-out portfolio, showing how one holding falling affects each, how to compute a simple concentration score, and what diversification does and does not protect against."
source_urls:
  - https://www.investor.gov/introduction-investing/getting-started/asset-allocation
claim_sources:
  definition: "Investor.gov: diversification is the practice of spreading money among different investments to reduce risk; spreading within an asset class, across stocks, bonds and sectors, also helps"
jurisdiction: global
risk_level: normal
last_verified_at: "2026-11-18"
review_due_at: null
version: 1
related_articles:
  - diversification-and-correlation
  - asset-allocation
  - portfolio-rebalancing
  - volatility-vs-permanent-loss
  - risk-tolerance-vs-risk-capacity
---

# Diversification: A Worked Portfolio Example

## Purpose

After reading this, the agent should be able to show with numbers why a portfolio concentrated in one holding is more exposed to that holding's fall, calculate a simple concentration score, and state clearly what diversification cannot do.

## Core Concepts

- Investor.gov describes diversification as spreading money among different investments to reduce risk, summed up as "don't put all your eggs in one basket". Spreading across asset classes can help because conditions that hurt one may help another, and spreading within each class (several stocks or bonds, different sectors) helps too.
- A holding's **weight** is its value divided by the portfolio's total value. The effect of one holding on the whole portfolio equals its weight times its change.
- **Concentration** means a large share of the portfolio sits in one or a few holdings, so a fall in one holding moves the whole portfolio.
- A simple measure of spread is `1 − Σ(weight²)`, the sum over holdings of each weight squared. It is 0 for a single holding and rises as the portfolio is spread more evenly; four equal holdings give 0.75. This is the score the Portfolio view of this assistant reports. It looks only at the weights and ignores how the holdings move together.
- The measure is a simplification: two holdings that always move together add little real diversification even if their weights look balanced.
- Diversification **reduces the damage from one holding failing; it does not remove market-wide risk**, and it does not guarantee a gain or protect against loss in a broad fall.
- More holdings is not automatically better: owning many similar things, or paying more costs to hold them, adds little.

## Worked Example

A hypothetical ₹10,00,000 portfolio in two versions. Nothing about the holdings is real.

| | Portfolio A (concentrated) | Portfolio B (spread) |
|---|---|---|
| Holding 1 | 80% (₹8,00,000) | 25% (₹2,50,000) |
| Holding 2 | 10% | 25% |
| Holding 3 | 5% | 25% |
| Holding 4 | 5% | 25% |
| Concentration score 1 − Σ(w²) | 0.345 | 0.750 |

Now suppose Holding 1 alone falls by 50% and the others do not move.

- Portfolio A loses 0.80 × 50% = 40% of its value, ₹4,00,000.
- Portfolio B loses 0.25 × 50% = 12.5%, ₹1,25,000.

If instead all four holdings fall by 50% together, for example in a broad market fall, both portfolios lose 50%: spreading across holdings that move together did not help. A mix of holdings that behave differently, such as different asset classes, is what the spread is meant to provide.

## Misconceptions

- "Diversified means safe." It reduces single-holding risk, but a broad market fall still hurts.
- "More holdings always means more diversification." What matters is how differently the holdings behave, and their weights.
- "The concentration score predicts returns." It describes how spread out the weights are, nothing more.
- "Diversifying costs me the chance to gain." It trades some upside from one holding for less exposure to its failure.

## Source References

- [Asset Allocation and Diversification, SEC Investor.gov](https://www.investor.gov/introduction-investing/getting-started/asset-allocation): the definition of diversification and spreading within asset classes. **Directly fetched and read on 2026-11-18.** The concentration score is the formula used in this project's own portfolio code; the numbers in the example were computed in code.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-18: definition read directly; all example numbers computed in code |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | Global concept |
| Next review due | Before production indexing |
