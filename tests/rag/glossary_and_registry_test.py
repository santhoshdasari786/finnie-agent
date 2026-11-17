"""The glossary lookup, the way a question becomes a term, and the registry/factory that builds components from config.

Run:  .venv/bin/python -m pytest tests/rag/glossary_and_registry_test.py -v

Contract
  extract_candidate   "what is an ETF?" -> "etf"; longer than 5 words is a real question, not a term (None)
  YamlGlossary        exact term, alias, simple plural; two entries under one name = ambiguous; fuzzy only when enabled
  the real glossary   every term and every alias resolves back to its own entry (a typo in the YAML would break this)
  registry / build    a name can be registered once; an unknown kind or type lists what IS available
"""
from pathlib import Path

import pytest
import yaml

from src.rag.common import registry
from src.rag.common.factory import build
from src.rag.common.registry import register
from src.rag.glossary.matching import extract_candidate, normalize
from src.rag.glossary.yaml_glossary import YamlGlossary

ROOT = Path(__file__).resolve().parents[2]


# ================================================================ question -> term
@pytest.mark.parametrize("question, term", [
    ("What is an ETF?", "etf"),
    ("what is a SIP", "sip"),
    ("What are bonds?", "bonds"),
    ("What's the Sensex?", "sensex"),
    ("Whats NAV", "nav"),
    ("Define expense ratio", "expense ratio"),
    ("definition of compounding", "compounding"),
    ("Meaning of CAGR", "cagr"),
    ("Explain XIRR", "xirr"),
    ("tell me about margin call", "margin call"),
    ("What does NAV mean?", "nav"),
    ("what does expense ratio mean", "expense ratio"),
    ("  WHAT IS   A   Demat Account ?!  ", "demat account"),
    ("Sensex", "sensex"),
    ("What is T+1?", "t 1"),
    ("What is P&L?", "p&l"),
])
def test_a_question_becomes_a_term(question, term):
    assert extract_candidate(question) == term


@pytest.mark.parametrize("question", [
    "What is the difference between a mutual fund and an ETF",       # more than five words: a real question
    "How do I start a SIP",
    "", "   ", "?", "What is", "what is a"
])
def test_a_real_question_or_nothing_is_not_a_term(question):
    assert extract_candidate(question) is None


def test_five_words_is_the_longest_term():
    assert extract_candidate("one two three four five") == "one two three four five"
    assert extract_candidate("one two three four five six") is None


def test_normalize_lowercases_and_drops_punctuation_but_keeps_symbols_used_in_terms():
    assert normalize("  Hello,   World! ") == "hello world"
    assert normalize("P&L / 80C-3%") == "p&l / 80c-3%"


# ================================================================ the glossary
YAML = """
- term: Exchange-traded fund
  aliases: [ETF, ETFs]
  definition: A fund that trades on an exchange like a share.
  topic: products
  source_urls: ["https://example.org/etf"]
  related_articles: [mutual-funds-and-etfs]
- term: Expense ratio
  aliases: [TER]
  definition: The annual fee a fund charges.
- term: Bond
  sense: fixed income
  definition: A loan that pays interest.
- term: Bond
  sense: surety
  definition: A written promise to pay a penalty.
- term: Treasury bill
  aliases: [T-bill]
  definition: A short-term government security.
"""


