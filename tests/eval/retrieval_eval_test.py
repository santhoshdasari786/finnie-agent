"""Live retrieval regression: the production retriever (threshold ON) against tests/eval/questions.yaml.

Costs one embedding call per question (~40). Skipped automatically without GOOGLE_API_KEY.
Run:  .venv/bin/python -m pytest tests/eval/retrieval_eval_test.py -v

Why it exists: min_score was chosen from a measured gap (in_kb lowest 0.739, off_topic highest 0.620).
If someone changes the threshold, the embedding model or the chunking, these tests say whether the gap survived.
"""
import os
from pathlib import Path

import pytest
import yaml
from dotenv import load_dotenv

from src.rag.common.models import RetrievalQuery

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
DATA = yaml.safe_load((Path(__file__).parent / "questions.yaml").read_text(encoding="utf-8"))

pytestmark = pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="live test: needs GOOGLE_API_KEY")


@pytest.fixture(scope="module")
def retriever():
    from src.rag.bootstrap import build_rag
    return build_rag().retriever


@pytest.mark.parametrize("item", DATA["in_kb"], ids=lambda i: i["q"][:50])
def test_in_kb_question_is_answerable_from_the_right_article(retriever, item):
    res = retriever.retrieve(RetrievalQuery(item["q"], k=5))
    assert res.status == "ok", f"wrongly refused (best={res.best_score})"
    assert item["expect"] in [c.metadata.get("doc_id") for c in res.chunks[:3]]


@pytest.mark.parametrize("item", DATA["off_topic"], ids=lambda i: i["q"][:50])
def test_off_topic_question_is_refused(retriever, item):
    res = retriever.retrieve(RetrievalQuery(item["q"], k=5))
    assert res.status == "no_source", f"leaked past the threshold (best={res.best_score})"
