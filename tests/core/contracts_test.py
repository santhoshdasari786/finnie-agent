"""Shared contracts: the rejections matter more than the happy path.

Run:  .venv/bin/python -m pytest tests/core/contracts_test.py -v
"""
import pytest
from pydantic import ValidationError

from src.core.contracts import Agent, AgentContext, AgentResult, UserProfile

def make(**over):
    base = dict(agent="finance_qa", status="ok", text="An answer.", disclaimer="Not advice.")
    return AgentResult(**{**base, **over})


# ---------------------------------------------------------------- AgentResult
def test_minimal_result_has_empty_defaults():
    r = make()
    assert r.citations == [] and r.data is None and r.meta == {}

@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_blank_text_is_rejected(blank):
    with pytest.raises(ValidationError):
        make(text=blank)

@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_disclaimer_is_rejected(blank):
    with pytest.raises(ValidationError):
        make(disclaimer=blank)

@pytest.mark.parametrize("data", [None, {}, {"login_url": ""}, {"other": 1}])
def test_needs_login_without_a_url_is_rejected(data):
    with pytest.raises(ValidationError):
        make(status="needs_login", data=data)

def test_needs_login_with_a_url_is_accepted():
    r = make(status="needs_login", data={"login_url": "https://kite.example/login"})
    assert r.status == "needs_login"

def test_unknown_status_is_rejected():
    with pytest.raises(ValidationError):
        make(status="maybe")

def test_defaults_are_not_shared_between_instances():
    a, b = make(), make()
    a.meta["x"] = 1
    a.citations.append("c")
    assert b.meta == {} and b.citations == []


# ---------------------------------------------------------------- UserProfile
def test_profile_defaults():
    p = UserProfile()
    assert p.risk_appetite is None and p.risk_source is None
    assert p.knowledge_level == "beginner" and p.jurisdiction == "india" and p.goals == []

def test_profile_rejects_an_unknown_risk_bucket():
    with pytest.raises(ValidationError):
        UserProfile(risk_appetite="yolo")

def test_profile_goals_are_not_shared():
    a, b = UserProfile(), UserProfile()
    a.goals.append("house")
    assert b.goals == []


# ---------------------------------------------------------------- AgentContext
def test_context_defaults():
    c = AgentContext(thread_id="t1")
    assert c.flags == frozenset() and c.history == [] and c.category_hint is None
    assert c.profile.knowledge_level == "beginner"

def test_context_requires_a_thread_id():
    with pytest.raises(ValidationError):
        AgentContext()

def test_context_flags_are_a_frozenset():
    c = AgentContext(thread_id="t", flags={"advice_seeking"})
    assert isinstance(c.flags, frozenset) and "advice_seeking" in c.flags


# ---------------------------------------------------------------- Agent protocol
def test_a_plain_class_satisfies_the_agent_protocol():
    class Dummy:
        name = "dummy"
        async def run(self, query, ctx=None):
            return make()
    assert isinstance(Dummy(), Agent)

def test_a_class_without_run_does_not():
    class NoRun:
        name = "x"
    assert not isinstance(NoRun(), Agent)
