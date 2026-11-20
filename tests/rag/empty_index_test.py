"""A fresh install (or a fresh Docker volume) has no index yet. The app must still start.

Run:  .venv/bin/python -m pytest tests/rag/empty_index_test.py -v
Contract
  * build_rag() on an empty vector store returns a working Rag (glossary, retriever) and logs a warning that says how to build the index
  * a missing API key is still a hard error (nothing could work)
No network: the embedder is only constructed, never called.
"""
import logging

import pytest
import yaml

from src.rag.bootstrap import CONFIG_PATH, build_rag
from src.rag.common.models import Rag


@pytest.fixture
def config(tmp_path, monkeypatch):
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg["vector_store"]["path"] = str(tmp_path / "chroma")
    path = tmp_path / "rag.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    monkeypatch.setenv("GOOGLE_API_KEY", "not-a-real-key")
    return path


def test_an_empty_index_still_builds_the_pipeline(config):
    assert isinstance(build_rag(config), Rag)


def test_the_warning_says_how_to_build_the_index(config, caplog):
    with caplog.at_level(logging.WARNING):
        build_rag(config)
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "empty" in text and "src.rag.ingestion.cli" in text


def test_the_glossary_still_works_without_an_index(config):
    rag = build_rag(config)
    assert rag.glossary.lookup("What is a margin call?") is not None


def test_a_missing_key_is_still_an_error(config, monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY")
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        build_rag(config)
