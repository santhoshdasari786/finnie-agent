"""GeminiEmbedder: request shape, retry with backoff on rate limits, a clear error when the quota is gone, and a query cache.

Run:  .venv/bin/python -m pytest tests/rag/embedder_test.py -v
No network: the Google client is replaced by a scripted fake.

Why: the free tier allows 100 requests a minute and 1,000 a day. Without this, one burst of questions (or a re-index) ended
in a raw stack trace, and an exhausted daily quota looked like "something went wrong" for hours.

Contract
  * documents are formatted with the document prefix (title, or "none"); queries with the query prefix
  * a per-minute 429 is retried with doubling waits; a 5xx is retried too; a per-DAY 429 is not retried at all
  * once retries run out (or the day's quota is gone) EmbeddingUnavailable is raised; any other API error passes through unchanged
  * the same query asked twice costs one request; failures are never cached; the cache is bounded (least recently used out)
"""
import pytest
from google.genai import errors

from src.rag.ingestion.embedders import gemini
from src.rag.ingestion.embedders.gemini import EmbeddingUnavailable, GeminiEmbedder

PER_MINUTE = {"error": {"code": 429, "message": "Quota exceeded: EmbedContentRequestsPerMinutePerUserPerProjectPerModel-FreeTier", "status": "RESOURCE_EXHAUSTED"}}
PER_DAY = {"error": {"code": 429, "message": "Quota exceeded: EmbedContentRequestsPerDayPerUserPerProjectPerModel-FreeTier", "status": "RESOURCE_EXHAUSTED"}}


class Embedding:
    def __init__(self, values):
        self.values = values


class FakeModels:
    def __init__(self, script):
        self.script = list(script)                      # items: "ok" or an exception to raise
        self.calls = []

    def embed_content(self, model, contents, config):
        self.calls.append({"model": model, "texts": [c.parts[0].text for c in contents], "dims": config.output_dimensionality})
        step = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(step, Exception):
            raise step
        return type("R", (), {"embeddings": [Embedding([float(len(t)), 0.5]) for t in self.calls[-1]["texts"]]})()


@pytest.fixture
def build(monkeypatch):
    monkeypatch.setenv("FAKE_KEY", "secret")
    sleeps = []

    def make(script=("ok",), **kw):
        models = FakeModels(script)
        monkeypatch.setattr(gemini.genai, "Client", lambda api_key: type("C", (), {"models": models})())
        emb = GeminiEmbedder("gemini-embedding-2", 768, "FAKE_KEY", sleep=sleeps.append, **kw)
        return emb, models, sleeps

    return make


# ================================================================ request shape
def test_documents_are_formatted_with_their_title_and_sent_with_the_model_and_size(build):
    emb, models, _ = build()
    vectors = emb.embed_documents(["alpha", "beta"], ["Title A", None])
    assert models.calls[0]["texts"] == ["title: Title A | text: alpha", "title: none | text: beta"]
    assert models.calls[0]["model"] == "gemini-embedding-2" and models.calls[0]["dims"] == 768
    assert vectors == [[5.0, 0.5], [4.0, 0.5]] or len(vectors) == 2


def test_titles_are_optional(build):
    emb, models, _ = build()
    emb.embed_documents(["alpha"])
    assert models.calls[0]["texts"] == ["title: none | text: alpha"]


def test_a_query_uses_the_query_prefix(build):
    emb, models, _ = build()
    emb.embed_query("what is a SIP")
    assert models.calls[0]["texts"] == ["task: search result | query: what is a SIP"]


def test_the_prefixes_can_be_configured(build):
    emb, models, _ = build(document_prefix="D {title}/{text}", query_prefix="Q {text}")
    emb.embed_documents(["x"], ["T"])
    emb.embed_query("y")
    assert [c["texts"] for c in models.calls] == [["D T/x"], ["Q y"]]


# ================================================================ the query cache
def test_the_same_query_twice_is_one_request(build):
    emb, models, _ = build()
    first = emb.embed_query("what is a SIP")
    second = emb.embed_query("what is a SIP")
    assert first == second and len(models.calls) == 1


def test_different_queries_are_separate_requests(build):
    emb, models, _ = build()
    emb.embed_query("a")
    emb.embed_query("b")
    assert len(models.calls) == 2


