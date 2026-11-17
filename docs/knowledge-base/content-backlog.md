# Financial Knowledge Base — Content Backlog

This is the content plan behind the RAG knowledge base shared by the **Finance Q&A Agent** ([`../agents/finance_qa_agent.md`](../agents/finance_qa_agent.md)) and the **Tax Education Agent** ([`../agents/tax_education_agent.md`](../agents/tax_education_agent.md)) — see [`../TECHNICAL_DESIGN.md`](../TECHNICAL_DESIGN.md) §4 for how it's indexed and retrieved. It answers the "what 50–100 articles, from which sources, in what format" question those docs' Definition of Done checklists assume but don't spell out.

**Goal:** make the agent a trustworthy financial educator — it explains concepts, demonstrates calculations, compares instruments objectively, clarifies risks, and cites its sources for every substantive claim. Approach: an **India-first knowledge base with globally applicable investing fundamentals** — mutual funds, inflation, taxation, fees, and fixed-income products framed for Indian users, without limiting the core learning material (compounding, diversification, risk/return) to one country.

---

## 1. Knowledge Base Structure

| Category | Articles | Covers |
|---|---|---|
| A. Investing foundations | 12 | Money, risk, returns, asset classes, investing principles |
| B. Growth and portfolio concepts | 12 | Compounding, diversification, allocation, rebalancing, benchmarks |
| C. Financial products and instruments | 16 | Stocks, mutual funds, ETFs, bonds, deposits, gold, retirement products |
| D. Costs, taxes, and financial mechanics | 12 | Fees, brokerage, taxes, inflation, liquidity, real returns |
| E. Investor behaviour and risk | 10 | Biases, volatility, drawdowns, scams, market myths |
| F. Safety, regulation, and investor protection | 8 | Regulators, disclosures, fraud prevention, product risks |
| G. Worked examples and FAQs | 10 | Practical calculations and common questions, no personalized recommendations |
| **Total** | **80** | |

---

## 2. Full Topic List

### A. Investing foundations (12)

| # | Title | What the agent should explain |
|---|---|---|
| 1 | What Is Investing? | Investing versus saving, and how investments can generate returns |
| 2 | Saving vs. Investing vs. Speculating | Differences in purpose, risk, and uncertainty |
| 3 | How Financial Markets Work | Buyers, sellers, exchanges, brokers, and price discovery |
| 4 | Understanding Risk and Return | Why expected returns and uncertainty are connected |
| 5 | What Are Asset Classes? | Equity, debt, cash, commodities, and real estate |
| 6 | Simple Interest vs. Compound Interest | How interest accumulates under different methods |
| 7 | What Is Compounding? | Growth on accumulated earnings and the effect of time |
| 8 | Inflation and Purchasing Power | Why nominal money growth can differ from real wealth growth |
| 9 | Nominal Returns vs. Real Returns | Returns before and after inflation |
| 10 | Short-Term vs. Long-Term Investing | How time horizon changes the relevance of volatility and liquidity |
| 11 | Liquidity, Solvency, and Capital Preservation | Access to money, financial resilience, and preservation risks |
| 12 | What Does It Mean to Own an Investment? | Ownership, contractual claims, income rights, and capital risk |

### B. Growth and portfolio concepts (12)

| # | Title | What the agent should explain |
|---|---|---|
| 13 | The Power of Compounding Over Time | Illustrations of growth across different periods |
| 14 | Lump-Sum Investing vs. Periodic Investing | How contribution patterns differ and why neither guarantees better returns |
| 15 | What Is Rupee-Cost Averaging? | Investing fixed amounts at regular intervals and its limitations |
| 16 | What Is Diversification? | Spreading exposure across investments, sectors, and asset classes |
| 17 | Correlation and Portfolio Diversification | Why assets that move differently may reduce overall portfolio risk |
| 18 | What Is Asset Allocation? | The role of equity, debt, cash, and other assets in a portfolio |
| 19 | What Is Portfolio Rebalancing? | Restoring target weights and the potential costs involved |
| 20 | Risk Tolerance vs. Risk Capacity | Emotional comfort with risk versus financial ability to bear losses |
| 21 | Volatility vs. Permanent Loss | Price fluctuations compared with lasting impairment of capital |
| 22 | Understanding Benchmarks and Market Indices | What indices measure and how to interpret comparisons |
| 23 | Absolute Returns vs. CAGR vs. XIRR | Different return calculations and when each is useful |
| 24 | How to Read a Portfolio's Performance | Time periods, cash flows, fees, taxes, and appropriate comparisons |

