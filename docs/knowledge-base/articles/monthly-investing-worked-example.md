---
article_id: monthly-investing-worked-example
title: "Monthly Investing: A Worked Example"
topic: worked-examples
summary: "A step-by-step calculation of how a fixed monthly investment grows under assumed returns, showing the effect of time and rate, with every figure labelled as hypothetical."
source_urls:
  - https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf
  - https://www.amfiindia.com/uploads/AMFI_Understanding_Mutual_Funds_IAP_Booklet_Final_Website_version_860a5b77aa.pdf
claim_sources: {}
jurisdiction: india
risk_level: normal
last_verified_at: "2026-11-17"
review_due_at: null
version: 1
related_articles:
  - sips-and-periodic-investing
  - compound-interest
  - cagr-vs-xirr
  - past-performance-and-survivorship-bias
---

# Monthly Investing: A Worked Example

## Purpose

After reading this, the agent should be able to walk through the arithmetic of a monthly investment, explain which assumptions drive the result, and make clear that the numbers illustrate a method and are not a forecast of any real investment.

## Core Concepts

- A **monthly investment** adds the same amount each month. Each instalment starts growing from the month it is made, so early instalments grow for longer than late ones.
- The **formula** (instalments at the end of each month, with the assumed annual return divided evenly across 12 months): future value = P × ((1 + r)^n − 1) ÷ r, where P is the monthly amount, r the monthly rate (annual rate ÷ 12) and n the number of months.
- Three **assumptions** decide the result: the monthly amount, the length of time, and the return. Real returns are not steady; they vary from month to month and can be negative.
- **Total invested** is simply the monthly amount times the number of months. The rest of the final value is the *assumed* growth.
- **Time matters more than it feels:** doubling the period usually more than doubles the final value because growth builds on earlier growth (see "Compound Interest").
- **A real SIP's return** is measured with XIRR, which allows for the dates of each instalment (see "CAGR vs. XIRR vs. Absolute Returns").
- SEBI's Financial Education Booklet shows the same effect with a ₹1,000 investment compounding at 9%, and AMFI's SIP illustration shows how a fixed amount buys more units when the price is low and fewer when it is high, noting it "doesn't guarantee profits or prevent losses".

## Worked Example

**Setup (all assumed):** ₹5,000 invested at the end of each month. The assumed annual return is applied as annual ÷ 12 each month. No charges or taxes. Figures are rounded to the nearest rupee.

| Assumed annual return | After 5 years (₹3,00,000 invested) | After 10 years (₹6,00,000 invested) | After 20 years (₹12,00,000 invested) |
|---|---|---|---|
| 0% (no growth) | ₹3,00,000 | ₹6,00,000 | ₹12,00,000 |
| 6% | ₹3,48,850 | ₹8,19,397 | ₹23,10,204 |
| 10% | ₹3,87,185 | ₹10,24,225 | ₹37,96,844 |
| 12% | ₹4,08,348 | ₹11,50,193 | ₹49,46,277 |

**Reading the table:**

- At 0% the investor only gets back what was put in: the table's first row is the "no growth" baseline.
- At an assumed 10% for 10 years, ₹6,00,000 put in becomes about ₹10,24,225: about ₹4,24,225 of assumed growth.
- Going from 10 to 20 years at the same 10% does not double the result, it multiplies it by about 3.7 (₹10.2 lakh to ₹38.0 lakh), while the amount invested only doubles. That is compounding at work.
- A **higher assumed return** has a big effect over long periods: after 20 years the 12% row is about ₹11.5 lakh larger than the 10% row, from a difference of two percentage points. This is also why small differences in cost matter (see "Expense Ratios and Fees").
- If the actual return were 6% instead of 10%, the 20-year value would be about ₹23.1 lakh rather than ₹38.0 lakh. The method is exact; the result depends entirely on the assumed rate, which nobody can know in advance.

## Misconceptions

- "These figures are what a SIP will give." They are arithmetic on assumed rates; real returns are uncertain and can be below the amount invested.
- "Returns are earned smoothly every month." They fluctuate; the average over a period may hide big swings.
- "Starting late is the same as starting early with a bigger amount." Time has an outsized effect; the table shows how the same monthly amount grows over different periods.
- "Taxes and costs do not matter." They reduce the final amount; this example ignores both for simplicity.

## Source References

- [Financial Education Booklet, SEBI (2020) (PDF)](https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf), Chapter 2 (power of compounding, rupee cost averaging). **Directly fetched and read on 2026-11-17.**
- [Mutual Funds Made Simple, AMFI booklet (PDF)](https://www.amfiindia.com/uploads/AMFI_Understanding_Mutual_Funds_IAP_Booklet_Final_Website_version_860a5b77aa.pdf): the SIP illustration and disclaimer. **Directly fetched and read on 2026-11-17.**
- **The table was computed in code** with the formula above (ordinary monthly annuity, monthly compounding). It was not copied from either source. All rates are assumptions.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-17: sources read directly; every figure recomputed in code |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | India |
| Next review due | Before production indexing |
