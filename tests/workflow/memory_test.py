"""Conversation memory: follow-up detection, the per-thread store, the rewriter, and the graph wiring.

Run:  .venv/bin/python -m pytest tests/workflow/memory_test.py -v
No LLM, no network: the rewriter is a fake that records what it was asked.

The idea: "and how is it taxed?" cannot be routed or answered alone. Memory turns it into a standalone
question ("How is ELSS taxed?") using the thread's recent turns, BEFORE routing. Safety is unchanged:
the guard still reads the user's raw words.
"""
import pytest

from src.common.models import QASettings
from src.core.contracts import AgentResult, Turn
from src.core.guardrails import Guardrails
from src.workflow.graph import ask, build_graph
from src.workflow.memory import ConversationMemory, LLMRewriter, looks_like_followup

from tests.conftest import FakeLLM, StubAgent

pytestmark = pytest.mark.asyncio


class FakeRewriter:
    def __init__(self, reply="How is ELSS taxed?"):
        self.reply, self.calls, self.error = reply, [], None

    async def rewrite(self, text, history):
        self.calls.append((text, list(history)))
        if self.error:
            raise self.error
        return self.reply


def result(text="An answer.", status="ok", agent="finance_qa"):
    return AgentResult(agent=agent, status=status, text=text, disclaimer="d")


# ================================================================ looks_like_followup
@pytest.mark.parametrize("text", [
    "and for TCS?", "And what about gold", "What about ELSS?", "how about the Nifty",
    "How is it taxed?", "Explain that more", "why does this matter for me", "Tell me more about those",
    "Why?", "Really?", "ok so what next", "then?",
])
async def test_these_look_like_follow_ups(text):
    assert looks_like_followup(text)

@pytest.mark.parametrize("text", [
    "What is a SIP?", "connect kite", "disconnect kite", "analyze my portfolio", "Nifty close today",
    "Can I retire at 50?", "latest news on Infosys", "How are capital gains taxed?", "Hello",
])
async def test_these_stand_alone(text):
    assert not looks_like_followup(text)

async def test_a_long_message_with_a_pronoun_is_left_alone():
    long = "I have been investing for ten years across several funds and I wonder whether it is wise to keep going"
    assert not looks_like_followup(long)


# ================================================================ the store
async def test_unknown_thread_has_no_history():
    assert ConversationMemory().history("nobody") == []

async def test_remember_stores_the_question_then_the_answer_in_order():
    m = ConversationMemory()
    m.remember("t", "What is ELSS?", result("ELSS is a tax-saving fund [1]."))
    assert m.history("t") == [Turn(role="user", text="What is ELSS?"),
                              Turn(role="assistant", text="ELSS is a tax-saving fund [1].")]

async def test_threads_do_not_see_each_other():
    m = ConversationMemory()
    m.remember("a", "q", result("x"))
    assert m.history("b") == []

async def test_only_the_newest_turns_are_kept():
    m = ConversationMemory(max_turns=4)
    for i in range(5):
        m.remember("t", f"q{i}", result(f"a{i}"))
    assert [t.text for t in m.history("t")] == ["q3", "a3", "q4", "a4"]

async def test_long_texts_are_cut():
    m = ConversationMemory(max_chars=20)
    m.remember("t", "q" * 100, result("a" * 100))
    assert all(len(t.text) <= 20 for t in m.history("t"))

async def test_history_returns_a_copy():
    m = ConversationMemory()
    m.remember("t", "q", result())
    m.history("t").clear()
    assert len(m.history("t")) == 2

@pytest.mark.parametrize("status", ["error", "redirect", "needs_login"])
async def test_failed_or_blocked_answers_are_not_remembered(status):
    m = ConversationMemory()
    data = {"login_url": "https://x"} if status == "needs_login" else None
    r = AgentResult(agent="a", status=status, text="t", disclaimer="d", data=data)
    m.remember("t", "q", r)
    assert m.history("t") == []

@pytest.mark.parametrize("status", ["ok", "clarify", "no_source"])
async def test_ok_clarify_and_no_source_are_remembered(status):
    m = ConversationMemory()
    m.remember("t", "q", result(status=status))
    assert len(m.history("t")) == 2

