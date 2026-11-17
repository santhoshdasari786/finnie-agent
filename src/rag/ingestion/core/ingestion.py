import logging
from functools import reduce
from src.rag.common.models import EmbeddedChunk

log = logging.getLogger(__name__)

class IngestionPipeline:
    def __init__(self, loaders, cleaners, chunker, embedder, store, manifest,
                 batch_size=64, on_error="skip_and_log"):
        self.loaders, self.cleaners, self.chunker = loaders, cleaners, chunker
        self.embedder, self.store, self.manifest = embedder, store, manifest
        self.batch_size = min(batch_size, embedder.max_batch_size)
        self.on_error = on_error

    def run(self) -> dict:
        self.store.ensure_collection()
        stats = {"seen": 0, "skipped": 0, "ingested": 0, "chunks": 0, "failed": 0}
        model_id = self.embedder.model_id

        for loader in self.loaders:
            for doc in loader.load():
                stats["seen"] += 1
                doc = reduce(lambda d, c: c.clean(d), self.cleaners, doc)

                if self.manifest.get_hash(doc.id, model_id) == doc.content_hash:
                    stats["skipped"] += 1
                    continue
                try:
                    n = self._ingest_doc(doc)
                except Exception:
                    log.exception("Failed on %s", doc.id)
                    stats["failed"] += 1
                    if self.on_error == "fail_fast":
                        raise
                    continue
                stats["ingested"] += 1
                stats["chunks"] += n
        return stats

    def _ingest_doc(self, doc) -> int:
        chunks = self.chunker.chunk(doc)
        embedded = []
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            vectors = self.embedder.embed_documents(
                [c.text for c in batch], [c.metadata.get("title") for c in batch])
            assert len(vectors) == len(batch), "embedder returned wrong number of vectors"
            embedded += [EmbeddedChunk(c, v) for c, v in zip(batch, vectors)]

        self.store.delete_by_doc(doc.id)       # replace stale chunks
        self.store.upsert(embedded)
        self.manifest.record(doc.id, doc.content_hash, self.embedder.model_id, len(chunks))  # last
        return len(chunks)
