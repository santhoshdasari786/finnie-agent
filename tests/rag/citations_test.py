"""citations.py: pure string/list logic, no fakes needed.

Run:  .venv/bin/python -m pytest tests/rag/citations_test.py -v
"""
from types import SimpleNamespace as NS

from src.rag.common.models import Citation
from src.rag.retrieval.citations import (primary_url, make_excerpt, merge_by_source,
                                         used_markers, renumber_markers)

def src(url):                       # renumber_markers only needs .citation.source
    return NS(citation=NS(source=url))

SRC = {1: src("a"), 2: src("a"), 3: src("b")}   # 1 and 2 are the SAME article


# ---------------------------------------------------------------- primary_url
def test_primary_url_takes_the_first_of_several():
    assert primary_url({"source_urls": "https://a, https://b"}) == "https://a"

def test_primary_url_falls_back_to_title_then_empty():
    assert primary_url({"title": "T"}) == "T"
    assert primary_url({}) == ""


# ---------------------------------------------------------------- make_excerpt
def test_excerpt_strips_markdown():
    assert make_excerpt("# Head\n**Bold** text.") == "Head Bold text."

def test_short_excerpt_is_unchanged():
    assert make_excerpt("Short one.") == "Short one."

def test_long_excerpt_is_cut_cleanly():
    out = make_excerpt("word " * 100)
    assert len(out) <= 201 and out.endswith(("…", "."))


# ---------------------------------------------------------------- used_markers
def test_used_markers_handles_groups_order_and_invalid():
    assert used_markers("a [2] b [1, 9] c [2]", {1, 2, 3}) == [2, 1]

def test_used_markers_none_found():
    assert used_markers("no markers here", {1, 2}) == []


# ---------------------------------------------------------------- merge_by_source
def test_merge_by_source_keeps_first_and_order():
    a1 = Citation(source="a", title="A first", excerpt="x")
    b = Citation(source="b", title="B", excerpt="y")
    a2 = Citation(source="a", title="A second", excerpt="z")
    assert merge_by_source([a1, b, a2]) == [a1, b]


# ---------------------------------------------------------------- renumber_markers
def test_renumber_maps_to_merged_position():
    assert renumber_markers("x [3]", [3], SRC) == "x [1]"

def test_separate_claims_keep_their_own_marker():
    assert renumber_markers("See [1] and [2].", [1, 2], SRC) == "See [1] and [1]."

def test_group_marker_expands():
    assert renumber_markers("x [1, 3] y", [1, 3], SRC) == "x [1][2] y"

def test_invented_marker_is_removed_mid_sentence_with_one_space():
    assert renumber_markers("x [9] y", [], SRC) == "x y"


# ---------------------------------------------------------------- the two known bugs (red until fixed)
def test_adjacent_markers_for_the_same_source_collapse():           # A22
    assert renumber_markers("SIPs [1][2] work.", [1, 2], SRC) == "SIPs [1] work."

def test_invented_marker_leaves_no_stray_space():                    # A23
    assert renumber_markers("Great [9].", [], SRC) == "Great."
