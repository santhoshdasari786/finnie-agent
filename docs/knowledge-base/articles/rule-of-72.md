---
article_id: rule-of-72
title: "The Rule of 72: Estimating How Long Money Takes to Double"
topic: worked-examples
summary: "How to estimate the time for an investment to double by dividing 72 by the yearly return, a worked example from SEBI's booklet, and how accurate the shortcut is at different rates."
source_urls:
  - https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf
claim_sources:
  rule: "SEBI Financial Education Booklet, chapter 2: divide the rule number 72 by the annual interest rate to find the approximate time to double the money; its example is 6 percent giving 12 years"
jurisdiction: global
risk_level: normal
last_verified_at: "2026-11-18"
review_due_at: null
version: 1
related_articles:
  - compound-interest
  - nominal-vs-real-returns
  - inflation-and-purchasing-power-worked-example
  - cagr-vs-xirr
---

# The Rule of 72: Estimating How Long Money Takes to Double

## Purpose

After reading this, the agent should be able to apply the rule of 72 to estimate a doubling time, state that it is an approximation, and show where it is accurate and where it drifts, using an assumed rate and not a forecast.

## Core Concepts

- SEBI's booklet states the rule: divide **72 by the annual interest rate** to find the approximate time required to double money. Its example: ₹200 at 6% a year, 72 ÷ 6 = 12 years to reach ₹400.
- The rule applies to a **compounded** return, where each year's return is earned on the earlier total, as the booklet explains in its compound-interest section.
- It is a **mental shortcut**. The exact doubling time solves (1 + rate)^years = 2, which gives years = ln 2 ÷ ln(1 + rate).
- The shortcut is close for moderate rates (roughly the middle single digits to low teens) and drifts for very low or very high rates.
- The same idea works **in reverse**: the rate needed to double in a number of years is about 72 divided by the years.
- The rule also shows how **inflation** halves purchasing power: at an assumed 6% inflation, prices double in about 12 years, so money's purchasing power halves in about that time.
- The rule uses the rate **per year, as a percentage number** (6, not 0.06).
- It works for any compounding growth, including a fee-reduced return: use the net rate after costs.
- It says nothing about whether any investment will actually earn the assumed rate; the rate is an input, not a prediction.

## Worked Example

Using the rule on assumed rates, with the exact value for comparison (computed in code):

| Yearly rate | 72 ÷ rate | Exact doubling time |
|---|---|---|
| 2% | 36 years | 35.0 years |
| 6% | 12 years | 11.9 years |
| 8% | 9 years | 9.0 years |
| 12% | 6 years | 6.1 years |
| 24% | 3 years | 3.2 years |

Check of the booklet's example: ₹200 at 6% for 12 years grows to 200 × 1.06^12 ≈ ₹402.44, very close to the ₹400 the rule predicts.

Using it the other way: to double money in 9 years, a compounded return of about 72 ÷ 9 = 8% a year would be needed.

## Misconceptions

- "The rule gives the exact doubling time." It is an approximation that is closest in the middle of the range.
- "It works for simple interest." It assumes compounding; with simple interest, doubling takes 100 ÷ rate years.
- "A rate that doubles money quickly is a good investment." A high assumed rate may carry high risk or be unrealistic.
- "The rule predicts my investment's growth." It converts an assumed rate into a time; the rate itself is not known in advance.

## Source References

- [Financial Education Booklet, SEBI (PDF)](https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf): the rule and the ₹200 example. **Directly fetched and read on 2026-11-17** (passage re-read on 2026-11-18). The accuracy table and the simple-interest note are computed or standard arithmetic, not from the booklet.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-18: rule and example read from the booklet; table computed in code |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | Global concept |
| Next review due | Before production indexing |
