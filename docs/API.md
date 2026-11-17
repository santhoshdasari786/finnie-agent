# HTTP API

**Status:** Implemented (2026-11-16) · **Files:** `src/api/` (`app.py`, `schemas.py`, `locks.py`), `src/workflow/runtime.py`, `src/main.py` · **Tests:** `tests/api/` (56)

Run it: `.venv/bin/python -m uvicorn src.main:app --reload --port 8000`, then open `http://localhost:8000/docs` for the generated OpenAPI page.

## Endpoints

| Method and path | Purpose |
|---|---|
| `POST /chat` | one message in, one `AgentResult` out. The whole graph (guard, memory, router, agent) runs behind it |
| `GET /agents` | the six agents and whether each is `ready` (for badges in the UI) |
| `DELETE /sessions/{thread_id}` | end a conversation: forget memory and pending questions, disconnect live portfolio sources. 204, also for an unknown id |
| `GET /health` | liveness |

### `POST /chat`

```json
// request                                       // response
{ "message": "can I retire at 50?",              { "thread_id": "9f2c…",  "agent": "goal_planning",
  "thread_id": "9f2c… (optional)",                 "status": "clarify",   "text": "So far I have: …",
  "agent": "tax_education (optional hint)" }       "citations": [{"source","title","excerpt","verified_at"}],
                                                   "data": {…} | null,    "meta": {"awaiting": "goal_planning", …},
                                                   "disclaimer": "…",     "login_url": null }
```

- **`thread_id`** is chosen by the server when missing and is always returned. The client keeps it for the whole conversation (a browser keeps one per tab). It must match `^[A-Za-z0-9_-]{8,64}$`.
- **`status`** is one of `ok`, `no_source`, `clarify`, `redirect`, `needs_login`, `error`. A blocked or failed message is still **HTTP 200**; only a malformed *request* is **422** (blank or over-2000-character message, bad `thread_id`, unknown `agent`).
- **`login_url`** is set only when `status` is `needs_login` (the Kite login link). The UI shows it as a button.
- **`meta`** exposes only `retryable`, `awaiting` and `missing`. The internal `learned` and `summary` never leave the server.
- An unexpected crash is **HTTP 500** `{"error": "Something went wrong on the server. Please try again."}`, with no stack trace. The cause is logged.

## Design

- **The graph is built once at startup**, not at import, so importing the module (and the tests) never loads models or the vector store. `create_app(runtime=..., build=...)` takes a ready `Runtime` (tests) or a `build` function (production: `bootstrap.build_runtime`).
- **One request at a time per session** (`ThreadLocks`). Memory and the Kite connection are per thread, and two interleaved requests on one thread would corrupt both. Different sessions run side by side. A lock is removed when nobody is using it.
- **CORS** allows the React dev server (`http://localhost:5173`, `http://127.0.0.1:5173`). Override with the `FINNIE_CORS_ORIGINS` environment variable (comma separated). No credentials are sent.
- **Shutdown** closes live broker connections (`Runtime.close` calls `ConnectionStore.close_all`).

## Known limits

- **No authentication and no rate limit.** Fine for a local demo; add both before exposing it. Anyone who guesses a `thread_id` shares that conversation.
- **Sessions are never evicted.** Memory grows with the number of threads until the process restarts (backlog M1, S3).
- **Not streaming.** A reply arrives whole, after the agent finishes (1 to 5 seconds on the live model). Token streaming needs each agent to stream; backlog S1.
- **The Kite login link only works on the machine running the server** (the OAuth callback is `localhost`), see backlog K4.
