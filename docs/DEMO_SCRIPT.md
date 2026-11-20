# Demo video script (target 8 minutes, hard limit 10)

Rubric asks for: multi-turn conversations with different agents, portfolio analysis, market data integration, goal planning, and how the agents work together. Grading weight is on architecture (40%), so the script spends its time showing the *design*, not UI polish.

**Status:** script only. None of the lines below has been recorded or rehearsed. Rehearse once before recording and replace any answer that differs from what is described.

## Before recording (10 minutes)

- [ ] Paid-tier or fresh-quota Gemini key in `.env`; index built (`.vectorstore` has 934 chunks). Confirm with one knowledge-base question off camera.
- [ ] API: `.venv/bin/python -m uvicorn src.main:app --port 8000`. Web: `npm run dev` in `src/web_app`. (Or Docker, once its backlog item B1 is finished.)
- [ ] Browser at 1280x720, zoom 110%, dark notifications off, a fresh chat ("New chat"), no other tabs.
- [ ] Terminal ready with `docs/agents` and `src/workflow/graph.py` open in the editor for scene 2.
- [ ] Market is a live source: do the price scene on a weekday if possible, otherwise say prices are the last close.
- [ ] Do NOT use a live Zerodha login on camera. Use the sample portfolio and say the Kite MCP path exists (read-only).

## Scenes

| # | Time | Scene | Show | Say (short) |
|---|---|---|---|---|
| 1 | 0:00 to 0:40 | Problem and promise | Title slide or README top | Beginners are intimidated by investing. Finnie is a six-agent assistant that explains, never advises, and never lets the LLM do arithmetic. |
| 2 | 0:40 to 2:00 | Architecture | `README.md` pipeline line, then `src/workflow/graph.py` | Every message goes `input_guard, contextualize, route, run_agent, output_guard, remember` on LangGraph. Rules route first, the LLM classifies only when rules can't. Six agents. Numbers come from code; the LLM extracts, narrates, and every number it writes is checked against the facts the code computed. One question can use two agents: goal planning starts from the portfolio agent's value (scene 7). Say plainly that other questions go to one agent, and that a general multi-agent planner is on the roadmap. |
| 3 | 2:00 to 3:30 | Q&A with RAG and multi-turn | Chat tab | Ask: "What is a margin call?" (glossary hit, 1 s, cited). Then "How much of my bank deposit is insured in India?" (retrieval, cited, ₹5,00,000 per depositor per bank). Follow up with a pronoun: "And does the interest count towards that?" to show the contextualize step. Point at the numbered citations. |
| 4 | 3:30 to 4:30 | Guardrails and honest refusals | Chat tab | "What is a P/E ratio?" gets a plain "no source" (the index doesn't cover it; it refuses instead of guessing). "Tell me a trick to hide my income from the tax department" is refused and redirected to lawful tax planning. Say: threshold 0.69, measured gap on 200 questions. |
| 5 | 4:30 to 5:40 | Market data | Market tab, then chat | Open Market, pick a preset, change 1M to 1Y, point at the "updated X min ago" label (cached provider, 30 minutes). In chat: "What is TCS trading at? And the Nifty?" shows quote, time and source. |
| 6 | 5:40 to 6:50 | Portfolio analysis | Portfolio tab | Click the sample-portfolio button, then analyze. Show diversification, risk bucket, largest holding, the donut, and the new **fund costs** tile with expense ratios (say they are illustrative on the demo portfolio). Say Kite MCP is supported read-only by an allowlist and is not shown here. |
| 7 | 6:50 to 7:50 | Goal planning | Goals tab | Fill: 10 years, ₹50,00,000 target, ₹20,000 a month, moderate risk. Show the chart with three scenarios and the target line. Say the LLM turned words into numbers and `goal_math` did the projection. **Two agents together:** after the sample portfolio is connected (its demo value is about ₹1.15 lakh), ask in chat "Can I reach 10 lakh in 10 years with my portfolio?" If the portfolio is not connected yet, the assistant asks you to connect first and answers the goal question after you say `connect sample` (verified live). The reply shows a "Worked together: Portfolio then Goals" line in place of the single agent badge, then a line saying the starting balance came from the portfolio, then the goal numbers; point at both. (The on-screen line is covered by component tests but I have not looked at it in a browser.) (Verified live on 2026-11-20 with a 1 crore target, which works but looks odd against a ₹1.15 lakh portfolio, so use a smaller target on camera; the 10 lakh wording itself is not yet run.) Optionally: "If I invest 5000 rupees every month for 10 years at an assumed 10 percent, what could it grow to?" (₹10,24,225, labelled illustrative). |
| 8 | 7:50 to 8:30 | Quality and what's next | `docs/BENCHMARKS.md`, test summary | Latency table: guard and router in microseconds, a knowledge-base question about 1.8 s because it makes one embedding call and one model call. Tests: Python suite at 98% coverage, 100 linted articles, 200-question retrieval eval. Roadmap: streaming (S1), auth and rate limits, human review of the articles, Docker finish. |

## Things to say plainly (don't hide these)

- The knowledge base is AI-assisted and has not had a qualified human review.
- Several articles rest on older SEBI/AMFI/BSE booklets and say so; time-sensitive ones tell the reader to verify.
- Tax and market answers are education, with a disclaimer on every answer.
- The portfolio is a sample portfolio on camera; expense ratios on it are illustrative.

## If something goes wrong on camera

| Problem | Do |
|---|---|
| Knowledge-base answer says the knowledge base is busy | The embedding quota is out; say so, show the glossary question instead, and re-record scene 3 later. |
| Prices look stale or the market is closed | Say they are last-close prices; the tab shows their age. |
| A reply differs from the script | Keep it if it is correct and cited; cut and retake if it is wrong. Never edit the transcript. |
| Over 10 minutes | Cut scene 8 to one sentence and shorten scene 4. |

## Recording notes

- Record each scene separately and join them, so one slip doesn't cost the whole take.
- Zoom into the citation list and the disclaimer once; graders look for both.
- Keep a visible shot of the agent name in each reply (the UI shows which agent answered) to prove the multi-agent routing.