### C. Financial products and instruments (16)

| # | Title | What the agent should explain |
|---|---|---|
| 25 | What Is a Stock or Share? | Ownership, dividends, price movements, and shareholder risk |
| 26 | How Stock Exchanges Work | Orders, trading sessions, settlement, and market participants |
| 27 | Market Capitalization and Company Size | Large-, mid-, and small-cap classifications and their limitations |
| 28 | What Are Dividends? | Dividend declarations, eligibility, payout mechanics, and uncertainty |
| 29 | What Are Bonds and Debentures? | Issuers, coupons, maturity, principal repayment, and credit risk |
| 30 | Bond Prices and Interest Rates | Why existing bond prices generally move inversely to market yields |
| 31 | Credit Risk and Credit Ratings | Default risk, rating limitations, and credit migration |
| 32 | What Are Government Securities? | Sovereign borrowing, interest-rate risk, and maturity |
| 33 | Fixed Deposits and Recurring Deposits | Interest, tenure, premature withdrawal, and applicable protections |
| 34 | What Is a Mutual Fund? | Pooling money, professional management, units, and NAV |
| 35 | Equity, Debt, and Hybrid Mutual Funds | Objectives, holdings, risks, and differences in fund categories |
| 36 | What Is an ETF? | Exchange-traded funds, pricing, tracking, and trading costs |
| 37 | Index Funds vs. Actively Managed Funds | Tracking an index versus attempting to outperform it |
| 38 | What Is an SIP? | Systematic investment plans, contribution schedules, and misconceptions |
| 39 | Gold as an Investment | Physical gold, gold ETFs, other eligible gold products, and their risks |
| 40 | PPF, EPF, NPS, and Retirement Investing | Purpose, structure, restrictions, and tax considerations of Indian retirement/long-term savings products |

### D. Costs, taxes, and financial mechanics (12)

| # | Title | What the agent should explain |
|---|---|---|
| 41 | The Impact of Investment Fees | How recurring fees reduce net returns over time |
| 42 | Expense Ratio in Mutual Funds | What the expense ratio covers and how it affects fund returns |
| 43 | Brokerage, STT, and Other Trading Charges | Common Indian equity trading charges and when they may apply |
| 44 | Direct vs. Regular Mutual Fund Plans | Distribution costs, plan differences, and investor responsibilities |
| 45 | Exit Loads, Lock-ins, and Withdrawal Restrictions | Costs and conditions associated with redeeming investments |
| 46 | Capital Gains Tax Basics in India | Capital gains, holding periods, and why tax treatment depends on the instrument and applicable law |
| 47 | Dividend Income and Taxation | How dividend distributions and tax treatment differ from capital gains |
| 48 | Tax-Efficient vs. Tax-Avoidant Investing | Lawful tax planning versus illegal evasion, with appropriate caveats |
| 49 | Pre-Tax vs. Post-Tax Returns | Comparing investments after relevant taxes and charges |
| 50 | Inflation-Adjusted Investment Returns | Calculating purchasing-power growth after inflation |
| 51 | Liquidity Costs, Bid-Ask Spreads, and Slippage | Trading frictions beyond visible fees |
| 52 | How to Compare Two Investment Products Fairly | Risk, fees, liquidity, taxation, tenure, and comparable return periods |

### E. Investor behaviour and risk (10)

| # | Title | What the agent should explain |
|---|---|---|
| 53 | Common Cognitive Biases in Investing | Familiarity, confirmation bias, anchoring, and overconfidence |
| 54 | Fear of Missing Out (FOMO) | Why popular market trends can encourage impulsive decisions |
| 55 | Herd Behaviour and Market Bubbles | How collective behaviour can amplify price movements |
| 56 | Loss Aversion and Panic Selling | Why perceived losses can influence decisions disproportionately |
| 57 | Understanding Market Corrections and Bear Markets | Common market terminology and historical drawdowns |
| 58 | Drawdown and Recovery Mathematics | Why recovering from a loss requires a larger percentage gain |
| 59 | Leverage, Margin, and Forced Liquidation | How borrowed exposure magnifies gains and losses |
| 60 | Why Past Performance Doesn't Guarantee Future Returns | Survivorship bias, changing conditions, and uncertainty |
| 61 | Common Investment Scams and Unrealistic Return Promises | Warning signs, guaranteed-return claims, impersonation, and fraud |
| 62 | Financial Influencers and Investment Misinformation | Sponsorships, conflicts of interest, unverifiable claims, and source checking |

### F. Safety, regulation, and investor protection (8)

