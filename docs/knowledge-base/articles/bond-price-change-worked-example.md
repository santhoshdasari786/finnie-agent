---
article_id: bond-price-change-worked-example
title: "How a Bond's Price Can Change Before Maturity: A Worked Example"
topic: worked-examples
summary: "A step-by-step calculation of how a bond's market price moves when interest rates change, why longer bonds move more, and why holding to maturity returns the face value."
source_urls:
  - https://investor.sebi.gov.in/pdf/reference-material/beginners.pdf
  - https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf
claim_sources: {}
jurisdiction: india
risk_level: normal
last_verified_at: "2026-11-17"
review_due_at: null
version: 1
related_articles:
  - bonds-and-interest-rate-risk
  - government-securities
  - credit-risk-and-credit-ratings
  - risk-vs-return
---

# How a Bond's Price Can Change Before Maturity: A Worked Example

## Purpose

After reading this, the agent should be able to walk through how a bond's price is worked out from interest rates, show that prices fall when rates rise and rise when rates fall, show why a longer bond is more sensitive, and explain that holding to maturity returns the face value, using only the hypothetical figures here.

## Core Concepts

- A **bond** pays a fixed interest amount (the **coupon**) on set dates and repays the **face value** at maturity (SEBI Beginner's Guide on debentures and bonds).
- The bond's **market price** is the present value of those future payments, discounted at the interest rate (yield) that investors currently demand for a similar bond.
- Formula used below: price = sum of each year's coupon ÷ (1 + y)^t, plus face value ÷ (1 + y)^n, where y is the market yield, t the year of each payment and n the years to maturity.
- If the **market yield equals the coupon rate**, the price equals the face value. If market yields **rise above** the coupon, the bond's fixed payments are less attractive and the price **falls below** face value. If yields **fall below** the coupon, the price **rises above** face value.
- **Longer maturity means a larger price move** for the same change in yield, because more payments lie further in the future.
- **Held to maturity**, a bond's price converges to its face value, and the investor receives all coupons plus the face value, provided the issuer does not default (see "Credit Risk and Credit Ratings"). A fall in price matters mainly to someone who sells early.
- Government securities have no default risk but have this price risk (see "Government Securities and Treasury Bills").

## Worked Example

**Setup (hypothetical):** a bond with face value ₹1,000, five years to maturity, paying an 8% coupon (₹80) once a year. Figures are rounded to the nearest paisa.

**A. Price today if market yields change**

| Market yield | Price of the 5-year bond | Compared with face value |
|---|---|---|
| 7% | ₹1,041.00 | above (₹41.00 more) |
| 8% | ₹1,000.00 | equal |
| 9% | ₹961.10 | below (₹38.90 less) |
| 10% | ₹924.18 | below (₹75.82 less) |

At 9%: the ₹80 coupons for years 1 to 5 and the ₹1,000 repayment, each discounted at 9%, add up to ₹961.10.

**B. The same 9% yield for bonds of different length (all with an 8% coupon)**

| Years to maturity | Price at 9% yield |
|---|---|
| 2 | ₹982.41 |
| 5 | ₹961.10 |
| 10 | ₹935.82 |

The longer the bond, the larger the fall for the same one-percentage-point rise.

**C. Time pulls the price toward face value.** One year later, with four years left and the yield still 9%, the price is ₹967.60, closer to ₹1,000 than ₹961.10. With four years left and a yield of 7% it is ₹1,033.87.

**D. If held to maturity.** An investor who bought at ₹961.10 and holds receives ₹80 a year for five years and ₹1,000 at the end, regardless of what the price did in between (assuming no default).

## Misconceptions

- "Bonds are safe, so their price never falls." The price can fall when rates rise, even for a government bond.
- "A bond's price falling means I lose the coupon." Coupons are fixed; the price reflects what buyers will pay for them now.
- "Longer bonds and shorter bonds behave the same." Longer bonds move more for the same change in rates.
- "These prices predict what bonds will do." The yields are assumptions chosen to show the method.

## Source References

- [Beginner's Guide to the Capital Markets, SEBI (PDF)](https://investor.sebi.gov.in/pdf/reference-material/beginners.pdf): debentures, bonds, G-secs. **Directly fetched and read on 2026-11-17.**
- [Financial Education Booklet, SEBI (2020) (PDF)](https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf): risks including market and interest-related risk. **Directly fetched and read on 2026-11-17.**
- **All prices were computed in code** from the formula above and checked by consistency (price at 8% yield equals face value). They are not taken from any source, and the yields are assumptions.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-17: sources read directly; every price recomputed in code |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | India (global concept) |
| Next review due | Before production indexing |
