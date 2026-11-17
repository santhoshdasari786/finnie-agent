"""HTTP API: POST /chat wraps the whole graph; GET /agents; DELETE /sessions/{id}; CORS; one request at a time per session.

Run:  .venv/bin/python -m pytest tests/api -v
No network, no LLM: the graph is built from stub agents.

Contract
  POST /chat   {message, thread_id?, agent?}  ->  {thread_id, agent, status, text, citations, data, meta, disclaimer, login_url}
  * thread_id is chosen by the server when missing and ALWAYS returned (the client keeps it for the conversation)
  * a blocked or failed message is still HTTP 200 (status redirect / error); only a malformed REQUEST is 422
  * `meta` exposes only retryable / awaiting / missing, never the internal learned / summary
  * an unexpected crash is HTTP 500 {"error": ...} with no stack trace
"""
import asyncio

import httpx
import pytest
from starlette.testclient import TestClient

from src.api.app import create_app
from src.workflow.runtime import Runtime
from src.common.models import QASettings
from src.core.contracts import AgentResult, Citation
from src.core.guardrails import Guardrails
from src.data.portfolio.store import ConnectionStore
from src.workflow.graph import build_graph
from src.workflow.memory import ConversationMemory
from src.workflow.state import AGENT_NAMES

from tests.conftest import StubAgent


class FakeStore(ConnectionStore):
    def __init__(self):
        super().__init__({})
        self.closed_all = 0
        self.disconnected: list[tuple[str, str]] = []
        self._fake_open: dict[str, list[str]] = {}

    def opened(self, thread_id):
        return list(self._fake_open.get(thread_id, []))

    def disconnect(self, thread_id, name):
        self.disconnected.append((thread_id, name))
        self._fake_open[thread_id] = [n for n in self._fake_open.get(thread_id, []) if n != name]
        return None

    async def close_all(self):
        self.closed_all += 1


def make_runtime(agents=None, store=None):
    agents = agents or {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    settings = QASettings()
    memory = ConversationMemory()
    graph = build_graph(agents, Guardrails(settings), settings, memory=memory)
    return Runtime(graph=graph, agents=agents, store=store or FakeStore(), memory=memory)


@pytest.fixture
def runtime():
    return make_runtime()

@pytest.fixture
def client(runtime):
    with TestClient(create_app(runtime=runtime)) as c:
        yield c

def chat(client, message="What is a SIP?", **kw):
    return client.post("/chat", json={"message": message, **kw})


# ================================================================ health and docs
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}

def test_the_openapi_description_lists_the_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/chat", "/agents", "/health", "/sessions/{thread_id}"} <= set(paths)


# ================================================================ the shape of a reply
def test_a_chat_reply_has_the_documented_fields(client):
    body = chat(client).json()
    assert set(body) == {"thread_id", "agent", "status", "text", "citations", "data", "meta", "disclaimer", "login_url"}
    assert body["agent"] == "finance_qa" and body["status"] == "ok" and body["text"] and body["disclaimer"]

def test_the_status_code_is_200(client):
    assert chat(client).status_code == 200

def test_a_thread_id_is_chosen_when_missing_and_returned(client):
    tid = chat(client).json()["thread_id"]
    assert len(tid) == 32 and tid.isalnum()

def test_two_new_conversations_get_different_ids(client):
    assert chat(client).json()["thread_id"] != chat(client).json()["thread_id"]

def test_a_given_thread_id_is_kept(client):
    assert chat(client, thread_id="my-session-0001").json()["thread_id"] == "my-session-0001"

def test_login_url_is_null_for_ordinary_answers(client):
    assert chat(client).json()["login_url"] is None


# ================================================================ the conversation continues on the same thread
def test_memory_continues_on_the_same_thread(client, runtime):
    chat(client, "What is a SIP?", thread_id="session-aaaa")
    chat(client, "What is a SIP?", thread_id="session-aaaa")
    _, ctx = runtime.agents["finance_qa"].calls[1]
    assert len(ctx.history) == 2

def test_another_thread_does_not_see_it(client, runtime):
    chat(client, "What is a SIP?", thread_id="session-aaaa")
    chat(client, "What is a SIP?", thread_id="session-bbbb")
    assert runtime.agents["finance_qa"].calls[1][1].history == []


# ================================================================ routing hint
def test_an_agent_hint_is_honoured(client):
    assert chat(client, agent="tax_education").json()["agent"] == "tax_education"

def test_an_unknown_agent_is_a_422_listing_the_options(client):
    r = chat(client, agent="made_up")
    assert r.status_code == 422 and "finance_qa" in r.text


# ================================================================ request validation
@pytest.mark.parametrize("message", ["", "   ", "\n\t"])
def test_a_blank_message_is_a_422(client, message):
    assert chat(client, message).status_code == 422

def test_a_missing_message_is_a_422(client):
    assert client.post("/chat", json={}).status_code == 422

def test_a_message_over_the_limit_is_a_422(client):
    assert chat(client, "x" * 2001).status_code == 422

