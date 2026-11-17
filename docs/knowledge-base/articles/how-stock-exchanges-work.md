---
article_id: how-stock-exchanges-work
title: "How Stock Exchanges Work"
topic: products
summary: "How a share trade moves from an order through a broker and the exchange to settlement in a demat account, who the participants are, and what protections exist."
source_urls:
  - https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf
  - https://investor.sebi.gov.in/pdf/reference-material/beginners.pdf
claim_sources:
  settlement_cycle: "SEBI/exchange circulars; exchanges moved all equity to T+1 from 27 January 2023 (search summary of exchange circulars; the SEBI booklet above still says T+2 because it is older)"
jurisdiction: india
risk_level: time-sensitive
last_verified_at: "2026-11-17"
review_due_at: null
version: 1
related_articles:
  - stocks-and-shares
  - how-financial-markets-work
  - brokerage-stt-and-trading-charges
  - verifying-a-financial-intermediary
---

# How Stock Exchanges Work

## Purpose

After reading this, the agent should be able to walk through what happens between placing an order and owning shares in a demat account, name the participants and their roles, and explain which parts of the process are time-sensitive and should be confirmed with current official sources.

## Critical Constraint

**Settlement timing has changed over the years and may change again.** The SEBI booklet cited here describes a T+2 cycle; Indian exchanges have since moved to T+1, and optional faster settlement has also been introduced. When a question depends on exactly when money or shares arrive, point the user to the current exchange or SEBI notice instead of stating a fixed number as current fact.

## Core Concepts

- India's main stock exchanges are **BSE** and the **NSE**, both recognised by SEBI (SEBI Financial Education Booklet). Anyone can buy on the secondary market as long as they pay the price at which securities are trading.
- To trade, an investor needs a **trading account** with a **SEBI-registered stock broker** and a **demat account** to hold shares electronically. KYC (Know Your Client) is mandatory and can be completed online or offline.
- **Orders** can be placed through the broker's website or mobile app, by phone ("call and trade"), or in person. The booklet's word of caution: buying or selling "shall always be done through a SEBI registered stock broker".
- **Trading days:** trading takes place on weekdays except exchange holidays.
- **Settlement:** after a trade, funds and shares are exchanged through the exchange and the brokers. The days between trade and settlement are written **T+n** (T = the trade day). The SEBI booklet describes the older T+2; exchange circulars moved all equity to **T+1 from 27 January 2023**.
- A **contract note** is the broker's legal evidence of the trade: securities, price, time, brokerage and charges. The booklet advises asking for a valid contract note within 24 hours.
- **Pay-in and pay-out** are the settlement days on which funds or shares move between broker and exchange.
- **Margin** means paying only part of the price up front and borrowing the rest from the broker; margin pledges are created on shares in the demat account (see "Leverage, Margin and Forced Liquidation").
- **Protections:** the exchanges run arbitration for disputes and investor protection funds that compensate investors when a broker is declared a defaulter, and depositories indemnify investors for loss through their own or a participant's negligence (SEBI Beginner's Guide).

## Worked Example

A hypothetical purchase, described in steps without prices:

1. The investor places a buy order for shares of a listed company through a SEBI-registered broker's app.
2. The order reaches the exchange and is matched with a seller at an agreed price.
3. The broker sends a contract note showing the trade, the brokerage and other charges.
4. On the settlement day (T+1 under today's cycle), the money goes out and the shares arrive in the investor's demat account.
5. The investor's holding shows in the demat statement; the shares are now the investor's.

If the investor sells later, the process runs in reverse: shares leave the demat account and money reaches the bank account after settlement.

## Misconceptions

- "The exchange sells you the shares." The exchange is a marketplace. You buy from other investors through your broker.
- "The money and shares move instantly." Settlement takes a defined number of trading days after the trade; the length of that gap is set by exchange rules.
- "Dabba trading is just a cheaper way to trade." SEBI's booklet states it is **illegal** and offers none of the protections of exchange trades.
- "Any app that shows stock prices is a broker." Only a SEBI-registered broker can legitimately execute your trades (see "How to Verify a Financial Intermediary").

## Source References

- [Financial Education Booklet, SEBI (2020) (PDF)](https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf), Chapter 5 on orders, settlement, contract notes, margin and the do's and don'ts. **Directly fetched and read on 2026-11-17.** Its T+2 description is out of date.
- [Beginner's Guide to the Capital Markets, SEBI (PDF)](https://investor.sebi.gov.in/pdf/reference-material/beginners.pdf): investor protection mechanisms. **Directly fetched and read on 2026-11-17.**
- **T+1 since 27 January 2023** was confirmed from a web-search summary of NSE and BSE circulars and SEBI documents; the circulars themselves were not read in this pass. Verify the current settlement cycle on the exchanges' websites.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-17: SEBI documents read directly; the current settlement cycle rests on a search summary, hence `time-sensitive` |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | India |
| Next review due | Whenever SEBI or the exchanges change the settlement cycle; otherwise within a year |
