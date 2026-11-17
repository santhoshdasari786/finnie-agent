"""QAResult -> AgentResult adapter.

Run:  .venv/bin/python -m pytest tests/common/interfaces_test.py -v
"""
from typing import get_args

import pytest

from src.common.interfaces import QAResult, _STATUS
from src.core.contracts import AgentResult
from src.rag.common.models import Citation

pytestmark = pytest.mark.asyncio

EXPECTED = {"rag": "ok", "glossary": "ok", "no_source": "no_source",
            "clarify": "clarify", "redirect": "redirect", "error": "error"}


@pytest.mark.parametrize("route,status", EXPECTED.items())
async def test_every_route_maps_to_the_expected_status(route, status):
    r = QAResult(answer="x", citations=[], route=route).to_result()
    assert isinstance(r, AgentResult)
    assert r.status == status
    assert r.meta["route"] == route
    assert r.agent == "finance_qa"


async def test_mapping_covers_every_route_in_the_literal():
    routes = set(get_args(QAResult.model_fields["route"].annotation))
    assert set(_STATUS) == routes, "a route was added without a status mapping"


async def test_citations_and_disclaimer_carry_over():
    c = Citation(source="https://example.org/a", title="A", excerpt="e")
    r = QAResult(answer="x", citations=[c], route="rag", disclaimer="Custom.").to_result()
    assert r.citations == [c]
    assert r.disclaimer == "Custom."


async def test_agent_name_can_be_overridden():
    assert QAResult(answer="x", citations=[], route="rag").to_result(agent="tax").agent == "tax"


async def test_blank_answer_is_not_silently_invented():
    # a blank LLM reply must surface as an error, not become made-up text
    with pytest.raises(Exception):
        QAResult(answer="  ", citations=[], route="rag").to_result()


async def test_real_agent_result_converts_cleanly(agent):
    r = (await agent.ask("What is a SIP?")).to_result()
    assert r.status == "ok" and r.agent == "finance_qa"
    assert r.text and r.disclaimer
    assert r.meta["route"] == "rag"


async def test_blocked_question_converts_to_redirect(agent):
    r = (await agent.ask("I want to die")).to_result()
    assert r.status == "redirect"