@pytest.fixture
def glossary(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text(YAML, encoding="utf-8")
    return YamlGlossary(p)


def test_an_exact_term_matches_and_carries_its_fields(glossary):
    m = glossary.lookup("What is an expense ratio?")
    e = m.entries[0]
    assert m.match_type == "exact" and not m.ambiguous and m.matched_text == "expense ratio"
    assert e.definition == "The annual fee a fund charges." and e.aliases == ("TER",)


def test_an_alias_is_reported_as_an_alias(glossary):
    m = glossary.lookup("what is TER")
    assert m.match_type == "alias" and m.entries[0].term == "Expense ratio"


def test_every_field_of_an_entry_is_read(glossary):
    e = glossary.lookup("ETF").entries[0]
    assert (e.term, e.topic, e.source_urls, e.related_articles) == (
        "Exchange-traded fund", "products", ("https://example.org/etf",), ("mutual-funds-and-etfs",))


def test_a_simple_plural_finds_the_singular(glossary):
    assert glossary.lookup("What are expense ratios?").entries[0].term == "Expense ratio"
    assert glossary.lookup("what are T-bills").entries[0].term == "Treasury bill"


def test_matching_ignores_case_and_punctuation(glossary):
    assert glossary.lookup("TREASURY   BILL???").entries[0].term == "Treasury bill"


def test_two_entries_under_one_name_are_ambiguous(glossary):
    m = glossary.lookup("What is a bond?")
    assert m.ambiguous and [e.sense for e in m.entries] == ["fixed income", "surety"]


def test_a_real_question_falls_through_to_retrieval(glossary):
    assert glossary.lookup("What is the difference between a bond and a deposit in practice?") is None


def test_an_unknown_term_is_no_match(glossary):
    assert glossary.lookup("What is a warrant?") is None


def test_a_short_word_ending_in_s_is_not_singularised(glossary):
    assert glossary.lookup("What is gas") is None               # "gas" would become "ga"; terms of 3 letters stay as they are


def test_fuzzy_matching_is_off_by_default(glossary):
    assert glossary.lookup("expense ratoi") is None


def test_fuzzy_matching_can_be_switched_on(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text(YAML, encoding="utf-8")
    m = YamlGlossary(p, fuzzy_cutoff=0.8).lookup("expense ratoi")
    assert m.match_type == "fuzzy" and m.entries[0].term == "Expense ratio"


def test_a_fuzzy_cutoff_that_is_too_strict_finds_nothing(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text(YAML, encoding="utf-8")
    assert YamlGlossary(p, fuzzy_cutoff=0.99).lookup("expense ratoi") is None


def test_a_missing_file_is_an_error_that_names_the_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="nope.yaml"):
        YamlGlossary(tmp_path / "nope.yaml")


def test_an_empty_file_is_an_empty_glossary(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("", encoding="utf-8")
    assert YamlGlossary(p).lookup("What is a SIP") is None


def test_definitions_are_joined_onto_one_line(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("- term: X\n  definition: >\n    line one\n    line two\n", encoding="utf-8")
    assert YamlGlossary(p).lookup("X").entries[0].definition == "line one line two"


def test_an_alias_that_is_also_the_term_is_not_listed_twice(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("- term: SIP\n  aliases: [SIP, sip]\n  definition: d\n", encoding="utf-8")
    assert len(YamlGlossary(p).lookup("SIP").entries) == 1


# ================================================================ the real glossary file
REAL = yaml.safe_load((ROOT / "docs" / "knowledge-base" / "glossary.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def real():
    return YamlGlossary(ROOT / "docs" / "knowledge-base" / "glossary.yaml")


@pytest.mark.parametrize("entry", REAL, ids=lambda e: f"{e['term']}|{e.get('sense', '')}")
def test_every_real_term_finds_its_own_entry(real, entry):
    m = real.lookup(f"What is {entry['term']}?") if len(entry["term"].split()) <= 5 else None
    assert m is not None and entry["term"] in [e.term for e in m.entries]


def test_every_real_alias_finds_its_entry(real):
    missing = []
    for entry in REAL:
        for alias in entry.get("aliases", []):
            m = real.lookup(alias)
            if m is None or entry["term"] not in [e.term for e in m.entries]:
                missing.append((entry["term"], alias))
    assert missing == []


def test_the_only_ambiguous_term_is_the_deliberate_one(real):
    ambiguous = {e["term"] for e in REAL if real.lookup(e["term"]) and real.lookup(e["term"]).ambiguous}
    assert ambiguous == {"Bond"}


# ================================================================ registry and factory
@pytest.fixture
def fresh_kind():
    kind = "test-kind-" + str(id(object()))
    yield kind
    registry._REGISTRY.pop(kind, None)


def test_a_registered_class_can_be_built_from_a_spec(fresh_kind):
    @register(fresh_kind, "thing")
    class Thing:
        def __init__(self, size, colour="red"):
            self.size, self.colour = size, colour

    t = build(fresh_kind, {"type": "thing", "size": 3})
    assert isinstance(t, Thing) and t.size == 3 and t.colour == "red"


def test_runtime_dependencies_are_passed_alongside_the_spec(fresh_kind):
    @register(fresh_kind, "store")
    class Store:
        def __init__(self, path, model_id):
            self.path, self.model_id = path, model_id

    s = build(fresh_kind, {"type": "store", "path": "/x"}, model_id="m1")
    assert (s.path, s.model_id) == ("/x", "m1")


def test_the_same_name_cannot_be_registered_twice(fresh_kind):
    @register(fresh_kind, "dup")
    class A: ...

    with pytest.raises(ValueError, match="already registered by A"):
        @register(fresh_kind, "dup")
        class B: ...


def test_the_same_name_may_exist_under_different_kinds(fresh_kind):
    @register(fresh_kind, "same")
    class A: ...

    @register(fresh_kind + "-other", "same")
    class B: ...

    registry._REGISTRY.pop(fresh_kind + "-other", None)


def test_an_unknown_type_lists_what_is_available(fresh_kind):
    @register(fresh_kind, "alpha")
    class A: ...

    with pytest.raises(ValueError, match="Unknown .* 'nope'. Available: \\['alpha'\\]"):
        build(fresh_kind, {"type": "nope"})


def test_an_unknown_kind_lists_the_known_kinds():
    with pytest.raises(ValueError, match="Unknown kind 'no-such-kind'"):
        build("no-such-kind", {"type": "x"})
