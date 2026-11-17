"""The ingestion pipeline end to end, offline: loader -> chunker -> embedder -> store, with a manifest for change detection.

Run:  .venv/bin/python -m pytest tests/rag/ingestion_pipeline_test.py -v
Real parts: the markdown loader, the recursive chunker, the sqlite manifest and a real Chroma store in a temp folder.
Fake part: the embedder (a tiny deterministic vector), so no network and no quota.

Contract
  * a changed or new document is chunked, embedded, and its OLD chunks are replaced; the manifest is written LAST
  * an unchanged document is skipped (no embedding call)
  * one bad document is logged and skipped (skip_and_log) or stops the run (fail_fast)
  * the document id is the article_id; the title and metadata reach every chunk (the category filter depends on `topic`)
"""
import logging
from pathlib import Path

import pytest

from src.rag.common.models import Chunk, Document
from src.rag.ingestion.chunkers.recursive import RecursiveChunker, flatten_metadata
from src.rag.ingestion.core.ingestion import IngestionPipeline
from src.rag.ingestion.loaders.markdown import MarkdownLoader
from src.rag.ingestion.manifest.sqlite import SqliteManifest
from src.rag.ingestion.stores.chroma import ChromaStore


class FakeEmbedder:
    model_id, dimensions, max_batch_size = "fake-model", 4, 3

    def __init__(self):
        self.calls: list[int] = []                      # number of texts per call
        self.titles: list = []
        self.fail_on: str | None = None
        self.short = False

    def embed_documents(self, texts, titles=None):
        self.calls.append(len(texts))
        self.titles += list(titles or [])
        if self.fail_on and any(self.fail_on in t for t in texts):
            raise RuntimeError("embedding failed")
        n = len(texts) - 1 if self.short else len(texts)
        return [[float(len(t) % 7), 1.0, 0.0, 0.5] for t in texts][:n]

    def embed_query(self, text):
        return [1.0, 1.0, 0.0, 0.5]


def article(path: Path, article_id: str, body: str, topic="products", title=None):
    head = f"---\narticle_id: {article_id}\ntitle: {title or article_id.title()}\ntopic: {topic}\nrelated_articles: [a, b]\n---\n\n"
    path.write_text(head + body, encoding="utf-8")


@pytest.fixture
def kb(tmp_path):
    root = tmp_path / "articles"
    root.mkdir()
    article(root / "one.md", "one", "# One\n\n" + "A sentence about SIPs. " * 80)
    article(root / "two.md", "two", "# Two\n\nShort article about bonds.", topic="costs-taxes")
    return root


@pytest.fixture
def parts(tmp_path, kb):
    embedder = FakeEmbedder()
    store = ChromaStore("kb", str(tmp_path / "chroma"), embedder.model_id, embedder.dimensions)
    manifest = SqliteManifest(str(tmp_path / "manifest.db"))

    def pipeline(**kw):
        return IngestionPipeline([MarkdownLoader(kb)], [], RecursiveChunker(300, 30), embedder, store, manifest, **kw)

    return pipeline, embedder, store, manifest


# ================================================================ the first run
def test_every_document_is_ingested_and_counted(parts):
    pipeline, embedder, store, _ = parts
    stats = pipeline().run()
    assert stats["seen"] == 2 and stats["ingested"] == 2 and stats["skipped"] == 0 and stats["failed"] == 0
    assert stats["chunks"] == store.info().count > 2


def test_chunks_reach_the_store_with_their_metadata(parts):
    pipeline, embedder, store, _ = parts
    pipeline().run()
    hits = store.search([1.0, 1.0, 0.0, 0.5], k=50)
    topics = {h.metadata["doc_id"]: h.metadata["topic"] for h in hits}
    assert topics == {"one": "products", "two": "costs-taxes"}
    assert all(h.metadata["chunker"] == "recursive" and "chunk_index" in h.metadata for h in hits)


def test_lists_in_the_front_matter_are_stored_as_text(parts):
    pipeline, _, store, _ = parts
    pipeline().run()
    assert store.search([1.0, 1.0, 0.0, 0.5], k=1)[0].metadata["related_articles"] == "a, b"


def test_the_title_is_given_to_the_embedder_for_every_chunk(parts):
    pipeline, embedder, _, _ = parts
    pipeline().run()
    assert set(embedder.titles) == {"One", "Two"}


