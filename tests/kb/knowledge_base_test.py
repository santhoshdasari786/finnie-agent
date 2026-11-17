"""Quality lint for the knowledge base: every article, the glossary, and the retrieval questions that point at them.

Run:  .venv/bin/python -m pytest tests/kb -v
Offline and instant. It does not judge whether a fact is TRUE (only a person with the source can); it makes sure every
article is complete, honest about how it was checked, free of advice wording, and wired into the glossary and the eval set.

Rules (each one exists because of a real failure or a stated guardrail in docs/knowledge-base/content-backlog.md)
  structure      front matter complete and valid; article_id == file name; the same sections in every article
  honesty        Source References says how each source was checked; Reviewer says AI-assisted
  education      no "you should buy/sell" style wording
  freshness      a time-sensitive article tells the reader to verify, and quotes no figures outside its worked example
  links          every related_articles id exists; no article points at itself
  coverage       at least 50 articles, every topic has several, every article has a retrieval question
"""
import re
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
KB = ROOT / "docs" / "knowledge-base"
ARTICLES = sorted((KB / "articles").glob("*.md"))
TOPICS = {"foundations", "growth-portfolio", "products", "costs-taxes", "behaviour-risk", "safety-regulation", "worked-examples"}
REQUIRED = ["article_id", "title", "topic", "summary", "source_urls", "jurisdiction", "risk_level", "last_verified_at", "version", "related_articles"]
SECTIONS = ["## Purpose", "## Core Concepts", "## Misconceptions", "## Source References", "## Review Metadata"]
ADVICE = re.compile(r"\byou should (buy|sell|invest in|put your money)\b|\bi recommend\b|\bbest (stock|fund|scheme) to (buy|invest)\b|\bguaranteed to (grow|beat|double)\b", re.I)


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, f"{path.name}: no front matter"
    return yaml.safe_load(m.group(1)), m.group(2)


PARSED = {p.stem: load(p) for p in ARTICLES}
IDS = set(PARSED)
param = pytest.mark.parametrize("stem", sorted(PARSED))


def section(body: str, heading: str) -> str:
    m = re.search(rf"^{re.escape(heading)}\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- structure
@param
def test_front_matter_is_complete(stem):
    meta, _ = PARSED[stem]
    assert [k for k in REQUIRED if k not in meta or meta[k] in (None, "")] == [] or meta.get("related_articles") == []
    assert [k for k in REQUIRED if k not in meta] == []


@param
def test_the_id_matches_the_file_name(stem):
    assert PARSED[stem][0]["article_id"] == stem


@param
def test_topic_jurisdiction_and_risk_level_are_from_the_allowed_lists(stem):
    meta, _ = PARSED[stem]
    assert meta["topic"] in TOPICS
    assert meta["jurisdiction"] in {"india", "global", "other"}
    assert meta["risk_level"] in {"normal", "high-impact", "time-sensitive"}


@param
def test_dates_and_version_have_the_right_shape(stem):
    meta, _ = PARSED[stem]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(meta["last_verified_at"]))
    assert isinstance(meta["version"], int) and meta["version"] >= 1


@param
def test_summary_is_a_real_sentence(stem):
    assert len(PARSED[stem][0]["summary"]) >= 60


@param
def test_there_is_at_least_one_https_source(stem):
    urls = PARSED[stem][0]["source_urls"]
    links = [u for u in urls if u.startswith(("http://", "https://"))]
    assert links and all(u.startswith("https://") for u in links)          # circular numbers etc. may be listed as plain text too


@param
def test_the_body_starts_with_the_title_and_has_every_section(stem):
    meta, body = PARSED[stem]
    assert body.lstrip().startswith(f"# {meta['title']}")
    assert [s for s in SECTIONS if s not in body] == []


@param
def test_length_is_reasonable_for_retrieval(stem):
    words = len(PARSED[stem][1].split())
    assert 250 <= words <= 1500, f"{words} words"


@param
def test_core_concepts_is_a_list_of_several_points(stem):
    assert len(re.findall(r"^- ", section(PARSED[stem][1], "## Core Concepts"), re.M)) >= 4


@param
def test_misconceptions_names_at_least_two(stem):
    assert len(re.findall(r"^- ", section(PARSED[stem][1], "## Misconceptions"), re.M)) >= 2


def test_titles_and_summaries_are_unique():
    titles = Counter(m["title"] for m, _ in PARSED.values())
    summaries = Counter(m["summary"] for m, _ in PARSED.values())
    assert [t for t, n in titles.items() if n > 1] == [] and [s for s, n in summaries.items() if n > 1] == []


# ---------------------------------------------------------------- honesty and education
@param
def test_source_references_say_how_the_sources_were_checked(stem):
    refs = section(PARSED[stem][1], "## Source References").lower()
    assert re.search(r"fetch|search|general|not (independently )?(verified|confirmed)|blocked", refs), "say how it was checked"


@param
def test_the_reviewer_line_says_there_was_no_human_review(stem):
    review = section(PARSED[stem][1], "## Review Metadata")
    assert re.search(r"AI-assisted|no qualified", review, re.I)


