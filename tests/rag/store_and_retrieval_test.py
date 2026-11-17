"""The Chroma store (real Chroma in a temp folder), the retrieval post-processors and the vector retriever.

Run:  .venv/bin/python -m pytest tests/rag/store_and_retrieval_test.py -v
Offline: vectors are written by hand, so cosine scores are easy to reason about.

Contract
  ChromaStore   one collection per (name, model, dimensions); upsert replaces by id; search returns similarity 0..1 best first
                and accepts SEVERAL metadata filters at once (a category AND an extra filter)
  threshold     keeps hits scoring at least min_score
  per_doc_cap   keeps at most N chunks from one document
  dedupe        drops a hit that is nearly the same text as a better one
  retriever     embeds the question, over-fetches (k x multiplier), post-processes, trims to k, and says no_source when empty
"""
import pytest

from src.rag.common.models import EmbeddedChunk, Chunk, RetrievalQuery, SearchHit
from src.rag.ingestion.stores.chroma import ChromaStore
from src.rag.retrieval.postprocessors.dedupe import Deduplicator
from src.rag.retrieval.postprocessors.per_doc_cap import PerDocCap
from src.rag.retrieval.postprocessors.threshold import ThresholdFilter
from src.rag.retrieval.retrievers.vector import VectorRetriever


def item(cid, doc, text, vector, **meta):
    return EmbeddedChunk(Chunk(cid, doc, text, {"doc_id": doc, **meta}), vector)


@pytest.fixture
def store(tmp_path):
    s = ChromaStore("kb", str(tmp_path / "chroma"), "my/model:1", 3)
    s.ensure_collection()
    s.upsert([
        item("a:0", "a", "alpha text", [1.0, 0.0, 0.0], topic="products", risk="low"),
        item("b:0", "b", "beta text", [0.9, 0.1, 0.0], topic="costs-taxes", risk="low"),
        item("c:0", "c", "gamma text", [0.0, 1.0, 0.0], topic="products", risk="high"),
    ])
    return s


# ================================================================ the store
def test_the_collection_name_carries_the_model_and_the_size_with_unsafe_characters_replaced():
    assert ChromaStore("kb", "/tmp/x-unused", "my/model:1", 768).name == "kb__my-model-1__768"


def test_info_reports_what_is_stored(store):
    info = store.info()
    assert (info.name, info.dimensions, info.model_id, info.count) == ("kb__my-model-1__3", 3, "my/model:1", 3)


def test_search_returns_the_nearest_first_with_a_similarity_score(store):
    hits = store.search([1.0, 0.0, 0.0], k=3)
    assert [h.chunk_id for h in hits] == ["a:0", "b:0", "c:0"]
    assert hits[0].score == pytest.approx(1.0, abs=1e-6) and hits[0].score > hits[1].score > hits[2].score
    assert hits[0].text == "alpha text" and hits[0].metadata["topic"] == "products"


def test_search_stops_at_k(store):
    assert len(store.search([1.0, 0.0, 0.0], k=2)) == 2


def test_one_filter_narrows_the_search(store):
    assert {h.chunk_id for h in store.search([1.0, 0.0, 0.0], k=5, filters={"topic": "products"})} == {"a:0", "c:0"}


def test_two_filters_at_once_must_both_hold(store):
    # a category AND an extra filter: Chroma needs an explicit $and for this
    hits = store.search([1.0, 0.0, 0.0], k=5, filters={"topic": "products", "risk": "high"})
    assert [h.chunk_id for h in hits] == ["c:0"]


def test_no_filter_means_no_where_clause(store):
    assert len(store.search([1.0, 0.0, 0.0], k=5, filters=None)) == 3
    assert len(store.search([1.0, 0.0, 0.0], k=5, filters={})) == 3


def test_upsert_replaces_a_chunk_with_the_same_id(store):
    store.upsert([item("a:0", "a", "alpha CHANGED", [1.0, 0.0, 0.0], topic="products", risk="low")])
    assert store.info().count == 3
    assert store.search([1.0, 0.0, 0.0], k=1)[0].text == "alpha CHANGED"