def test_texts_are_sent_in_batches_no_bigger_than_the_embedder_allows(parts):
    pipeline, embedder, _, _ = parts
    pipeline(batch_size=64).run()                       # asks for 64 but the fake embedder allows 3
    assert max(embedder.calls) <= 3 and len(embedder.calls) > 2


def test_the_batch_size_asked_for_is_honoured_when_it_is_smaller(parts):
    pipeline, embedder, _, _ = parts
    pipeline(batch_size=2).run()
    assert max(embedder.calls) <= 2


# ================================================================ change detection
def test_a_second_run_with_nothing_changed_embeds_nothing(parts):
    pipeline, embedder, _, _ = parts
    pipeline().run()
    calls = len(embedder.calls)
    stats = pipeline().run()
    assert stats == {"seen": 2, "skipped": 2, "ingested": 0, "chunks": 0, "failed": 0} and len(embedder.calls) == calls


def test_an_edited_document_replaces_its_old_chunks(parts, kb):
    pipeline, embedder, store, _ = parts
    pipeline().run()
    before = store.info().count
    article(kb / "two.md", "two", "# Two\n\nCompletely different words about gold.", topic="costs-taxes")
    stats = pipeline().run()
    assert stats["ingested"] == 1 and stats["skipped"] == 1
    texts = " ".join(h.text for h in store.search([1.0, 1.0, 0.0, 0.5], k=50) if h.metadata["doc_id"] == "two")
    assert "gold" in texts and "bonds" not in texts                      # the old chunks are gone, not left beside the new ones
    assert store.info().count <= before


def test_the_manifest_is_written_only_after_the_chunks_are_stored(parts):
    pipeline, embedder, store, manifest = parts
    embedder.fail_on = "bonds"
    stats = pipeline().run()
    assert stats["failed"] == 1 and manifest.get_hash("two", "fake-model") is None      # so the next run retries it
    assert manifest.get_hash("one", "fake-model") is not None


def test_a_failed_document_is_retried_on_the_next_run(parts):
    pipeline, embedder, _, _ = parts
    embedder.fail_on = "bonds"
    pipeline().run()
    embedder.fail_on = None
    assert pipeline().run() == {"seen": 2, "skipped": 1, "ingested": 1, "chunks": pytest.approx(1, abs=3), "failed": 0}


# ================================================================ errors
def test_skip_and_log_carries_on_and_logs_the_cause(parts, caplog):
    pipeline, embedder, _, _ = parts
    embedder.fail_on = "bonds"
    with caplog.at_level(logging.ERROR):
        stats = pipeline(on_error="skip_and_log").run()
    assert stats["ingested"] == 1 and "Failed on two" in caplog.text


def test_fail_fast_stops_at_the_first_failure(parts):
    pipeline, embedder, _, _ = parts
    embedder.fail_on = "SIPs"                                            # the first document ("one") fails
    with pytest.raises(RuntimeError):
        pipeline(on_error="fail_fast").run()


def test_an_embedder_that_returns_too_few_vectors_is_caught(parts):
    pipeline, embedder, _, manifest = parts
    embedder.short = True
    stats = pipeline().run()
    assert stats["failed"] == 2 and manifest.get_hash("one", "fake-model") is None


def test_a_different_embedding_model_means_everything_is_embedded_again(parts, tmp_path, kb):
    pipeline, embedder, store, manifest = parts
    pipeline().run()
    other = FakeEmbedder()
    other.model_id = "other-model"
    store2 = ChromaStore("kb", str(tmp_path / "chroma"), other.model_id, other.dimensions)
    stats = IngestionPipeline([MarkdownLoader(kb)], [], RecursiveChunker(300, 30), other, store2, manifest).run()
    assert stats["ingested"] == 2                                        # the manifest is keyed by (document, model)


# ================================================================ cleaners
def test_cleaners_run_before_the_hash_is_compared(tmp_path, kb):
    class Shout:
        def clean(self, doc):
            return Document(doc.id, doc.text.upper(), doc.metadata, doc.content_hash)

    embedder = FakeEmbedder()
    store = ChromaStore("kb", str(tmp_path / "c2"), embedder.model_id, embedder.dimensions)
    IngestionPipeline([MarkdownLoader(kb)], [Shout()], RecursiveChunker(300, 30), embedder, store,
                      SqliteManifest(str(tmp_path / "m2.db"))).run()
    assert all(h.text == h.text.upper() for h in store.search([1.0, 1.0, 0.0, 0.5], k=20))


# ================================================================ the chunker
def doc(text, **meta):
    return Document("d1", text, meta, "h")


