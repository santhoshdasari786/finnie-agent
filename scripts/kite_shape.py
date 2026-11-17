"""Print the SHAPE of Kite MCP responses (key names and types), never the values.

Run:  .venv/bin/python -m scripts.kite_shape
Kite's MCP server now uses OAuth: the first connection prints a login link; you open it, log in to Zerodha and
approve. This script then checks which tools exist and what their replies look like (types only), so
KiteSource can be written against the truth instead of assumptions. Nothing from your account is printed.
"""
import asyncio
import json
import re

from fastmcp import Client
from fastmcp.client.auth import OAuth

URL = "https://mcp.kite.trade/mcp"


class PrintLinkOAuth(OAuth):
    """Same OAuth flow, but PRINT the authorization link instead of opening a browser by itself."""

    async def redirect_handler(self, authorization_url: str) -> None:
        print("\n>>> Open this link, log in to Zerodha and approve:\n    " + authorization_url + "\n", flush=True)


def shape(x, depth=0):
    """'dict{a:str, b:int}' / 'list[3] of dict{...}' -- types only."""
    if isinstance(x, dict):
        inner = ", ".join(f"{k}:{shape(v, depth + 1) if depth < 2 else type(v).__name__}" for k, v in x.items())
        return "dict{" + inner + "}"
    if isinstance(x, list):
        return f"list[{len(x)}]" + (f" of {shape(x[0], depth + 1)}" if x else "")
    return type(x).__name__


def parsed(result):
    """Prefer plain JSON: structured_content (dict) -> JSON text -> .data if it is already a dict/list -> raw text."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, (dict, list)):
        return structured
    text = "".join(getattr(c, "text", "") for c in (getattr(result, "content", None) or []))
    try:
        return json.loads(text)
    except ValueError:
        pass
    data = getattr(result, "data", None)
    return data if isinstance(data, (dict, list)) else (text or repr(type(data).__name__))


async def probe(client, tool, args=None):
    try:
        out = parsed(await asyncio.wait_for(client.call_tool(tool, args or {}), 30))
    except Exception as e:
        print(f"  {tool}: RAISED {type(e).__name__}: {str(e)[:160]!r}")
        return None
    if isinstance(out, str):
        # error-like replies are shown as-is; anything longer is masked (it might hold account data)
        short_notice = len(out) < 200 and re.search(r"session|login|log in|expired|authenticat", out, re.I)
        shown = out[:200] if short_notice else re.sub(r"[A-Za-z0-9]", "x", out[:80])
        print(f"  {tool}: TEXT ({len(out)} chars): {shown!r}")
    else:
        print(f"  {tool}: {shape(out)}")
    return out


async def main():
    print("Connecting (OAuth). If a login link is printed, open it and approve; this waits up to 5 minutes...")
    async with Client(URL, auth=PrintLinkOAuth(client_name="Finnie capstone (read-only)")) as client:
        print("Connected.\n")
        print("replies (types only; holdings limited to 1 row):")
        # (tool, arguments): the ONLY three calls the app will ever make. No orders / gtt / alerts / logout.
        for tool, args in (("session", {"mode": "status"}),
                           ("portfolio", {"mode": "holdings", "type": "full", "limit": 1}),
                           ("mutual_funds", {"mode": "holdings"})):
            print(f"{tool} {args}")
            await probe(client, tool, args)


if __name__ == "__main__":
    asyncio.run(main())
