import logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("src.workflow.memory").setLevel(logging.INFO)
logging.getLogger("src.workflow.nodes").setLevel(logging.INFO)

import asyncio
from dotenv import load_dotenv; load_dotenv(".env")
from src.agents.finance_qa_agent import FinanceQAAgent

from src.workflow.bootstrap import build_app
from src.workflow.graph import ask
from src.workflow.state import AGENT_NAMES
from src.data.portfolio.store import ConnectionStore


HELP = ("Finnie. Ask anything; blank line or 'exit' quits.\n"
        f"  /agent <name> <question>   force an agent. Names: {', '.join(sorted(AGENT_NAMES))}")

def parse(line: str) -> tuple[str, str | None]:
    """'/agent tax_education What is 80C?' -> ('What is 80C?', 'tax_education')"""
    if line.startswith("/agent "):
        _, name, *rest = line.split(maxsplit=2)
        return (rest[0] if rest else ""), name
    return line, None

async def main():
    store = ConnectionStore()                  # kept here so live connections can be closed on exit
    app = build_app(store=store)
    print("Finance Q&A. Type a question; blank line or 'exit' quits.")
    try:
        while True:
            q = (await asyncio.to_thread(input, "\nask> ")).strip()
            if q.lower() in ("", "exit", "quit"):
                break
            text, agent = parse(q)
            try:
                res = await ask(app, text, thread_id="cli", agent=agent)
            except ValueError as e:
                print(f"\n{e}")
                continue
            print(f"\n[{res.agent}: {res.status}]\n{res.text}")
            if res.status == "needs_login" and res.data:
                print(f"\n  >>> {res.data['login_url']}")
            if res.citations:
                print("\ncitations:", *[f"\n  - {c.title}: {c.source}" for c in res.citations])
            print(f"\n{res.disclaimer}")
    finally:
        await store.close_all()                # closes the Kite connection and its localhost callback server


asyncio.run(main())