@param
def test_no_advice_wording(stem):
    assert ADVICE.search(PARSED[stem][1]) is None


# ---------------------------------------------------------------- freshness
@param
def test_a_time_sensitive_article_tells_the_reader_to_verify(stem):
    meta, body = PARSED[stem]
    if meta["risk_level"] == "time-sensitive":
        assert re.search(r"verify|confirm|check (the )?current", body, re.I)


# Articles that knowingly quote one dated figure and tell the reader to recheck it. Add to this list only with a reason.
DATED_FIGURE_OK = {
    "expense-ratios-and-fees": "quotes AMFI's index-fund cap, tied to a named March 2026 circular, and says to recheck it",
}


@param
def test_a_time_sensitive_article_quotes_no_figures_outside_its_worked_example(stem):
    meta, body = PARSED[stem]
    if meta["risk_level"] != "time-sensitive" or stem in DATED_FIGURE_OK:
        pytest.skip("not time-sensitive, or an explained exception")
    outside = re.sub(r"^## Worked Example\n.*?(?=^## |\Z)", "", body, flags=re.S | re.M)
    outside = re.sub(r"^## (Source References|Review Metadata)\n.*", "", outside, flags=re.S | re.M)
    assert re.findall(r"\d+(\.\d+)?\s?%", outside) == [], "tax rates, interest rates and limits go stale: say where to look instead"


# ---------------------------------------------------------------- links
@param
def test_related_articles_exist_and_are_not_self(stem):
    related = PARSED[stem][0]["related_articles"] or []
    assert [r for r in related if r not in IDS] == []
    assert stem not in related


# ---------------------------------------------------------------- coverage
def test_there_are_at_least_fifty_articles():
    assert len(ARTICLES) >= 50


def test_every_topic_has_several_articles():
    counts = Counter(m["topic"] for m, _ in PARSED.values())
    assert {t: counts[t] for t in TOPICS if counts[t] < 2} == {}


def test_the_tax_agent_has_enough_to_work_with():
    assert sum(1 for m, _ in PARSED.values() if m["topic"] == "costs-taxes") >= 6


# ---------------------------------------------------------------- the glossary
GLOSSARY = yaml.safe_load((KB / "glossary.yaml").read_text(encoding="utf-8"))
ENTRIES = GLOSSARY if isinstance(GLOSSARY, list) else GLOSSARY.get("terms", GLOSSARY)


def test_the_glossary_is_big_enough_to_be_useful():
    assert len(ENTRIES) >= 60


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: f"{e['term']}|{e.get('sense', '')}")
def test_every_glossary_entry_is_complete(entry):
    assert len(" ".join(str(entry["definition"]).split())) >= 25
    assert entry.get("topic") in TOPICS or entry.get("topic") is None
    assert [r for r in entry.get("related_articles", []) if r not in IDS] == []


def test_no_two_entries_share_a_name_unless_they_are_marked_as_different_senses():
    seen: dict[str, set] = {}
    clashes = []
    for e in ENTRIES:
        for name in [e["term"], *e.get("aliases", [])]:
            key = name.lower()
            senses = seen.setdefault(key, set())
            if senses and (e.get("sense") is None or e.get("sense") in senses or None in senses):
                clashes.append(name)
            senses.add(e.get("sense"))
    assert clashes == []


# ---------------------------------------------------------------- the retrieval questions
QUESTIONS = yaml.safe_load((ROOT / "tests" / "eval" / "questions.yaml").read_text(encoding="utf-8"))


def test_every_expected_article_exists():
    assert [q["expect"] for q in QUESTIONS["in_kb"] if q["expect"] not in IDS] == []


def test_every_article_has_at_least_one_retrieval_question():
    asked = {q["expect"] for q in QUESTIONS["in_kb"]}
    assert sorted(IDS - asked) == []


def test_no_question_is_listed_twice():
    every = [q["q"].strip().lower() for g in ("in_kb", "borderline", "off_topic") for q in QUESTIONS[g]]
    assert [q for q, n in Counter(every).items() if n > 1] == []


def test_price_questions_are_routed_to_the_market_agent_before_retrieval():
    from src.workflow.router import route_by_rules
    wrong = [q["q"] for q in QUESTIONS["routed_to_market"]
             if (route_by_rules(q["q"]) is None or str(route_by_rules(q["q"]).intent) != "market")]
    assert wrong == []


def test_educational_questions_about_indices_are_not_swallowed_by_the_market_rule():
    from src.workflow.router import route_by_rules
    for q in ("Can I invest directly in the Sensex or the Nifty?", "What is a benchmark index and why is a fund compared with it?"):
        d = route_by_rules(q)
        assert d is None or str(d.intent) != "market", q


def test_no_term_or_alias_is_too_long_to_ever_match():
    # the matcher treats more than five words as a real question, not a term: such an entry could never be found
    too_long = [n for e in ENTRIES for n in [e["term"], *e.get("aliases", [])] if len(n.split()) > 5]
    assert too_long == []