| # | Title | What the agent should explain |
|---|---|---|
| 63 | Understanding SEBI and India's Financial Regulators | The respective roles of SEBI, RBI, IRDAI, and PFRDA |
| 64 | How to Verify a Financial Intermediary | Registration checks, official records, and verification limitations |
| 65 | Reading a Mutual Fund Factsheet | Objectives, benchmark, portfolio holdings, expenses, and risk disclosures |
| 66 | Understanding Risk Disclosures and Product Documents | Key Information Memorandums, Scheme Information Documents, and other disclosures |
| 67 | Deposit Insurance and Its Limitations in India | DICGC coverage, eligibility, limits, and exclusions |
| 68 | Nomination, Joint Holding, and Investment Ownership | Basic operational concepts; nomination does not always determine legal ownership |
| 69 | Protecting Investment Accounts and Financial Data | OTP safety, phishing, account security, and recovery practices |
| 70 | Investor Grievances and Official Complaint Channels | Appropriate official escalation channels and record keeping |

### G. Worked examples and FAQs (10)

Especially valuable for RAG — they let the agent answer numerical/conceptual questions from explicit, reviewed examples rather than improvising calculations.

| # | Title | What the agent should explain |
|---|---|---|
| 71 | Compound Interest: A Worked Example | Principal, rate, time, compounding frequency, and assumptions |
| 72 | Monthly Investing: A Worked Example | How recurring contributions accumulate under an assumed return |
| 73 | Inflation: What Will Today's Money Be Worth Later? | Future purchasing power under an assumed inflation rate |
| 74 | How Fees Change Long-Term Investment Outcomes | Comparing otherwise equivalent hypothetical investments with different costs |
| 75 | Diversification: A Worked Portfolio Example | Concentration versus spreading exposure, including limitations |
| 76 | Understanding CAGR With a Worked Example | Beginning value, ending value, and elapsed time |
| 77 | Understanding XIRR With Irregular Cash Flows | Why the timing of contributions and withdrawals matters |
| 78 | How a Bond's Price Can Change Before Maturity | An illustrative rate-change scenario and market-value risk |
| 79 | How a Portfolio Loss Affects Recovery | Percentage losses and the gains required to recover |
| 80 | Investment Myths: Questions and Evidence-Based Answers | Common misconceptions, evidence, caveats, and source-backed corrections |

---

## 3. Trusted Sources

Prioritize primary regulators, official product documents, and established educational references — avoid random blogs as the primary authority for financial claims.

| Source | Best for | Link |
|---|---|---|
| **SEBI** (market education & investor protection) | Mutual funds, equities, intermediaries, market risks, fraud prevention, investor rights | Official SEBI site / SEBI Investor website |
| **RBI** (banking & fixed income) | Banking, deposits, government securities, monetary policy, financial-system concepts | Official RBI site |
| **AMFI** (mutual fund education) | Fund terminology, NAV, SIPs, expense ratios, mutual fund basics — cross-check regulatory claims against SEBI | Official AMFI site |
| **NSE India** (market mechanics) | Stock market terminology, indices, trading mechanics, investor education | Official NSE site |
| **Income Tax Department** (taxation) | Capital gains, dividends, exemptions, tax calculations — use current official guidance/legislation | Income Tax e-Filing portal |
| **Investor.gov** (universal fundamentals) | Diversification, compound interest, fees, risk, investor behaviour — supplementary; clearly label US-specific rules/examples | Investor.gov education resources |

Also consider **PFRDA** for NPS/pensions and **DICGC** for deposit insurance.

---

## 4. Article Format

Every article is a structured, reviewed knowledge document — not a copied web page. Reusable template: [`article-template.md`](article-template.md).

---

## 5. Retrieval Metadata Schema

Every article carries this metadata so the retriever can filter by jurisdiction/freshness, not just semantic similarity:

| Field | Purpose |
|---|---|
| `article_id` | Stable identifier for citations and updates |
| `title` | Human-readable article title |
| `topic` | One of the 7 categories above (A–G) |
| `summary` | Short description for retrieval and navigation |
| `content` | Reviewed article body |
| `source_urls` | Primary source links supporting the claims |
| `claim_sources` | Which sources support specific material claims (see note below) |
| `jurisdiction` | `india`, `global`, or another applicable jurisdiction |
| `risk_level` | `normal`, `high-impact`, or `time-sensitive` |
| `last_verified_at` | When the content and its claims were last checked |
| `review_due_at` | When the article needs another review |
| `version` | Content revision identifier |
| `related_articles` | Links to relevant concepts and prerequisites |

