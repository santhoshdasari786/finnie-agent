---
article_id: bonds-and-interest-rate-risk
title: Bonds and Interest-Rate Risk
topic: products
summary: What a bond actually is, how its market price moves as interest rates change, and why "fixed income" doesn't mean "fixed value."
source_urls:
  - https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=711
  - https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds
claim_sources: {}
jurisdiction: global
risk_level: normal
last_verified_at: "2026-10-22"
review_due_at: null
version: 1
related_articles:
  - risk-vs-return
  - nominal-vs-real-returns
---

# Bonds and Interest-Rate Risk

## Purpose

After reading this, the agent should be able to explain what a bond is, why its market price moves inversely to prevailing interest rates, and distinguish holding a bond to maturity from selling it early.

## Core Concepts

- A **bond** is essentially a loan: the issuer (government or company) borrows money from investors and promises to pay periodic interest (the **coupon**) plus return the **principal** at **maturity**.
- If held to maturity and the issuer doesn't default, a bond's cash flows (coupons + principal) are generally known in advance — this is why bonds are called "fixed income."
- However, a bond's **market price before maturity** can fluctuate — and it generally moves **inversely** to prevailing interest rates: when rates rise, existing bonds with lower fixed coupons become less attractive relative to newly issued bonds, so their market price falls (and vice versa when rates fall).
- **Credit risk** is separate from interest-rate risk: it's the risk the issuer fails to pay interest or principal at all, independent of rate movements (see "Credit Risk and Credit Ratings"). Government securities (G-Secs) are the clearest illustration of this split — per RBI's own investor FAQ, they "carry practically no risk of default and, hence, are called risk-free gilt-edged instruments," yet their market price still moves with interest rates like any other bond.
- **Duration** (a bond's sensitivity to rate changes) is generally longer for longer-maturity bonds — RBI's primer gives a concrete example: a 2-year bond with a 10% coupon, priced at ₹101.79, has a duration of about 1.86 years. Duration rises with maturity, so short-maturity bonds suit investors who specifically want to limit interest-rate risk.

## Worked Example

Illustrative, simplified scenario: a bond pays a fixed 6% annual coupon. If newly issued, comparable bonds start offering 8% (rates rose), the 6%-coupon bond becomes less attractive at its original price — its market price must fall so that a *new* buyer's effective return (coupon + price discount) is roughly in line with the new 8% market rate. The reverse happens if new bonds start offering only 4%: the existing 6% bond becomes more attractive, and its market price rises.

*(Specific rate figures above are illustrative only, to demonstrate the inverse-price mechanism — not a prediction or current rate data.)*

## Misconceptions

- "Fixed income" describes the promised cash flows (coupon + principal if held to maturity), not a fixed *market price* at every point in time before maturity.
- An investor who holds a bond to maturity and the issuer doesn't default generally still receives the promised cash flows, even if the bond's market price fluctuated in the interim — interim price moves only matter if selling before maturity.
- Interest-rate risk and credit risk are different things — a bond can have low credit risk (reliable issuer) but still show meaningful price swings purely from rate changes.

## Source References

- [Government Securities Market in India — RBI FAQs](https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=711) (official RBI, dated 1 April 2020) — **directly fetched and read in full**; source of the risk-free/gilt-edged quote and the duration worked example above. Also confirms: "the yield of a bond is inversely related to its price" (the core mechanic this article explains), and that price movements are driven by interest rates, inflation expectations, liquidity, and RBI policy actions.
- [Bonds — Investor.gov FAQs](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds) — **not independently fetch-confirmed**: investor.gov returns 403 Forbidden to automated fetches; this citation rests on general knowledge of the page's likely content, not verified text.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-10-22 — RBI content directly verified via full page fetch; Investor.gov citation not independently confirmed (site blocks automated access) |
| Reviewer | — (AI-assisted only) |
| Jurisdiction | Global concept; RBI-sourced details are India-specific |
| Next review due | Before production indexing |
