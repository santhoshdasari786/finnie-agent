import logging
import os
import time
from collections import OrderedDict

from google import genai
from google.genai import errors, types

from src.rag.common.registry import register

log = logging.getLogger(__name__)


class EmbeddingUnavailable(Exception):
    """The embedding service cannot be used right now: the daily quota is gone, or rate limits did not clear after retries."""


@register("embedder", "gemini")
class GeminiEmbedder:
    max_batch_size = 100          # verify against the current API limit

    def __init__(self, model, output_dimensionality, api_key_env,
                 document_prefix="title: {title} | text: {text}",
                 query_prefix="task: search result | query: {text}",
                 retries=5, backoff=2.0, cache_size=256, sleep=time.sleep,
                 requests_per_minute=90, clock=time.monotonic):
        self.model_id, self.dimensions = model, output_dimensionality
        self._doc_fmt, self._query_fmt = document_prefix, query_prefix
        self._client = genai.Client(api_key=os.environ[api_key_env])
        self._retries, self._backoff, self._sleep = retries, backoff, sleep
        self._cache_size = cache_size
        self._rpm, self._clock = requests_per_minute, clock
        self._sent: list[tuple[float, int]] = []                    # (time, texts) of calls in the last minute
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._counts = {"requests": 0, "cache_hits": 0, "retries": 0}

    def stats(self) -> dict:
        return {**self._counts, "cached_queries": len(self._cache)}

    def _throttle(self, n):
        """Each text counts as one request against the per-minute quota, so a batch of 64 uses most of a minute.
        Wait until the last 60 seconds leave room for n more, instead of sending and being refused."""
        n = min(n, self._rpm)
        while True:
            now = self._clock()
            self._sent = [(t, c) for t, c in self._sent if now - t < 60]
            if sum(c for _, c in self._sent) + n <= self._rpm:
                self._sent.append((now, n))
                return
            wait = 60 - (now - self._sent[0][0])
            log.info("embedding quota window full; waiting %.0fs", wait)
            self._sleep(max(wait, 0.1))

    def _embed(self, texts):
        """One API call, retried when the service is rate limiting or briefly down. A per-DAY quota is not retried:
        waiting a few seconds cannot help, so the caller gets a clear error at once."""
        for attempt in range(self._retries + 1):
            self._throttle(len(texts))
            self._counts["requests"] += 1
            try:
                resp = self._client.models.embed_content(
                    model=self.model_id,
                    contents=[types.Content(parts=[types.Part(text=t)]) for t in texts],
                    config=types.EmbedContentConfig(output_dimensionality=self.dimensions))
                return [list(e.values) for e in resp.embeddings]
            except (errors.ClientError, errors.ServerError) as e:
                rate_limited = isinstance(e, errors.ClientError) and e.code == 429
                if isinstance(e, errors.ClientError) and not rate_limited:
                    raise                                           # a bad request is a bug, not a wait
                if rate_limited and "PerDay" in str(e):
                    raise EmbeddingUnavailable("The daily embedding quota is used up.") from e
                if attempt == self._retries:
                    raise EmbeddingUnavailable("The embedding service is rate limited or unavailable right now.") from e
                self._counts["retries"] += 1
                wait = self._backoff * 2 ** attempt
                log.warning("embedding call failed (%s); retrying in %.1fs", getattr(e, "code", "?"), wait)
                self._sleep(wait)
        raise AssertionError("unreachable")                         # the loop always returns or raises

    def embed_documents(self, texts, titles=None):
        titles = titles or [None] * len(texts)
        return self._embed([self._doc_fmt.format(title=t or "none", text=x)
                            for t, x in zip(titles, texts)])

    def embed_query(self, text):
        if text in self._cache:
            self._cache.move_to_end(text)
            self._counts["cache_hits"] += 1
            return list(self._cache[text])                          # a copy: callers may change it
        vector = self._embed([self._query_fmt.format(text=text)])[0]
        self._cache[text] = list(vector)
        while len(self._cache) > self._cache_size:                  # a size of 0 evicts at once: no cache
            self._cache.popitem(last=False)
        return vector
