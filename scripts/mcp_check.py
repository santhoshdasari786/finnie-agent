"""Start the MCP server the way Claude Desktop does (a child process, stdio) and call every tool once.

Run:  .venv/bin/python -m scripts.mcp_check
Uses the real runtime: your API key, the vector store, Google News and yfinance. Takes about 30 seconds.
Passing means the protocol is clean (nothing but JSON-RPC on stdout) and each tool answers.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parents[1]

CALLS = [
    ("ask_finance", {"question": "What is compound interest?"}),
    ("explain_term", {"term": "expense ratio"}),
    ("get_quote", {"symbols": ["TCS", "NIFTY50"]}),
    ("plan_goal", {"horizon_years": 10, "target_amount": 5000000, "monthly_contribution": 20000}),
    ("analyze_portfolio", {"source": "sample"}),
    ("ask_finance", {"question": "I want to die"}),
]
EXPECTED_TOOLS = {"ask_finance", "explain_term", "get_quote", "plan_goal", "analyze_portfolio", "portfolio_login"}


async def main() -> int:
    # cwd="/" on purpose: Claude Desktop does not start the server in the project folder
    transport = StdioTransport(command=sys.executable, args=["-m", "src.mcp_server"], cwd="/",
                               env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"})
    failures = 0
    async with Client(transport, timeout=180) as client:
        print(f"connected to {client.server_info.name}")
        names = {t.name for t in await client.list_tools()}
        print("tools:", ", ".join(sorted(names)))
        if names != EXPECTED_TOOLS:
            print("  UNEXPECTED TOOL LIST:", sorted(names ^ EXPECTED_TOOLS))
            failures += 1
        for tool, args in CALLS:
            started = time.time()
            try:
                out = (await client.call_tool(tool, args)).data
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL {tool}: {e}")
                failures += 1
                continue
            first = out["text"].splitlines()[0][:100]
            print(f"  ok   {tool:18} {time.time() - started:4.1f}s [{out['agent']}: {out['status']}] {first}")
    print("\nAll good." if not failures else f"\n{failures} problem(s).")
    return failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