async def test_clear_forgets_one_thread_only():
    m = ConversationMemory()
    m.remember("a", "q", result()); m.remember("b", "q", result())
    m.clear("a")
    assert m.history("a") == [] and len(m.history("b")) == 2


# ================================================================ standalone()
def seeded(rewriter, **kw):
    m = ConversationMemory(rewriter=rewriter, **kw)
    m.remember("t", "What is ELSS?", result("ELSS is a tax-saving fund."))
    return m

async def test_follow_up_with_history_is_rewritten():
    rw = FakeRewriter("How is ELSS taxed?")
    out = await seeded(rw).standalone("t", "and how is it taxed?")
    assert out == "How is ELSS taxed?"
    text, hist = rw.calls[0]
    assert text == "and how is it taxed?" and hist[0].text == "What is ELSS?"

async def test_no_history_means_no_rewrite():
    rw = FakeRewriter()
    assert await ConversationMemory(rewriter=rw).standalone("t", "and how is it taxed?") == "and how is it taxed?"
    assert rw.calls == []

async def test_a_standalone_question_is_never_sent_to_the_rewriter():
    rw = FakeRewriter()
    assert await seeded(rw).standalone("t", "What is a SIP?") == "What is a SIP?"
    assert rw.calls == []

async def test_without_a_rewriter_the_text_is_unchanged():
    assert await seeded(None).standalone("t", "and how is it taxed?") == "and how is it taxed?"

@pytest.mark.parametrize("bad", ["", "   ", "x" * 301, "line one\nline two"])
async def test_a_bad_rewrite_falls_back_to_the_original(bad):
    assert await seeded(FakeRewriter(bad)).standalone("t", "and how is it taxed?") == "and how is it taxed?"

async def test_a_rewriter_failure_never_blocks_the_question():
    rw = FakeRewriter(); rw.error = RuntimeError("llm down")
    assert await seeded(rw).standalone("t", "and how is it taxed?") == "and how is it taxed?"


# ================================================================ LLMRewriter
async def test_llm_rewriter_returns_the_models_question():
    llm = FakeLLM("How is ELSS taxed?")
    out = await LLMRewriter(llm).rewrite("and how is it taxed?", [Turn(role="user", text="What is ELSS?")])
    assert out == "How is ELSS taxed?"

async def test_llm_rewriter_shows_the_model_the_history_and_the_message():
    llm = FakeLLM("x")
    hist = [Turn(role="user", text="What is ELSS?"), Turn(role="assistant", text="A tax-saving fund.")]
    await LLMRewriter(llm).rewrite("and how is it taxed?", hist)
    seen = llm.prompt_text()
    assert "What is ELSS?" in seen and "A tax-saving fund." in seen and "and how is it taxed?" in seen

async def test_llm_rewriter_tells_the_model_not_to_answer():
    llm = FakeLLM("x")
    await LLMRewriter(llm).rewrite("and for TCS?", [Turn(role="user", text="PE of Infosys?")])
    assert "do not answer" in llm.prompt_text().lower()

@pytest.mark.parametrize("raw, clean", [('"How is ELSS taxed?"', "How is ELSS taxed?"),
                                         ("  How is ELSS taxed?  \n", "How is ELSS taxed?")])
async def test_llm_rewriter_cleans_quotes_and_whitespace(raw, clean):
    assert await LLMRewriter(FakeLLM(raw)).rewrite("and?", [Turn(role="user", text="q")]) == clean


# ================================================================ wired into the graph
@pytest.fixture
def settings():
    return QASettings()

def make_app(stub_agents, settings, rewriter=None, memory=None):
    memory = memory or ConversationMemory(rewriter=rewriter or FakeRewriter())
    return build_graph(stub_agents, Guardrails(settings), settings, memory=memory), memory

async def test_a_follow_up_is_routed_and_answered_as_the_rewritten_question(stub_agents, settings):
    app, _ = make_app(stub_agents, settings, FakeRewriter("How is ELSS taxed?"))
    await ask(app, "What is ELSS?", thread_id="t")
    r = await ask(app, "and how is it taxed?", thread_id="t")
    assert r.agent == "tax_education"                                    # routed on the REWRITTEN text ("taxed")
    assert stub_agents["tax_education"].calls[0][0] == "How is ELSS taxed?"

