---
article_id: leverage-and-margin
title: "Leverage, Margin and Forced Liquidation"
topic: behaviour-risk
summary: "How borrowing to invest magnifies both gains and losses, how margin and margin calls work, and why a leveraged position can be closed at a loss without the investor's consent."
source_urls:
  - https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-29
  - https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf
claim_sources: {}
jurisdiction: global
risk_level: normal
last_verified_at: "2026-11-17"
review_due_at: null
version: 1
related_articles:
  - corrections-bear-markets-and-recovery
  - how-stock-exchanges-work
  - volatility-vs-permanent-loss
  - investing-vs-saving-vs-speculating
---

# Leverage, Margin and Forced Liquidation

## Purpose

After reading this, the agent should be able to explain leverage and margin, show how borrowing magnifies outcomes both ways, and describe a margin call and forced sale, without encouraging or discouraging any user's decision to borrow.

## Core Concepts

- **Leverage** means investing with borrowed money, or with a product that gives exposure larger than the money put in. It magnifies gains *and* losses on the investor's own money.
- **Margin** is the portion of a purchase the investor pays up front; the broker finances the rest. SEBI's booklet: when buying a stock, an investor can pay the whole price, or "pay only a certain percentage of the price of the stock and borrow money from the broker to finance the rest. The percentage of the price of the stock paid upfront is called margin."
- In India, margin in the form of securities is given to the broker by a **pledge** over shares in the investor's demat account, done on the investor's instruction (SEBI Financial Education Booklet).
- **Margin call:** when the value of the securities falls, the investor may have to add cash or securities. The SEC's Investor Bulletin warns that investors "may be required to provide the broker with additional cash or securities if the price of the stock falls".
- **Forced liquidation:** the broker may sell the investor's securities without notice. The bulletin lists, among the risks of a margin account: you "can lose more money than you have invested"; you "may have to deposit additional cash or securities in your account on short notice"; your firm "may sell some or all of your securities without consulting you"; you are "not entitled to choose which securities" are sold; the firm "can increase its margin requirements at any time"; and you are "not entitled to an extension of time on a margin call".
- **Interest** is paid on borrowed money, which adds a cost whether or not the investment gains.
- **Derivatives** such as futures and options give leveraged exposure. SEBI's booklet notes that trading in futures and options "is riskier than the cash segment" because the contracts are time-dependent.
- SEBI's do's and don'ts for the securities market include: **"Don't borrow money for investment."**
- A forced sale tends to happen at the worst time: when prices have already fallen, which is when borrowed positions are tested.

## Worked Example

A hypothetical comparison of two investors buying ₹2,00,000 of the same shares, ignoring interest and charges:

- Investor A pays the full ₹2,00,000 with own money.
- Investor B puts in ₹1,00,000 of own money and borrows ₹1,00,000.

| Shares move | A's result on ₹2,00,000 | B's result on own ₹1,00,000 |
|---|---|---|
| +10% | +₹20,000 (+10%) | +₹20,000 (+20%) |
| -10% | -₹20,000 (-10%) | -₹20,000 (-20%) |
| -30% | -₹60,000 (-30%) | -₹60,000 (-60%) |
| -50% | -₹1,00,000 (-50%) | -₹1,00,000 (-100%) |

B's own money is wiped out when shares fall 50%, and a broker would normally demand more margin or sell well before that point. A fall beyond 50% would leave B owing money. Interest on the loan would make every row for B worse.

## Misconceptions

- "Leverage only magnifies gains." It magnifies losses equally, and the loan must be repaid either way.
- "I can wait out a fall on margin." A margin call or a forced sale can end the position before any recovery.
- "I can choose what gets sold." The broker typically decides, and may sell without consulting you.
- "Only large traders use leverage." Retail investors use it through margin accounts and derivatives.

## Source References

- [Investor Bulletin: Understanding Margin Accounts, SEC Investor.gov](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-29): the list of margin risks and the margin-call example. **Directly fetched and read on 2026-11-17.** It describes U.S. rules; the risks described apply in principle to margin trading elsewhere, but Indian margin rules and limits differ and were not read here.
- [Financial Education Booklet, SEBI (2020) (PDF)](https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf): margin, pledge, derivatives risk, "don't borrow money for investment". **Directly fetched and read on 2026-11-17.**

## Review Metadata

| Field | Value |
|---|---|
| Last verified | 2026-11-17: SEC and SEBI texts read directly; example computed in code; Indian margin-rule details not read |
| Reviewer | none (AI-assisted only, no qualified human reviewer) |
| Jurisdiction | Global concept, Indian operating details |
| Next review due | Before production indexing |
