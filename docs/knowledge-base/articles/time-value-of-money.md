---
article_id: time-value-of-money
title: "The Time Value of Money: Why ₹1,000 Today Is Not ₹1,000 Later"
topic: foundations
summary: "What the time value of money means, how future value and present value are calculated at an assumed rate, why it underlies compounding and inflation arguments, and worked numbers including a monthly saving example."
source_urls:
  - https://investor.sebi.gov.in/pdf/reference-material/beginners.pdf
claim_sources:
  tvm: "SEBI Beginner's Guide to the Capital Markets: money has time value; a thousand rupees today is worth more than a thousand rupees five years from now, even without inflation; ₹1,000 invested today at 5 percent a year becomes ₹1,050 after a year"
jurisdiction: global
risk_level: normal
last_verified_at: "2026-11-18"
review_due_at: null
version: 1
related_articles:
  - compound-interest
  - rule-of-72
  - inflation-and-purchasing-power-worked-example
  - monthly-investing-worked-example
  - nominal-vs-real-returns
---

# The Time Value of Money: Why ₹1,000 Today Is Not ₹1,000 Later

## Purpose

After reading this, the agent should be able to explain the time value of money, convert between present and future amounts at an assumed rate with the formulas, and show how starting earlier changes the result, while stating that the rate is an assumption.

## Core Concepts

- SEBI's Beginner's Guide states that **money has time value**: a thousand-rupee note today is worth more than the same note five years from now, even if there were no inflation. The reason it gives is that people prefer consumption today to uncertain consumption in the future, and money today can earn a return.
- Its example: invest ₹1,000 today at 5% a year and you receive ₹1,050 after a year, so ₹1,000 today is equivalent to ₹1,050 one year from now.
- **Future value (FV)** of a single amount = amount × (1 + rate)^years. **Present value (PV)** is the reverse: amount ÷ (1 + rate)^years. The rate used is called the discount rate.
- A **series of equal monthly amounts** has a future value of payment × ((1 + r)^n − 1) ÷ r, where r is the monthly rate and n the number of months (assuming payments at the end of each month).
- The same idea explains **compounding** (returns earned on earlier returns) and why starting early matters. **Inflation** is a separate effect: it lowers what money buys, while time value is about what money can earn.
- A higher rate or a longer time makes the gap between today's and future amounts larger. This is also why a **fixed amount promised in the future** is worth less today, and why debt costs more the longer it runs.
- The discount or growth rate is an **assumption**; real returns vary and can be negative.
- The SEBI Beginner's Guide also has an illustration of ₹5,000 a month from age 25 growing past a crore. The figures given for the later periods could not be reproduced from the rate stated, so this article uses its own computed numbers instead.

## Worked Example

Assume 5% a year for the single-amount examples, and 10% a year compounded monthly for the monthly saving example. All rates are invented.

- **Future value:** ₹1,000 today becomes ₹1,050 in one year and about ₹1,276 in five years (1,000 × 1.05^5).
- **Present value:** ₹1,000 promised in five years is worth about ₹783.53 today (1,000 ÷ 1.05^5).
- **Monthly saving:** ₹5,000 a month at 10% a year (compounded monthly) grows to about ₹37.97 lakh after 20 years and about ₹1.90 crore after 35 years. The extra 15 years of saving, ₹9 lakh more paid in, add about ₹1.52 crore, because the early deposits keep compounding.

Taxes, fees and inflation are ignored.

## Misconceptions

- "Time value of money is just inflation." Even with no inflation, money available now can be put to use.
- "The formula predicts what I will have." It converts an assumed rate into a number; actual returns vary.
- "The growth is linear, so doubling the time doubles the result." It compounds, so the result grows faster than the time.
- "Present value means what the money costs today." It is the amount that would grow to the future sum at the assumed rate.

## Source References

- [Beginner's Guide to the Capital Markets, SEBI (PDF)](https://investor.sebi.gov.in/pdf/reference-material/beginners.pdf): the statement of time value and its ₹1,000 at 5% example. **Directly fetched and read on 2026-11-17** (passage re-read on 2026-11-18). The formulas and all other figures were computed in code.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-18: concept read directly; all other numbers computed in code; the guide's own long-run illustration not reproduced |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | Global concept |
| Next review due | Before production indexing |
