"""Live retrieval regression: the production retriever (threshold ON) against tests/eval/questions.yaml.

Costs one embedding call per question (~40). Skipped automatically without GOOGLE_API_KEY.
Run:  .venv/bin/python -m pytest tests/eval/retrieval_eval_test.py -v

Why it exists: min_score was chosen from a measured gap. Measured 2026-11-17 with 51 articles and 102 in_kb questions: in_kb
lowest 0.718 (top-3 hit 102/102, top-1 96/102), off_topic highest 0.652. If someone changes the threshold, the embedding model, the
chunking or the knowledge base, these tests say whether the gap survived. (Price questions are in `routed_to_market`: the router,
not retrieval, handles them; see tests/kb.)

The free tier of the embedding API allows 100 requests a minute and 1,000 a day: a 429 is waited out, and an
exhausted daily quota skips the test.
"""
import os
import time
from pathlib import Path

import pytest
import yaml
from dotenv import load_dotenv

from src.rag.common.models import RetrievalQuery
from src.rag.ingestion.embedders.gemini import EmbeddingUnavailable

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
DATA = yaml.safe_load((Path(__file__).parent / "questions.yaml").read_text(encoding="utf-8"))

pytestmark = pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="live test: needs GOOGLE_API_KEY")


class _Throttled:
    """The real retriever. The embedder already retries a per-minute 429 a few times; if it still gives up, wait for the
    minute window and try again. If the DAILY quota is used up, skip the test instead of failing it."""

    def __init__(self, inner):
        self._inner = inner

    def retrieve(self, query):
        for _ in range(6):
            try:
                return self._inner.retrieve(query)
            except EmbeddingUnavailable as e:
                if "daily" in str(e).lower():
                    pytest.skip("embedding quota for the day is used up")
                time.sleep(20)                                           # the per-minute limit: wait for the window
        raise RuntimeError("the embedding rate limit did not clear")


@pytest.fixture(scope="module")
def retriever():
    from src.rag.bootstrap import build_rag
    return _Throttled(build_rag().retriever)


@pytest.mark.parametrize("item", DATA["in_kb"], ids=lambda i: i["q"][:50])
def test_in_kb_question_is_answerable_from_the_right_article(retriever, item):
    res = retriever.retrieve(RetrievalQuery(item["q"], k=5))
    assert res.status == "ok", f"wrongly refused (best={res.best_score})"
    assert item["expect"] in [c.metadata.get("doc_id") for c in res.chunks[:3]]


@pytest.mark.parametrize("item", DATA["off_topic"], ids=lambda i: i["q"][:50])
def test_off_topic_question_is_refused(retriever, item):
    res = retriever.retrieve(RetrievalQuery(item["q"], k=5))
    assert res.status == "no_source", f"leaked past the threshold (best={res.best_score})"