def test_delete_by_doc_removes_only_that_document(store):
    store.delete_by_doc("a")
    assert {h.chunk_id for h in store.search([1.0, 0.0, 0.0], k=5)} == {"b:0", "c:0"}


def test_the_data_survives_reopening_the_folder(store, tmp_path):
    again = ChromaStore("kb", str(tmp_path / "chroma"), "my/model:1", 3)
    again.ensure_collection()
    assert again.info().count == 3


# ================================================================ post-processors
def hit(cid, score, text="t", **meta):
    return SearchHit(cid, text, score, {"doc_id": cid.split(":")[0], **meta})


def test_threshold_keeps_hits_at_or_above_the_minimum():
    out = ThresholdFilter(0.66).process("q", [hit("a:0", 0.9), hit("b:0", 0.66), hit("c:0", 0.6599)])
    assert [h.chunk_id for h in out] == ["a:0", "b:0"]


def test_threshold_can_empty_the_list():
    assert ThresholdFilter(0.99).process("q", [hit("a:0", 0.5)]) == []


def test_per_doc_cap_keeps_the_best_chunks_of_each_document():
    hits = [hit("a:0", .9), hit("a:1", .8), hit("a:2", .7), hit("b:0", .6), hit("b:1", .5)]
    assert [h.chunk_id for h in PerDocCap(2).process("q", hits)] == ["a:0", "a:1", "b:0", "b:1"]


def test_per_doc_cap_groups_by_chunk_id_when_there_is_no_doc_id():
    h = SearchHit("lonely", "t", 0.9, {})
    assert PerDocCap(1).process("q", [h, SearchHit("other", "t", 0.8, {})]) == [h, SearchHit("other", "t", 0.8, {})]


SAME = "compound interest means earning returns on both the original amount and on earlier returns over time"


def test_dedupe_drops_a_near_copy_and_keeps_the_better_one():
    hits = [hit("a:0", .9, SAME), hit("b:0", .8, SAME + " today"), hit("c:0", .7, "bonds pay a fixed coupon each year until maturity")]
    assert [h.chunk_id for h in Deduplicator(0.8).process("q", hits)] == ["a:0", "c:0"]


def test_dedupe_keeps_different_texts():
    hits = [hit("a:0", .9, "gold has no yield"), hit("b:0", .8, "bonds pay interest")]
    assert len(Deduplicator(0.9).process("q", hits)) == 2


def test_dedupe_treats_short_texts_without_failing():
    hits = [hit("a:0", .9, "hi"), hit("b:0", .8, "hi"), hit("c:0", .7, "")]
    assert [h.chunk_id for h in Deduplicator(0.9).process("q", hits)] == ["a:0", "c:0"]


@pytest.mark.parametrize("bad", [0, -0.1, 1.5])
def test_dedupe_refuses_a_similarity_outside_zero_to_one(bad):
    with pytest.raises(ValueError):
        Deduplicator(bad)


def test_dedupe_similarity_of_exactly_one_means_identical_only():
    hits = [hit("a:0", .9, SAME), hit("b:0", .8, SAME), hit("c:0", .7, SAME + " more words")]
    assert [h.chunk_id for h in Deduplicator(1.0).process("q", hits)] == ["a:0", "c:0"]


# ================================================================ the retriever
class FakeEmbedder:
    def __init__(self):
        self.queries = []

    def embed_query(self, text):
        self.queries.append(text)
        return [1.0, 0.0, 0.0]


class FakeStore:
    def __init__(self, hits):
        self.hits, self.calls = hits, []

    def search(self, vector, k, filters=None):
        self.calls.append((vector, k, filters))
        return self.hits[:k]


def retriever(hits, **kw):
    return VectorRetriever(FakeEmbedder(), FakeStore(hits), **kw)


