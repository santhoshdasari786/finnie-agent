# MCP Server

**Status:** Implemented and verified (2026-11-17) · **Files:** `src/mcp_server/server.py`, `src/mcp_server/__main__.py` · **Tests:** `tests/mcp_server/` (103), `scripts/mcp_check.py` (a live check) · **Rubric ties:** MCP Server (5%, bonus)

## Purpose and scope

Finnie as **tools for Claude Desktop** (or any MCP client). A thin adapter over the same runtime as the HTTP API (`Runtime`: the graph, the agents, the connection store and the memory), so every tool goes through the guards, the memory and the disclaimer. No finance logic lives here.

In scope: six read-only tools over **stdio**. Out of scope: trading, anything that writes, re-exposing Kite's raw tools.

This project is also an MCP *client* (the Portfolio agent talks to Kite's MCP server). This is the other direction.

## Tools

| Tool | Arguments | How it works |
|---|---|---|
| `ask_finance` | `question` (1 to 2000 chars), optional `thread_id` | the whole graph: guards, router, memory, any agent |
| `explain_term` | `term` (1 to 80) | "What is X?" to the Q&A agent |
| `get_quote` | `symbols` (1 to 10) | the Market agent. `^NSEI`, `NIFTY`, `NIFTY50` become "Nifty 50"; `^BSESN`, `SENSEX` become "Sensex"; any other `^` index is refused, because the agent supports only these two |
| `plan_goal` | `horizon_years` (0 to 60), then at least one of `target_amount`, `monthly_contribution`, `starting_balance`; optional `risk_appetite`, `annual_return_pct` (0 to 30) | the arguments are written as one sentence for the Goal agent, starting "New goal:" so numbers remembered from an earlier goal are not reused |
| `analyze_portfolio` | `source`: `sample` or `kite` | `connect <source>`, then `analyze my portfolio`. A connection that is not `ok` (for example `needs_login`) is returned as it is, with its link |
| `portfolio_login` | none | `connect kite`; returns the OAuth link |

Every tool returns the **same JSON as `POST /chat`** (`thread_id`, `agent`, `status`, `text`, `citations`, `data`, `meta`, `disclaimer`, `login_url`), so a disclaimer is always present. Every tool is annotated `readOnlyHint: true`.

**Not exposed, on purpose:** any order, GTT or raw Kite tool; `search_knowledge_base` (raw passages would skip the answer-level guards); `get_price_history` (the market provider has no history call yet).

## Conversations

stdio means **one server process is one client**, so one process is one default conversation (`mcp-<random>`). Follow-ups work across tools ("and how is it different from simple interest?"). A client that wants separate conversations passes `thread_id`. Calls within one conversation run one at a time; different `thread_id`s run side by side.

(`fastmcp` 4.1.1 gives a new `session_id` on every call, so it cannot identify a conversation. This was found by testing, not assumed.)

## Safety

- Read-only by construction, and checked: the tool list is an exact allowlist in the tests, and none of `place_order`, `modify_order`, `cancel_order`, `get_holdings`, `login`... can appear.
- Arguments are validated by the tool schema with limits (lengths, ranges, an enum for `source` and `risk_appetite`, a pattern for symbols and thread ids). A bad call is a clear `ToolError`, never a stack trace.
- A crash inside a tool becomes a generic `ToolError`; the cause goes to the log on stderr.
- **stdout belongs to the protocol.** Logs go to stderr, the start-up banner is off, and a test captures stdout during every tool call and requires it to be empty.

## Running it

```bash
.venv/bin/python -m src.mcp_server        # stdio; normally started by the client, not by hand
.venv/bin/python -m scripts.mcp_check     # starts it as a child process, calls every tool, reports
```

`mcp_check` starts the server with `cwd="/"`, because Claude Desktop does not start servers in your project folder. The server reads `.env` by absolute path and finds the vector store relative to the project, so no working directory and no API key in the client config are needed.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS; check the current Claude Desktop documentation for other systems) and add, with **absolute** paths:

```json
{
  "mcpServers": {
    "finnie": {
      "command": "/ABSOLUTE/PATH/ai_finance_assistant/.venv/bin/python",
      "args": ["-m", "src.mcp_server"],
      "env": { "PYTHONPATH": "/ABSOLUTE/PATH/ai_finance_assistant" }
    }
  }
}
```

Restart Claude Desktop. The first start takes a few seconds (the vector store and models load once, then every call is fast). Logs from the server appear in Claude Desktop's MCP log file.

## Design notes

- **The runtime is built once**, when the first client connects (`asyncio.to_thread`, so it does not block the event loop), and closed when the last one leaves. `fastmcp` enters the lifespan once and leaves it after the last client; an earlier counter of mine duplicated that and was removed.
- **No `print` anywhere on the path**, and the live check confirms nothing but JSON-RPC reaches stdout, even with the real vector store, models and market data loading.
- The tool functions are tiny; the work is the same graph the web app uses.

## Known limits

- Only **stdio** is supported; a network (HTTP) transport would need a per-client conversation id.
- The Kite login link works only on the machine running the server (the OAuth callback is `localhost`), which suits Claude Desktop on your own computer.
- `get_quote` supports two indexes and any stock ticker (the Market agent's own limit; backlog M3).
- Verified with a real stdio client (`mcp_check`). **Not yet verified inside Claude Desktop itself** (it must be tried by hand).

## Definition of Done

- [x] `python -m src.mcp_server` starts on stdio and lists exactly the six tools
- [x] `ask_finance` routes through the graph; every specific tool also goes through the guards
- [x] No trading or raw Kite tools exposed (tested)
- [x] Logs on stderr only; the stdout test passes; verified live over real stdio
- [x] `needs_login` returned with the link; one connection per conversation
- [x] In-memory client tests (103); `fastmcp` declared in `pyproject.toml`
- [ ] The Claude Desktop config tried end to end (manual)
