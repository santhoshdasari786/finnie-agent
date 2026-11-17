# Web app (React)

**Status:** Implemented and verified (2026-11-17: tabs and charts added) · **Where:** `src/web_app/` · **Stack:** Vite, React 19, TypeScript (strict), Tailwind CSS 4, Vitest and Testing Library · **Tests:** 454 (plus 9 that run only against a live server)

A chat front end for the HTTP API in [`API.md`](API.md). It is a separate npm project; the Python image does not contain it (`.dockerignore`).

## Run it

```bash
cd src/web_app
npm install
npm run dev            # http://localhost:5173, expects the API on http://localhost:8000
npm test               # 454 tests, no server needed
npm run build          # type check + production build (about 82 KB of JavaScript, gzipped)
```

Start the API in another terminal: `.venv/bin/python -m uvicorn src.main:app --port 8000`. To point at a different API, copy `.env.example` to `.env` and set `VITE_API_URL`. The API already allows the `http://localhost:5173` origin (CORS).

## The four tabs

| Tab | What it shows | Where its data comes from |
|---|---|---|
| **Chat** | the conversation (everything below) | `POST /chat` |
| **Portfolio** | KPI tiles (diversification, risk profile, largest holding, holdings), an asset-class donut, a holdings bar list and the holdings table | the same conversation: its buttons send `connect sample` or `connect kite`, then `analyze my portfolio`, to the portfolio agent. The tab shows the newest analysis in the chat |
| **Market** | a closing-price line chart for 1M, 3M, 6M or 1Y, with latest price, change, high and low; six presets and a symbol box | `GET /market/history`, not the chat |
| **Goals** | a form (years, target, monthly saving, starting balance, risk appetite, return) and a projected-balance line chart with one line per scenario and the target as a dashed line | the form is turned into one sentence (`New goal: Can I reach 5000000 rupees in 10 years, ...`) and sent to the goal agent. Leave the years empty to ask "how long will it take" |

Portfolio and Goals are views over the **same conversation** as the Chat tab, so what you do there appears in the transcript, "New chat" clears all three, and a reload restores them. A tab is built the first time it is opened and then kept (hidden), so a form or a chart survives a visit to another tab. The charts are hand-written SVG (no chart library): `src/charts/` has `LineChart`, `DonutChart`, `BarList` and the pure geometry they share. Every chart has a text name that carries its numbers, for screen readers.

## What it does

| Feature | How |
|---|---|
| Chat | `POST /chat`; the server-chosen `thread_id` is kept per browser tab (`sessionStorage`) and the conversation is restored on reload (last 60 messages) |
| Which agent answered | a coloured badge per reply (Q&A, Tax, Portfolio, Market, Goals, News, Safety) |
| Sources | citation chips; only `http(s)` sources become links, opened with `rel="noopener noreferrer"` |
| Kite login | a `needs_login` reply shows an **Open Zerodha login** button and an **I've approved it** button that sends `connect kite` |
| Portfolio menu | the `clarify` reply's options become buttons that send `connect <source>` |
| Details panels | goal scenarios (three modes: projection, needed per month, time to reach), portfolio holdings with P&L, price quotes |
| Errors | a failed request shows an inline alert with **Try again**, unless retrying cannot help (a 4xx) |
| New chat | `DELETE /sessions/{id}`, then a clean slate; ignored while an answer is pending |
| Agent status | a dot per agent from `GET /agents` |
| Dark mode and phones | follows the system theme; checked at 390 px wide |

## Design decisions

- **Types mirror the API** (`src/api/types.ts`). A live contract test (`LIVE_API=http://localhost:8000 npm test -- live`) drives the real server through the real client, so drift between the two is caught.
- **Nothing is ever injected as HTML.** Replies are rendered by a small component that understands `**bold**`, `- ` lists and line breaks, and nothing else. A test feeds it `<script>` and `<img onerror>`.
- **Untrusted data is parsed defensively.** Panels check the shape of `data` and render nothing for anything malformed. Login links must be `http(s)`; portfolio option names must match `^[a-z0-9_]+$` before becoming a command.
- **Numbers use thousands grouping** (`₹5,000,000`) to match the assistant's own text. Indian lakh grouping everywhere is backlog U1.
- **The details panel follows the backend's own modes**: when the user gave no monthly amount it shows only "needed per month", never a projection of nothing.

## Known limits

- Replies arrive whole; there is no token streaming (backlog S1).
- On a very narrow phone the five-column goal table scrolls sideways inside its card.
- The Market chart has no hover tooltip yet; the numbers are in the chart's text name and the High / Low row.
- Quotes and history are not cached yet (backlog), so every tab visit with a new symbol asks Yahoo.
- The conversation is stored in the browser tab only; "New chat" in another tab is a separate conversation.
- No authentication (see `API.md`).