def test_a_message_at_the_limit_is_accepted(client):
    assert chat(client, "x" * 2000).status_code == 200

@pytest.mark.parametrize("tid", ["short", "has space in it", "../../etc/passwd", "a" * 65, "semi;colon-0000", "émoji-session"])
def test_a_malformed_thread_id_is_a_422(client, tid):
    assert chat(client, thread_id=tid).status_code == 422

@pytest.mark.parametrize("tid", ["abcdefgh", "A1_b2-c3_d4", "a" * 64, "0123456789abcdef0123456789abcdef"])
def test_a_well_formed_thread_id_is_accepted(client, tid):
    assert chat(client, thread_id=tid).status_code == 200

def test_the_message_is_trimmed(client, runtime):
    chat(client, "   What is a SIP?   ")
    assert runtime.agents["finance_qa"].calls[0][0] == "What is a SIP?"


# ================================================================ blocked, failed and login results are still 200
def test_a_blocked_message_is_a_normal_reply(client):
    r = chat(client, "I want to die")
    assert r.status_code == 200 and r.json()["agent"] == "guard" and r.json()["status"] == "redirect"

def test_an_agent_crash_is_reported_in_the_body_not_as_an_http_error(runtime):
    runtime.agents["finance_qa"].raises = RuntimeError("secret internal detail")
    with TestClient(create_app(runtime=runtime)) as c:
        r = chat(c)
    assert r.status_code == 200 and r.json()["status"] == "error" and "secret" not in r.text

def test_a_login_link_is_lifted_to_the_top_level():
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents["portfolio"] = StubAgent("portfolio", status="needs_login", data={"login_url": "https://kite.example/login"})
    with TestClient(create_app(runtime=make_runtime(agents))) as c:
        body = chat(c, "Analyze my portfolio").json()
    assert body["status"] == "needs_login" and body["login_url"] == "https://kite.example/login"
    assert body["data"]["login_url"] == "https://kite.example/login"


# ================================================================ citations, data, meta
def test_citations_are_plain_json():
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents["finance_qa"].run = _with(citations=[Citation(source="https://x.org/a", title="A", excerpt="e", verified_at="2026-11-01")])
    with TestClient(create_app(runtime=make_runtime(agents))) as c:
        body = chat(c).json()
    assert body["citations"] == [{"source": "https://x.org/a", "title": "A", "excerpt": "e", "verified_at": "2026-11-01"}]

def test_structured_data_is_passed_through():
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents["goal_planning"] = StubAgent("goal_planning", data={"plan": {"years": 10, "scenarios": [{"name": "expected"}]}})
    with TestClient(create_app(runtime=make_runtime(agents))) as c:
        body = chat(c, "can I retire at 50?").json()
    assert body["data"]["plan"]["scenarios"][0]["name"] == "expected"

def test_only_safe_meta_is_exposed():
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents["goal_planning"] = StubAgent("goal_planning", status="clarify", meta={
        "awaiting": "goal_planning", "missing": ["horizon_years"], "retryable": False,
        "learned": {"slots": {"a": 1}}, "summary": "internal", "price_sources": ["x"]})
    with TestClient(create_app(runtime=make_runtime(agents))) as c:
        meta = chat(c, "can I retire at 50?").json()["meta"]
    assert meta == {"awaiting": "goal_planning", "missing": ["horizon_years"], "retryable": False}


def _with(**fields):
    async def run(query, ctx=None):
        return AgentResult(agent="finance_qa", status="ok", text="answer", disclaimer="d", **fields)
    return run


# ================================================================ an unexpected crash
def test_a_graph_crash_is_a_clean_500():
    rt = make_runtime()

    class Broken:
        async def ainvoke(self, *a, **k):
            raise RuntimeError("database password is hunter2")
    rt.graph = Broken()
    with TestClient(create_app(runtime=rt), raise_server_exceptions=False) as c:
        r = chat(c)
    assert r.status_code == 500 and r.json() == {"error": "Something went wrong on the server. Please try again."}
    assert "hunter2" not in r.text


# ================================================================ /agents
def test_agents_lists_all_six_with_readiness(client):
    body = client.get("/agents").json()
    assert [a["name"] for a in body] == sorted(AGENT_NAMES) and all(a["ready"] for a in body)

def test_a_placeholder_agent_is_not_ready():
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents["news_synthesizer"].ready = False
    with TestClient(create_app(runtime=make_runtime(agents))) as c:
        ready = {a["name"]: a["ready"] for a in c.get("/agents").json()}
    assert ready["news_synthesizer"] is False and ready["finance_qa"] is True

def test_a_missing_agent_is_listed_as_not_ready():
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES) if n != "news_synthesizer"}
    with TestClient(create_app(runtime=make_runtime(agents))) as c:
        ready = {a["name"]: a["ready"] for a in c.get("/agents").json()}
    assert ready["news_synthesizer"] is False