**Important:** an article-level citation isn't always sufficient. A page can contain several claims, and a single source might support only one of them — for high-impact claims (tax rates, regulatory limits), store the source at paragraph/claim level, not just once per article.

---

## 6. Agent Guardrails

These should be encoded directly in the Finance Q&A and Tax Education agents' system prompts (see their respective docs):

- **Grounded answers** — answer from retrieved, approved sources; cite the supporting article/source for every substantive claim
- **No invented facts** — if the knowledge base lacks sufficient evidence, say so and identify what's missing
- **Education, not recommendations** — explain products, trade-offs, calculations, and risks without telling the user what to buy or sell
- **No account-specific decisions** — route portfolio/goal questions to the relevant agent (Portfolio Analysis / Goal Planning), which stay descriptive, not prescriptive, themselves
- **Freshness awareness** — revalidate tax rules, regulatory requirements, fee schedules, and product-specific details more often than stable concepts (`risk_level: time-sensitive` + `review_due_at` exist for exactly this)
- **Transparent examples** — label hypothetical returns, assumptions, time periods, and exclusions; never imply an illustrative calculation predicts actual outcomes
- **Conflict handling** — if sources disagree, prefer the applicable authoritative source, surface the disagreement, don't silently blend conflicting claims

---

## 6b. Status after the 2026-11-17 expansion: 51 of 80 articles

The starter set below (15) was extended with **36 more articles** covering the remaining product, cost, tax, behaviour, safety and worked-example topics, plus a **93-term glossary** (it was 4). Topics now: foundations 7 · growth-portfolio 7 · products 13 · costs-taxes 9 · behaviour-risk 7 · safety-regulation 6 · worked-examples 2 (counts include the older set; run `ls docs/knowledge-base/articles` for the truth).

**How they were checked (honest account).** Each article's *Source References* and *Review Metadata* say exactly what was read. In this pass the following were **fetched and read as page or PDF text**: SEBI's Financial Education Booklet (2020) and Beginner's Guide, the BSE and AMFI investor booklets (AMFI's carries the SEBI Master Circular of 20 March 2026), the DICGC FAQ page (read in full), SEBI's caution-to-investors page, the SCORES portal, SEBI's credit-rating FAQ (March 2026), the RBI complaint portal home page, and the SEC's behaviour, margin and asset-allocation pages. **Read only as search summaries** (the site blocked automated reading or the page did not render): the Income Tax Department pages (dividend TDS, penalties, anti-avoidance), RBI Retail Direct, the NSI PPF page, EPFO's FAQ, the newer PFRDA exit rule, SEBI's gold-exchange FAQ, SMART ODR and IRDAI's Bima Bharosa. Those claims are labelled as such inside each article. Figures were computed in code for every worked example. **No qualified human has reviewed any of it.**

**Rules enforced by `tests/kb/knowledge_base_test.py`** (offline, instant): complete and valid front matter, the same sections in every article, a note on how sources were checked, no "you should buy/sell" wording, time-sensitive articles must say to verify and may quote no figures outside their worked example, every `related_articles` id exists, at least 50 articles, every article has a retrieval question, glossary entries complete and unambiguous. It found real problems on its first run: a colon in a title that made the YAML invalid, a placeholder link, and two older articles with no linkable source.

**Retrieval measured live (embedding model gemini-embedding-2, threshold 0.66):** 102 in-knowledge-base questions, expected article in the top 3 for **102 of 102** and ranked first for 96; lowest in-KB score 0.718; highest off-topic score 0.652. Price questions ("Sensex close today") score 0.687 against the new index article, above the threshold, but they never reach retrieval: the router sends them to the Market agent, which `tests/kb` proves offline. Before the expansion the gap was +0.119 (0.739 vs 0.620); it is now +0.066, so adding content narrows it. Watch it as the knowledge base grows.

## 7. Build-First Set — Drafted

Don't curate all 80 before testing the agent. This starter set is now **drafted** (AI-written, unverified — see each file's Review Metadata) under [`articles/`](articles/), mapped back to the full list above for traceability:

