---
article_id: etf-structure-and-premium-discount
title: "How ETFs Work: Creation, Market Price and NAV"
topic: products
summary: "How an exchange-traded fund differs from a mutual fund in how it is bought and sold, why its market price can differ from its NAV, how arbitrage keeps the gap small, and what extra costs the spread adds."
source_urls:
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-24
claim_sources:
  trading: "Investor.gov ETF bulletin (Feb 2023): ETFs do not sell or redeem individual shares directly with retail investors; shares trade throughout the day on exchanges at market prices"
  premium_discount: "same bulletin: an ETF's market price is typically more or less than its NAV per share (a premium or discount), kept close to NAV by arbitrage"
jurisdiction: global
risk_level: normal
last_verified_at: "2026-11-18"
review_due_at: null
version: 1
related_articles:
  - mutual-funds-and-etfs
  - index-vs-active-funds
  - bid-ask-spreads-and-slippage
  - expense-ratios-and-fees
  - mutual-fund-scheme-categories
---

# How ETFs Work: Creation, Market Price and NAV

## Purpose

After reading this, the agent should be able to explain how an ETF is created and traded, why its price on the exchange can differ from the value of what it holds, and which costs a buyer should look at, without comparing specific funds.

## Core Concepts

- An **ETF** (exchange-traded fund) pools money into a portfolio, like a mutual fund, and each share represents proportionate ownership of the portfolio and the income it generates (Investor.gov bulletin, which covers US-registered ETFs).
- Like a mutual fund, an ETF calculates its **NAV per share**: the value of all its assets minus all its liabilities, divided by the number of shares, every business day.
- An ETF can be **index-based** (it aims to track an index) or **actively managed**.
- **Unlike a mutual fund**, an ETF does not sell or redeem individual shares directly to retail investors. Retail investors buy and sell ETF shares on an exchange, **at market prices that move through the day**.
- **Creation and redemption:** only large financial institutions called **Authorized Participants** deal with the ETF directly, in large blocks called creation units, usually exchanging a basket of securities for ETF shares, or the reverse. They can then sell the shares on the exchange.
- **Premium or discount:** because the market price moves with supply and demand during the day, it can be higher than NAV (a premium) or lower (a discount). The bulletin says arbitrage, taking advantage of a price difference between two markets, tends to keep the market price close to NAV, as Authorized Participants can trade at NAV with the fund and at market price on the exchange.
- **There is a risk that a trading market may not develop** for some ETFs, so the price paid or received can be less favourable than NAV.
- **Bid-ask spread:** like any exchange-traded security, an ETF has a bid and an ask price, and the difference is the spread. The bulletin's example is a share quoted $59.50 bid and $60 ask, a spread of 50 cents.
- **Costs:** the bulletin says ETFs have tended to be less expensive to run than similar mutual funds, but buyers may also pay brokerage commissions and trading costs. Fees are in the fund's prospectus.
- In India the same idea applies to ETFs listed on Indian exchanges, but details such as the market makers' role and taxes were not read for this article.

## Worked Example

A hypothetical ETF has a NAV of ₹100.00 per unit at the end of the day.

- During the day it trades at ₹101.20 on the exchange, a **premium** of ₹1.20, or 1.2% of NAV. A buyer paying ₹101.20 pays more than the units' underlying value.
- On another day it trades at ₹99.40: a **discount** of ₹0.60, or 0.6%.
- Suppose the quote is bid ₹99.90, ask ₹100.10. An investor who buys 200 units at the ask and sells them at once at the bid loses ₹0.20 × 200 = ₹40 before brokerage.

The prices are invented to show the arithmetic.

## Misconceptions

- "The ETF price is always its NAV." The market price moves during the day and can differ from NAV.
- "ETFs have no costs because there is no entry load." Spreads, brokerage and the fund's own fees still apply.
- "I buy ETF units from the fund house." Retail investors buy from other market participants on the exchange.
- "A low premium means the fund is cheap." A premium or discount describes price versus NAV, not cost or quality.

## Source References

- [Updated Investor Bulletin: Exchange-Traded Funds (ETFs), SEC Investor.gov (Feb 2023)](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-24): structure, creation and redemption, premium or discount, arbitrage, spread, fees. **Directly fetched and read on 2026-11-18.** It describes US-registered ETFs; Indian ETF rules and taxes were not read.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-18: bulletin read directly; examples computed in code |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | Global concept (US source) |
| Next review due | Before production indexing |
