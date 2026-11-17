from src.rag.common.models import RetrievalResult, RetrievedChunk
from src.rag.common.registry import register


@register("retriever", "vector")
class VectorRetriever:
    def __init__(self, embedder, store, post_processors=None,
                 fetch_multiplier=4, category_field="topic"):
        if fetch_multiplier < 1:
            raise ValueError("fetch_multiplier must be >= 1")
        self.embedder = embedder
        self.store = store
        self.post_processors = list(post_processors or [])
        self.fetch_multiplier = fetch_multiplier
        self.category_field = category_field

    def retrieve(self, q):
        vec = self.embedder.embed_query(q.text)

        filters = dict(q.filters or {})
        if q.category:
            filters[self.category_field] = q.category

        raw = self.store.search(vec, k=q.k * self.fetch_multiplier, filters=filters or None)
        hits = [self._to_chunk(h) for h in raw]

        for p in self.post_processors:
            hits = p.process(q, hits)
        hits = hits[:q.k]

        return RetrievalResult(
            status="ok" if hits else "no_source",
            chunks=hits,
            best_score=max((h.score for h in hits), default=None),
            query=q,
        )

    def _to_chunk(self, hit):
        m = hit.metadata
        return RetrievedChunk(
            chunk_id=hit.chunk_id,
            text=hit.text,
            score=hit.score,
            source=m.get("source", ""),
            title=m.get("title", ""),
            metadata=m,
        )
