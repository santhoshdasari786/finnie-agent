from src.core.contracts import Agent
from tests.conftest import StubAgent

import pytest



def test_there_is_one_stub_per_agent_name(stub_agents):
    from src.workflow.state import AGENT_NAMES
    assert set(stub_agents) == AGENT_NAMES

def test_stubs_satisfy_the_agent_protocol(stub_agents):
    assert all(isinstance(a, Agent) for a in stub_agents.values())

@pytest.mark.asyncio
async def test_stub_records_calls_and_returns_a_valid_result(stub_agents):
    a = stub_agents["finance_qa"]
    r = await a.run("hello", None)
    assert a.calls == [("hello", None)] and r.agent == "finance_qa" and r.status == "ok"

@pytest.mark.asyncio
async def test_stub_can_simulate_a_crash():
    a = StubAgent("portfolio")
    a.raises = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        await a.run("x")

@pytest.mark.asyncio
async def test_stub_can_return_needs_login():
    a = StubAgent("portfolio", status="needs_login", data={"login_url": "https://kite.example/login"})
    assert (await a.run("x")).status == "needs_login"
