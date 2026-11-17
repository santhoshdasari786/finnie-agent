import asyncio

from src.agents.finance_qa_agent import FinanceQAAgent

from tests.conftest import make_chunk, FakeLLM, FakeRetriever, FakeGlossary
from src.agents.finance_qa_agent import FinanceQAAgent
from dotenv import load_dotenv
load_dotenv()

a = FinanceQAAgent(llm=FakeLLM(), retriever=FakeRetriever(), glossary=FakeGlossary())

src = a._from_chunk(1, make_chunk())
print(src)                                          # check field order and values
print(a._build_user_prompt("What is a SIP?", [src], advice=False))   # read the exact prompt
print(a._build_user_prompt("Should I buy X?", [src], advice=True))   # note appears first


async def main():
    agent = FinanceQAAgent()
    await agent.ask("What is a SIP")

# asyncio.run(main())