| Starter topic | Maps to # | Article |
|---|---|---|
| Compound interest | 7, 71 | [`articles/compound-interest.md`](articles/compound-interest.md) |
| Inflation | 8, 73 | [`articles/inflation-and-purchasing-power.md`](articles/inflation-and-purchasing-power.md) |
| Nominal vs. real returns | 9 | [`articles/nominal-vs-real-returns.md`](articles/nominal-vs-real-returns.md) |
| Diversification and correlation | 16, 17 | [`articles/diversification-and-correlation.md`](articles/diversification-and-correlation.md) |
| Risk vs. return | 4 | [`articles/risk-vs-return.md`](articles/risk-vs-return.md) |
| Asset allocation | 18 | [`articles/asset-allocation.md`](articles/asset-allocation.md) |
| CAGR vs. XIRR | 23, 76, 77 | [`articles/cagr-vs-xirr.md`](articles/cagr-vs-xirr.md) |
| Mutual funds and ETFs | 34, 36 | [`articles/mutual-funds-and-etfs.md`](articles/mutual-funds-and-etfs.md) |
| Expense ratios and fees | 41, 42 | [`articles/expense-ratios-and-fees.md`](articles/expense-ratios-and-fees.md) |
| Bonds and interest-rate risk | 29, 30 | [`articles/bonds-and-interest-rate-risk.md`](articles/bonds-and-interest-rate-risk.md) |
| SIPs and periodic investing | 14, 38 | [`articles/sips-and-periodic-investing.md`](articles/sips-and-periodic-investing.md) |
| Capital gains tax basics in India | 46 | [`articles/capital-gains-tax-basics-india.md`](articles/capital-gains-tax-basics-india.md) ⚠️ `time-sensitive` |
| Investor scams and unrealistic return promises | 61 | [`articles/investor-scams-and-unrealistic-returns.md`](articles/investor-scams-and-unrealistic-returns.md) |
| How to read a mutual fund factsheet | 65 | [`articles/reading-a-mutual-fund-factsheet.md`](articles/reading-a-mutual-fund-factsheet.md) |
| How to compare investment products fairly | 52 | [`articles/comparing-investment-products-fairly.md`](articles/comparing-investment-products-fairly.md) |

> Reconciled to 15 by counting "compound interest" and "inflation" as two separate articles rather than one combined bullet.

**Verification status (2026-10-22, second pass):** a first pass cited sources found via web search but mostly relied on the search tool's own compressed summaries rather than the actual page text. This second pass directly fetched every cited URL to check that. Results:

- **Fully fetch-confirmed and content directly extracted:** AMFI's investor education PDF booklet (downloaded and parsed page-by-page with `pypdf` — not just a web-rendered page; this materially upgraded `compound-interest.md`, `expense-ratios-and-fees.md`, `sips-and-periodic-investing.md`, `mutual-funds-and-etfs.md`, and `risk-vs-return.md` with real worked examples, formulas, and quotes instead of invented illustrative ones); RBI's government securities FAQ (`bonds-and-interest-rate-risk.md`); SEC's asset-allocation guide on sec.gov (`asset-allocation.md`, `diversification-and-correlation.md`); Zerodha Varsity's mutual-fund-returns chapter (`cagr-vs-xirr.md`); SEBI's investor caution page (`investor-scams-and-unrealistic-returns.md`).
- **Blocked at the platform level, not just skipped:** every `investor.gov` URL cited (compound interest, purchasing power, risk, asset allocation, bonds, Ponzi alert) returns **HTTP 403** to automated fetches — this is a site-wide bot-blocking behavior, confirmed by hitting it from multiple different pages. Those citations now explicitly say "not independently fetch-confirmed, resting on a search-engine snippet" rather than implying they were verified. `incometaxindia.gov.in` behaves the same way (403).
- **Timed out, not yet resolved:** the NSE ETF structure page (`mutual-funds-and-etfs.md`) — two attempts both exceeded the fetch timeout; flagged as lower-confidence in that file.
- **Confirmed via secondary sources only, not a primary regulator:** `cagr-vs-xirr.md` (Zerodha Varsity, not AMFI/SEBI) and the SEBI riskometer circular numbers in `reading-a-mutual-fund-factsheet.md` (industry blogs citing the circular, not a direct sebi.gov.in fetch) — both explicitly flagged in their own files.
- `capital-gains-tax-basics-india.md` still deliberately states no specific rates/thresholds, independent of fetch status, since those change with each Union Budget — the 403 block is a secondary issue here, not the main reason.

This is still **AI-assisted verification, not qualified human review** — every article's Review Metadata is specific about exactly what was fetched-and-read versus search-snippet-only versus blocked. Use this set to test retrieval accuracy, citation quality, and refusal behavior — then expand toward the full 80 based on the gaps those tests reveal.

---

**Overall recommendation:** aim for 50–100 authoritative, focused articles, each with traceable claims, explicit jurisdiction, and review dates. A smaller, well-maintained corpus beats a much larger collection of loosely sourced material.
