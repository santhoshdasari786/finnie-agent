import asyncio
from dotenv import load_dotenv; load_dotenv(".env")
from src.agents.finance_qa_agent import FinanceQAAgent
from src.common.models import QASettings
from src.core.guardrails import Guardrails
from src.workflow.graph import ask, build_graph
from src.workflow.state import AGENT_NAMES
from tests.conftest import StubAgent

async def main():
    s = QASettings()
    agents = {n: StubAgent(n) for n in AGENT_NAMES}
    agents["finance_qa"] = FinanceQAAgent()          # the only real one
    app = build_graph(agents, Guardrails(s), s)
    for q in ["What is a SIP?", "I can't pay my credit card EMI. What is a SIP?", "I want to die", "Nifty close today"]:
        r = await ask(app, q)
        print(f"\n> {q}\n[{r.agent} / {r.status}] {r.text[:200]}")

asyncio.run(main())
