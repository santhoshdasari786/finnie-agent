"""Workflow state and routing types.

Run:  .venv/bin/python -m pytest tests/workflow/state_test.py -v
"""
from typing import get_args, get_type_hints

import pytest
from pydantic import ValidationError

from src.workflow.state import (AGENT_NAMES, INTENT_TO_AGENT, AgentName, GraphState,
                                Intent, RoutingDecision)

def decision(**over):
    base = dict(intent="concept_qa", confidence=0.9, source="rules", normalized_question="What is a SIP?")
    return RoutingDecision(**{**base, **over})


# ---------------------------------------------------------------- intents and agents
def test_every_mapped_agent_is_a_valid_agent_name():
    assert set(INTENT_TO_AGENT.values()) <= AGENT_NAMES

def test_every_agent_is_reachable_from_some_intent():
    assert set(INTENT_TO_AGENT.values()) == AGENT_NAMES, "an agent exists that no intent routes to"

def test_only_the_self_handled_intents_have_no_agent():
    assert set(get_args(Intent)) - set(INTENT_TO_AGENT) == {"clarify", "off_topic", "profile"}

def test_every_mapped_intent_is_a_real_intent():
    assert set(INTENT_TO_AGENT) <= set(get_args(Intent))

def test_agent_names_come_from_the_literal():
    assert AGENT_NAMES == frozenset(get_args(AgentName))


# ---------------------------------------------------------------- RoutingDecision
def test_valid_decision_has_empty_defaults():
    d = decision()
    assert d.secondary_intents == [] and d.symbols == [] and d.clarification is None

@pytest.mark.parametrize("bad", [1.5, -0.1])
def test_confidence_out_of_range_is_rejected(bad):
    with pytest.raises(ValidationError):
        decision(confidence=bad)

@pytest.mark.parametrize("field,value", [("intent", "weather"), ("source", "magic"),
                                         ("secondary_intents", ["weather"])])
def test_unknown_literal_values_are_rejected(field, value):
    with pytest.raises(ValidationError):
        decision(**{field: value})

def test_decision_lists_are_not_shared():
    a, b = decision(), decision()
    a.symbols.append("TCS")
    assert b.symbols == []


# ---------------------------------------------------------------- GraphState
def test_graph_state_has_every_key_the_nodes_will_use():
    keys = set(get_type_hints(GraphState))
    assert {"text", "thread_id", "agent", "profile", "guard", "decision", "result"} <= keys, \
        f"missing: { {'text','thread_id','agent','profile','guard','decision','result'} - keys }"

def test_graph_state_keys_are_optional():
    assert GraphState.__total__ is False     # nodes return partial updates; keys may be absent
