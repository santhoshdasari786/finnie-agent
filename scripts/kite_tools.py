"""Print Kite MCP's tool DESCRIPTIONS and ARGUMENT SCHEMAS, plus the server's own help text.

Run:  .venv/bin/python -m scripts.kite_tools
This is published API metadata, not account data: it reads tool definitions and calls only `help`.
It never calls portfolio / orders / gtt / session. You log in once (OAuth) because the server hides tools until then.
"""
import asyncio
import json

from fastmcp import Client

from scripts.kite_shape import URL, PrintLinkOAuth, parsed


def args_of(tool) -> str:
    schema = getattr(tool, 'input_schema', None) or getattr(tool, 'inputSchema', None) or {}
    required = set(schema.get("required", []))
    lines = []
    for name, spec in (schema.get("properties") or {}).items():
        kind = spec.get("type") or ("|".join(t.get("type", "?") for t in spec.get("anyOf", [])) or "?")
        extra = f" enum={spec['enum']}" if "enum" in spec else ""
        desc = (spec.get("description") or "").replace("\n", " ")[:160]
        lines.append(f"      - {name}{' (required)' if name in required else ''}: {kind}{extra}  {desc}")
    return "\n".join(lines) or "      (no arguments)"


async def main():
    print("Connecting (OAuth). Open the link if one is printed; this waits up to 5 minutes...")
    async with Client(URL, auth=PrintLinkOAuth(client_name="Finnie capstone (read-only)")) as client:
        print("Connected.\n")
        for t in sorted(await client.list_tools(), key=lambda t: t.name):
            print(f"## {t.name}")
            print("   ", (t.description or "").replace("\n", " ")[:900])
            print("    arguments:")
            print(args_of(t))
            print()
        print("=" * 70, "\nserver help text (no arguments):")
        try:
            out = parsed(await asyncio.wait_for(client.call_tool("help", {}), 30))
            text = out if isinstance(out, str) else json.dumps(out, indent=1, default=str)
            print(text[:3500])
        except Exception as e:
            print(f"help RAISED {type(e).__name__}: {str(e)[:300]}")


if __name__ == "__main__":
    asyncio.run(main())