# ================================================================ ending a session
def test_deleting_a_session_forgets_the_conversation(client, runtime):
    chat(client, "What is a SIP?", thread_id="session-aaaa")
    assert client.delete("/sessions/session-aaaa").status_code == 204
    assert runtime.memory.history("session-aaaa") == []

def test_deleting_a_session_disconnects_its_sources():
    store = FakeStore()
    store._fake_open["session-aaaa"] = ["kite", "sample"]
    with TestClient(create_app(runtime=make_runtime(store=store))) as c:
        assert c.delete("/sessions/session-aaaa").status_code == 204
    assert sorted(store.disconnected) == [("session-aaaa", "kite"), ("session-aaaa", "sample")]

def test_deleting_an_unknown_session_is_fine(client):
    assert client.delete("/sessions/never-existed").status_code == 204

def test_deleting_with_a_malformed_id_is_a_422(client):
    assert client.delete("/sessions/short").status_code == 422

def test_other_sessions_survive_a_delete(client, runtime):
    chat(client, "What is a SIP?", thread_id="session-aaaa")
    chat(client, "What is a SIP?", thread_id="session-bbbb")
    client.delete("/sessions/session-aaaa")
    assert len(runtime.memory.history("session-bbbb")) == 2


# ================================================================ CORS for the React dev server
def test_the_react_dev_origin_is_allowed(client):
    r = client.options("/chat", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                                         "Access-Control-Request-Headers": "content-type"})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "http://localhost:5173"

def test_a_reply_carries_the_allow_origin_header(client):
    r = client.post("/chat", json={"message": "What is a SIP?"}, headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"

def test_an_unknown_origin_is_not_allowed(client):
    r = client.options("/chat", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers

def test_the_allowed_origins_are_configurable(runtime):
    with TestClient(create_app(runtime=runtime, cors_origins=["https://app.example"])) as c:
        ok = c.options("/chat", headers={"Origin": "https://app.example", "Access-Control-Request-Method": "POST"})
        no = c.options("/chat", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "https://app.example"
    assert "access-control-allow-origin" not in no.headers


# ================================================================ startup and shutdown
def test_the_runtime_is_built_at_startup_when_not_injected():
    built = []
    rt = make_runtime()

    def build():
        built.append(1)
        return rt
    with TestClient(create_app(build=build)) as c:
        assert chat(c).status_code == 200
    assert built == [1]

def test_the_runtime_is_not_built_at_import_time():
    built = []
    create_app(build=lambda: built.append(1) or make_runtime())
    assert built == []

def test_connections_are_closed_at_shutdown():
    store = FakeStore()
    with TestClient(create_app(runtime=make_runtime(store=store))):
        pass
    assert store.closed_all == 1


# ================================================================ one request at a time per session
class SlowAgent(StubAgent):
    active = 0
    peak = 0

    async def run(self, query, ctx=None):
        SlowAgent.active += 1
        SlowAgent.peak = max(SlowAgent.peak, SlowAgent.active)
        await asyncio.sleep(0.05)
        SlowAgent.active -= 1
        return await super().run(query, ctx)


async def _two(app, id_a, id_b):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        await asyncio.gather(c.post("/chat", json={"message": "What is a SIP?", "thread_id": id_a}),
                             c.post("/chat", json={"message": "What is a SIP?", "thread_id": id_b}))

@pytest.mark.asyncio
async def test_two_requests_on_one_session_run_one_after_the_other():
    SlowAgent.active = SlowAgent.peak = 0
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents["finance_qa"] = SlowAgent("finance_qa")
    await _two(create_app(runtime=make_runtime(agents)), "session-aaaa", "session-aaaa")
    assert SlowAgent.peak == 1

@pytest.mark.asyncio
async def test_different_sessions_run_side_by_side():
    SlowAgent.active = SlowAgent.peak = 0
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents["finance_qa"] = SlowAgent("finance_qa")
    await _two(create_app(runtime=make_runtime(agents)), "session-aaaa", "session-bbbb")
    assert SlowAgent.peak == 2

@pytest.mark.asyncio
async def test_the_per_session_locks_do_not_pile_up():
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    app = create_app(runtime=make_runtime(agents))
    await _two(app, "session-aaaa", "session-bbbb")
    assert app.state.locks.size() == 0


# ================================================================ two more guards
def test_a_login_link_is_only_lifted_for_a_login_result():
    agents = {n: StubAgent(n) for n in sorted(AGENT_NAMES)}
    agents["finance_qa"] = StubAgent("finance_qa", status="ok", data={"login_url": "https://not-a-login.example"})
    with TestClient(create_app(runtime=make_runtime(agents))) as c:
        assert chat(c).json()["login_url"] is None

def test_deleting_a_session_also_forgets_its_pending_portfolio_question():
    store = FakeStore()
    store.set_pending("session-aaaa", "how's the market treating me?")
    with TestClient(create_app(runtime=make_runtime(store=store))) as c:
        c.delete("/sessions/session-aaaa")
    assert store.take_pending("session-aaaa") is None
