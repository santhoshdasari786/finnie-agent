---
article_id: money-market-instruments
title: "Money Market Instruments: Treasury Bills, Commercial Paper and Certificates of Deposit"
topic: products
summary: "What short-term money market instruments are, how treasury bills, commercial paper and certificates of deposit are issued at a discount, and how a discount price converts to a yield, including a worked example and why quoted yields can differ by convention."
source_urls:
  - https://investor.sebi.gov.in/pdf/reference-material/beginners.pdf
claim_sources:
  instruments: "SEBI Beginner's Guide: money market instruments are loan instruments up to one year; treasury bills are issued by the government at a discount with maturities of 14 to 365 days, commercial papers by companies and certificates of deposit by banks, both at a discount with maturities of 90 to 365 days"
jurisdiction: india
risk_level: time-sensitive
last_verified_at: "2026-11-18"
review_due_at: "2027-05-18"
version: 1
related_articles:
  - government-securities
  - credit-risk-and-credit-ratings
  - fixed-and-recurring-deposits
  - mutual-fund-scheme-categories
  - liquidity-safety-and-return
---

# Money Market Instruments: Treasury Bills, Commercial Paper and Certificates of Deposit

## Purpose

After reading this, the agent should be able to name the main money market instruments, explain issue at a discount and how to convert the price to an annualised yield, and note that quoted yields depend on convention and that maturities and rules should be verified.

## Core Concepts

- SEBI's Beginner's Guide describes **money market instruments** as loan instruments with a tenure of **up to one year**.
- **Treasury bills (T-bills)** are short-term instruments issued by the government for its cash management. They are **issued at a discount to face value** and repay face value at maturity; the guide gives maturities from 14 to 365 days.
- **Commercial papers (CPs)** are short-term **unsecured** instruments issued by companies for cash management, also at a discount; the guide gives maturities of 90 to 365 days.
- **Certificates of deposit (CDs)** are short-term **unsecured** instruments issued by banks, at a discount, with maturities of 90 to 365 days in the guide.
- **No periodic interest:** the investor's return is the difference between the discounted purchase price and the face value received at maturity.
- **Risk differs by issuer:** T-bills are sovereign borrowing, the guide says government securities are free from the risk of default (credit risk). Commercial paper and bank certificates are unsecured, so the issuer's creditworthiness matters, and they carry credit ratings.
- **Why they matter to individuals:** they are the main holdings behind liquid, overnight and money market funds, whose categories are defined by how short the maturities are, and they are used by institutions to park cash.
- A short maturity means **lower sensitivity to interest-rate changes** than long bonds, though not none.
- The annualised yield on a discount instrument depends on a **day-count convention**, so different sources can quote slightly different yields for the same price.
- The ranges of maturity above are those given in an older guide; verify the current ones in RBI or SEBI documents.

## Worked Example

The guide's illustration: a T-bill issued at ₹98.50 matures at ₹100 in 91 days, and the guide says this offers a yield of 6.25% a year.

Computed in code from those two prices:

- Gain = ₹1.50 on ₹98.50 invested = about 1.52% over 91 days.
- Annualised on a 365-day year: 1.523% × 365 ÷ 91 ≈ **6.11%**.
- On a 360-day basis it is about 6.02%.

So the guide's 6.25% is slightly higher than either of these simple annualisations; the guide does not state its method, and different conventions give different figures. The lesson is that the same price can be quoted as slightly different yields, so compare yields on the same basis.

The prices are the guide's illustration, not a market quote.

## Misconceptions

- "T-bills pay interest every month or six months." They are bought at a discount and repaid at face value.
- "All money market instruments are as safe as government paper." Commercial paper and certificates of deposit depend on the issuer.
- "Short term means no risk." The price can still move, and unsecured instruments can default.
- "A quoted yield is exact." It depends on the convention used.

## Source References

- [Beginner's Guide to the Capital Markets, SEBI (PDF)](https://investor.sebi.gov.in/pdf/reference-material/beginners.pdf): instruments, maturity ranges and the T-bill example. **Directly fetched and read on 2026-11-17** (passage re-read on 2026-11-18). An older guide; current RBI rules were not read. The yield recomputation is mine, and I could not reproduce the guide's 6.25%.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-18: guide passage read; yield recomputed in code; the guide's stated yield not reproduced |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | India |
| Next review due | 2027-05-18 |