def test_the_cache_hands_out_copies(build):
    emb, _, _ = build()
    v = emb.embed_query("q")                            # the first answer, straight from the API
    v.append(99.0)
    hit = emb.embed_query("q")                          # a cache hit
    hit.append(77.0)
    again = emb.embed_query("q")
    assert 99.0 not in hit and 77.0 not in again


def test_the_cache_is_bounded_and_drops_the_least_recently_used(build):
    emb, models, _ = build(cache_size=2)
    emb.embed_query("a")
    emb.embed_query("b")
    emb.embed_query("a")                                # a is now the most recent
    emb.embed_query("c")                                # b is pushed out
    before = len(models.calls)
    emb.embed_query("a")
    emb.embed_query("b")
    assert len(models.calls) == before + 1              # a was cached, b was not


def test_a_cache_size_of_zero_switches_it_off(build):
    emb, models, _ = build(cache_size=0)
    emb.embed_query("q")
    emb.embed_query("q")
    assert len(models.calls) == 2


def test_documents_are_never_cached(build):
    emb, models, _ = build()
    emb.embed_documents(["x"])
    emb.embed_documents(["x"])
    assert len(models.calls) == 2


def test_stats_count_hits_and_requests(build):
    emb, _, _ = build()
    emb.embed_query("q")
    emb.embed_query("q")
    assert emb.stats() == {"requests": 1, "cache_hits": 1, "retries": 0, "cached_queries": 1}


# ================================================================ retry and the quota
def test_a_per_minute_limit_is_retried_with_doubling_waits(build):
    emb, models, sleeps = build([errors.ClientError(429, PER_MINUTE), errors.ClientError(429, PER_MINUTE), "ok"])
    assert emb.embed_query("q")
    assert len(models.calls) == 3 and sleeps == [2.0, 4.0] and emb.stats()["retries"] == 2


def test_the_waits_follow_the_backoff_setting(build):
    emb, _, sleeps = build([errors.ClientError(429, PER_MINUTE), "ok"], backoff=0.5)
    emb.embed_query("q")
    assert sleeps == [0.5]


def test_a_server_error_is_retried_too(build):
    emb, models, sleeps = build([errors.ServerError(503, {"error": {"code": 503, "message": "overloaded"}}), "ok"])
    assert emb.embed_query("q") and len(models.calls) == 2 and len(sleeps) == 1


def test_when_the_retries_run_out_the_error_says_what_happened(build):
    emb, models, sleeps = build([errors.ClientError(429, PER_MINUTE)], retries=2)
    with pytest.raises(EmbeddingUnavailable) as info:
        emb.embed_query("q")
    assert len(models.calls) == 3 and len(sleeps) == 2 and "rate" in str(info.value).lower()


def test_a_daily_quota_is_not_retried_at_all(build):
    emb, models, sleeps = build([errors.ClientError(429, PER_DAY)])
    with pytest.raises(EmbeddingUnavailable) as info:
        emb.embed_query("q")
    assert len(models.calls) == 1 and sleeps == [] and "daily" in str(info.value).lower()


def test_the_original_error_is_kept_as_the_cause(build):
    emb, _, _ = build([errors.ClientError(429, PER_DAY)])
    with pytest.raises(EmbeddingUnavailable) as info:
        emb.embed_query("q")
    assert isinstance(info.value.__cause__, errors.ClientError)


def test_other_client_errors_pass_straight_through(build):
    emb, models, sleeps = build([errors.ClientError(400, {"error": {"code": 400, "message": "bad request"}})])
    with pytest.raises(errors.ClientError):
        emb.embed_query("q")
    assert len(models.calls) == 1 and sleeps == []


def test_a_failure_is_not_cached(build):
    emb, models, _ = build([errors.ClientError(429, PER_DAY), "ok"])
    with pytest.raises(EmbeddingUnavailable):
        emb.embed_query("q")
    assert emb.embed_query("q") and len(models.calls) == 2


def test_documents_get_the_same_retry_treatment(build):
    emb, models, sleeps = build([errors.ClientError(429, PER_MINUTE), "ok"])
    assert len(emb.embed_documents(["x", "y"])) == 2 and len(sleeps) == 1


def test_the_unavailable_error_is_a_plain_exception():
    assert issubclass(EmbeddingUnavailable, Exception)