async def test_the_agent_receives_the_history(stub_agents, settings):
    app, _ = make_app(stub_agents, settings)
    await ask(app, "What is ELSS?", thread_id="t")
    await ask(app, "and how is it taxed?", thread_id="t")
    _, ctx = stub_agents["tax_education"].calls[0]
    assert [t.text for t in ctx.history][0] == "What is ELSS?"

async def test_the_rewritten_question_is_what_gets_remembered(stub_agents, settings):
    app, memory = make_app(stub_agents, settings, FakeRewriter("How is ELSS taxed?"))
    await ask(app, "What is ELSS?", thread_id="t")
    await ask(app, "and how is it taxed?", thread_id="t")
    assert "How is ELSS taxed?" in [t.text for t in memory.history("t")]
    assert "and how is it taxed?" not in [t.text for t in memory.history("t")]

async def test_the_guard_reads_the_raw_words_before_any_rewrite(stub_agents, settings):
    rw = FakeRewriter()
    app, memory = make_app(stub_agents, settings, rw)
    await ask(app, "What is ELSS?", thread_id="t")
    r = await ask(app, "and I want to die", thread_id="t")
    assert r.agent == "guard" and rw.calls == []
    assert len(memory.history("t")) == 2                                 # the blocked message was not remembered

async def test_another_thread_has_no_history(stub_agents, settings):
    rw = FakeRewriter()
    app, _ = make_app(stub_agents, settings, rw)
    await ask(app, "What is ELSS?", thread_id="a")
    await ask(app, "and how is it taxed?", thread_id="b")
    assert rw.calls == []

async def test_commands_are_not_rewritten(stub_agents, settings):
    rw = FakeRewriter()
    app, _ = make_app(stub_agents, settings, rw)
    await ask(app, "What is ELSS?", thread_id="t")
    await ask(app, "connect kite", thread_id="t")
    assert rw.calls == [] and stub_agents["portfolio"].calls[0][0] == "connect kite"

async def test_an_agent_crash_is_not_remembered(stub_agents, settings):
    stub_agents["finance_qa"].raises = RuntimeError("boom")
    app, memory = make_app(stub_agents, settings)
    await ask(app, "What is ELSS?", thread_id="t")
    assert memory.history("t") == []

async def test_the_graph_still_works_without_memory(stub_agents, settings):
    app = build_graph(stub_agents, Guardrails(settings), settings)
    r = await ask(app, "What is a SIP?")
    assert r.agent == "finance_qa"

async def test_a_hint_still_overrides_after_a_rewrite(stub_agents, settings):
    app, _ = make_app(stub_agents, settings, FakeRewriter("How is ELSS taxed?"))
    await ask(app, "What is ELSS?", thread_id="t")
    r = await ask(app, "and how is it taxed?", thread_id="t", agent="finance_qa")
    assert r.agent == "finance_qa"


# ================================================================ real models return content PARTS, not a string
class PartsLLM:
    """Gemini-style reply: .content is a list of parts with extra metadata (found live 2026-11-13)."""
    def __init__(self, text):
        self.text = text

    async def ainvoke(self, messages, *a, **k):
        from langchain_core.messages import AIMessage
        return AIMessage(content=[{"type": "text", "text": self.text, "extras": {"signature": "abc123"}}])

async def test_llm_rewriter_reads_a_list_of_content_parts():
    out = await LLMRewriter(PartsLLM("How is a capital gain taxed?")).rewrite("how is it taxed?", [Turn(role="user", text="q")])
    assert out == "How is a capital gain taxed?"

async def test_the_rewritten_question_never_contains_provider_metadata():
    out = await LLMRewriter(PartsLLM("How is a capital gain taxed?")).rewrite("how is it taxed?", [Turn(role="user", text="q")])
    assert "signature" not in out and "extras" not in out and "{" not in out


# ================================================================ a successful rewrite leaves a log line
async def test_a_rewrite_is_logged(caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="src.workflow.memory"):
        await seeded(FakeRewriter("How is ELSS taxed?")).standalone("t", "and how is it taxed?")
    assert any("and how is it taxed?" in r.message and "How is ELSS taxed?" in r.message for r in caplog.records)

async def test_no_log_when_nothing_is_rewritten(caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="src.workflow.memory"):
        await seeded(FakeRewriter()).standalone("t", "What is a SIP?")
    assert not [r for r in caplog.records if "rewrite" in r.message.lower()]
