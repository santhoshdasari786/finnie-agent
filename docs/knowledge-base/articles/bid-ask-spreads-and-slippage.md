---
article_id: bid-ask-spreads-and-slippage
title: "Bid-Ask Spreads, Slippage and Hidden Trading Costs"
topic: costs-taxes
summary: "How the gap between the buying and selling price, and the way large or fast orders move the price, add a cost to trading that is not shown as a fee, and how limit orders manage it."
source_urls:
  - https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-24
claim_sources:
  market_order: "Investor.gov: a market order guarantees execution but not price, and generally fills at or near the current bid (sell) or ask (buy); the last-traded price is not necessarily the execution price"
  limit_order: "Investor.gov: a limit order buys or sells at a specific price or better, but is not guaranteed to execute"
jurisdiction: global
risk_level: normal
last_verified_at: "2026-11-18"
review_due_at: null
version: 1
related_articles:
  - brokerage-stt-and-trading-charges
  - how-stock-exchanges-work
  - comparing-investment-products-fairly
  - mutual-funds-and-etfs
---

# Bid-Ask Spreads, Slippage and Hidden Trading Costs

## Purpose

After reading this, the agent should be able to explain what the bid and ask are, why buying and immediately selling the same share loses money even if the "price" has not moved, what slippage is, and how order types change the price an investor gets.

## Core Concepts

- The **bid** is the highest price a buyer in the market is currently willing to pay. The **ask** (or offer) is the lowest price a seller is currently willing to accept. The **bid-ask spread** is the ask minus the bid. The Investor.gov ETF bulletin gives the same definitions, with the spread as the difference between the two prices (its example: bid $59.50, ask $60.00, a spread of 50 cents).
- An investor who wants to buy at once generally pays near the **ask**; an investor who wants to sell at once generally receives near the **bid**. The spread is therefore a cost of trading immediately, paid to the other side of the trade rather than to a broker.
- A **market order** buys or sells immediately. It guarantees that the order will be executed but not the price; it generally executes at or near the current bid (for a sell) or ask (for a buy), and the last-traded price is not necessarily the price at which it will execute (Investor.gov).
- A **limit order** buys or sells at a specific price or better. A buy limit can only execute at the limit price or lower, a sell limit at the limit price or higher. It controls the price but is not guaranteed to execute at all.
- **Slippage** is the difference between the price expected when the order was placed and the average price actually obtained. It is larger when an order is big compared with what is on offer at the best price, or when prices are moving fast.
- Spreads are usually narrower for heavily traded securities and wider for thinly traded ones, which is one reason liquidity matters when comparing investments.
- These costs add to visible charges such as brokerage and taxes on each trade, so frequent trading pays them repeatedly.

## Worked Example

A hypothetical share has a bid of ₹99.90 and an ask of ₹100.10.

- The spread is ₹100.10 − ₹99.90 = ₹0.20, which is 0.2% of ₹100.
- An investor who buys 1,000 shares at the ask and immediately sells them at the bid, with the market unchanged, loses ₹0.20 × 1,000 = ₹200 before brokerage and taxes.

Now suppose a market order to buy 1,000 shares finds these offers: 300 shares at ₹100.10, 400 at ₹100.20 and 300 at ₹100.30.

- Total cost = 300 × 100.10 + 400 × 100.20 + 300 × 100.30 = ₹1,00,200, so the average price is ₹100.20.
- Compared with the best ask of ₹100.10, the slippage is ₹0.10 a share, or ₹100 on the order.
- A buy limit order at ₹100.10 would have filled only the first 300 shares and left the rest waiting, trading price protection for the chance of not completing.

The prices and quantities are invented for illustration.

## Misconceptions

- "If there is no brokerage, there is no cost." The spread and slippage are costs even with zero brokerage.
- "The last traded price is what I will get." A market order can fill at a different price, especially in fast or thin markets.
- "A limit order is always better." It protects the price but may not execute, and the investor can miss the move they wanted.
- "Spreads only matter to large traders." A small order still crosses the spread, and for thinly traded securities the spread can be a large share of the price.

## Source References

- [Types of Orders, SEC Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders): market and limit orders, and where market orders execute relative to bid and ask. **Directly fetched and read on 2026-11-18.** It describes U.S. markets; the mechanics of order types are the same idea on Indian exchanges, but exchange-specific rules were not read here.
- [Updated Investor Bulletin: Exchange-Traded Funds (ETFs), SEC Investor.gov](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-24): the definitions of bid, ask and spread and the $59.50 / $60 example. **Directly fetched and read on 2026-11-18.** The Investor.gov glossary entries for "bid-and-ask" and "bid-ask spread" loaded without readable text.

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-18: order-type claims read from Investor.gov; the example computed in code; spread definition confirmed from the ETF bulletin |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | Global concept |
| Next review due | Before production indexing |