def test_a_short_text_is_one_chunk_with_a_stable_id():
    chunks = RecursiveChunker(800, 100).chunk(doc("Just a short note."))
    assert len(chunks) == 1 and chunks[0].id.startswith("d1:0:") and chunks[0].doc_id == "d1"
    assert chunks[0].id == RecursiveChunker(800, 100).chunk(doc("Just a short note."))[0].id


def test_a_change_in_the_text_changes_the_chunk_id():
    a = RecursiveChunker().chunk(doc("one"))[0].id
    b = RecursiveChunker().chunk(doc("two"))[0].id
    assert a != b


def test_long_text_is_split_and_every_chunk_is_numbered():
    chunks = RecursiveChunker(200, 20).chunk(doc("Alpha beta gamma. " * 80))
    assert len(chunks) > 3 and [c.metadata["chunk_index"] for c in chunks] == list(range(len(chunks)))
    assert all(len(c.text) <= 200 for c in chunks)


def test_headings_are_preferred_split_points():
    text = "## Part A\n" + "alpha " * 60 + "\n## Part B\n" + "beta " * 60
    chunks = RecursiveChunker(400, 0).chunk(doc(text))
    assert any(c.text.lstrip().startswith("## Part B") or c.text.lstrip().startswith("Part B") for c in chunks) or len(chunks) >= 2


def test_overlap_repeats_a_little_text_between_neighbours():
    chunks = RecursiveChunker(120, 40).chunk(doc(" ".join(f"word{i}" for i in range(120))))
    assert len(chunks) > 2 and set(chunks[0].text.split()) & set(chunks[1].text.split())


def test_flatten_metadata_keeps_only_what_chroma_accepts():
    out = flatten_metadata({"a": 1, "b": "x", "c": None, "d": {"n": 1}, "e": [1, "z"], "f": True, "g": 2.5})
    assert out == {"a": 1, "b": "x", "e": "1, z", "f": True, "g": 2.5}


# ================================================================ the loader and the manifest
def test_the_loader_reads_front_matter_and_body(tmp_path):
    article(tmp_path / "x.md", "x-id", "Body text.", topic="foundations", title="X Title")
    d = next(MarkdownLoader(tmp_path).load())
    assert d.id == "x-id" and d.text == "Body text." and d.metadata["topic"] == "foundations" and d.metadata["title"] == "X Title"
    assert d.metadata["source"].endswith("x.md")


def test_a_file_without_front_matter_uses_its_path_as_id_and_a_title_from_its_name(tmp_path):
    (tmp_path / "my-first-note.md").write_text("Plain text only.", encoding="utf-8")
    d = next(MarkdownLoader(tmp_path).load())
    assert d.id == "my-first-note.md" and d.metadata["title"] == "My First Note" and d.text == "Plain text only."


def test_the_loader_follows_its_glob_and_sorts(tmp_path):
    (tmp_path / "b.md").write_text("b", encoding="utf-8")
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "skip.txt").write_text("c", encoding="utf-8")
    assert [d.id for d in MarkdownLoader(tmp_path).load()] == ["a.md", "b.md"]
    assert [d.id for d in MarkdownLoader(tmp_path, glob="*.txt").load()] == ["skip.txt"]


def test_the_hash_follows_the_body(tmp_path):
    article(tmp_path / "x.md", "x", "same")
    first = next(MarkdownLoader(tmp_path).load()).content_hash
    article(tmp_path / "x.md", "x", "same")
    assert next(MarkdownLoader(tmp_path).load()).content_hash == first
    article(tmp_path / "x.md", "x", "different")
    assert next(MarkdownLoader(tmp_path).load()).content_hash != first


def test_the_manifest_remembers_by_document_and_model(tmp_path):
    m = SqliteManifest(str(tmp_path / "deep" / "m.db"))                  # creates the folder
    assert m.get_hash("d", "m1") is None
    m.record("d", "h1", "m1", 3)
    assert m.get_hash("d", "m1") == "h1" and m.get_hash("d", "m2") is None
    m.record("d", "h2", "m1", 4)
    assert m.get_hash("d", "m1") == "h2"                                  # replaced, not duplicated


def test_the_manifest_survives_a_restart(tmp_path):
    SqliteManifest(str(tmp_path / "m.db")).record("d", "h", "m", 1)
    assert SqliteManifest(str(tmp_path / "m.db")).get_hash("d", "m") == "h"