def test_the_question_is_embedded_and_the_store_over_fetches():
    r = retriever([hit(f"d{i}:0", 0.9 - i / 100) for i in range(30)], fetch_multiplier=4)
    r.retrieve(RetrievalQuery("what is a SIP", k=5))
    assert r.embedder.queries == ["what is a SIP"] and r.store.calls[0][1] == 20


def test_the_result_is_trimmed_to_k_and_carries_the_best_score():
    r = retriever([hit(f"d{i}:0", 0.9 - i / 100) for i in range(30)])
    res = r.retrieve(RetrievalQuery("q", k=3))
    assert res.status == "ok" and len(res.chunks) == 3 and res.best_score == pytest.approx(0.9)


def test_chunks_expose_source_title_and_metadata():
    r = retriever([SearchHit("a:0", "text", 0.8, {"doc_id": "a", "source": "/x/a.md", "title": "A Title"})])
    c = r.retrieve(RetrievalQuery("q")).chunks[0]
    assert (c.chunk_id, c.text, c.score, c.source, c.title) == ("a:0", "text", 0.8, "/x/a.md", "A Title")


def test_missing_source_and_title_become_empty_strings():
    c = retriever([SearchHit("a:0", "text", 0.8, {})]).retrieve(RetrievalQuery("q")).chunks[0]
    assert c.source == "" and c.title == ""


def test_no_hits_is_no_source_and_no_score():
    res = retriever([]).retrieve(RetrievalQuery("q"))
    assert res.status == "no_source" and res.chunks == [] and res.best_score is None


def test_post_processors_run_in_order_before_the_trim():
    hits = [hit("a:0", .9), hit("a:1", .8), hit("a:2", .7), hit("b:0", .5)]
    r = retriever(hits, post_processors=[PerDocCap(1), ThresholdFilter(0.6)])
    assert [c.chunk_id for c in r.retrieve(RetrievalQuery("q", k=5)).chunks] == ["a:0"]


def test_everything_filtered_out_is_no_source():
    r = retriever([hit("a:0", .5)], post_processors=[ThresholdFilter(0.66)])
    assert r.retrieve(RetrievalQuery("q")).status == "no_source"


def test_the_category_becomes_a_filter_on_the_category_field():
    r = retriever([hit("a:0", .9)])
    r.retrieve(RetrievalQuery("q", category="costs-taxes"))
    assert r.store.calls[0][2] == {"topic": "costs-taxes"}


def test_the_category_field_can_be_renamed():
    r = retriever([hit("a:0", .9)], category_field="kind")
    r.retrieve(RetrievalQuery("q", category="x"))
    assert r.store.calls[0][2] == {"kind": "x"}


def test_a_category_and_other_filters_are_combined_without_changing_the_callers_dict():
    extra = {"risk": "low"}
    r = retriever([hit("a:0", .9)])
    r.retrieve(RetrievalQuery("q", category="products", filters=extra))
    assert r.store.calls[0][2] == {"risk": "low", "topic": "products"} and extra == {"risk": "low"}


def test_no_category_and_no_filters_means_none_is_passed():
    r = retriever([hit("a:0", .9)])
    r.retrieve(RetrievalQuery("q"))
    assert r.store.calls[0][2] is None


def test_a_multiplier_below_one_is_refused():
    with pytest.raises(ValueError):
        VectorRetriever(FakeEmbedder(), FakeStore([]), fetch_multiplier=0)


def test_the_retriever_works_on_a_real_store(store):
    r = VectorRetriever(FakeEmbedder(), store, post_processors=[ThresholdFilter(0.5)])
    res = r.retrieve(RetrievalQuery("q", k=5, category="products", filters={"risk": "high"}))
    assert [c.chunk_id for c in res.chunks] == []                    # c:0 is high-risk but orthogonal to the query: below 0.5
    res = r.retrieve(RetrievalQuery("q", k=5, category="products"))
    assert [c.chunk_id for c in res.chunks] == ["a:0"]
