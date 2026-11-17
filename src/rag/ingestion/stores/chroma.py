import re
import chromadb
from src.rag.common.models import CollectionInfo, SearchHit
from src.rag.common.registry import register

def _slug(s): return re.sub(r"[^a-zA-Z0-9._-]", "-", s)

@register("vector_store", "chroma")
class ChromaStore:
    def __init__(self, collection, path, model_id, dimensions):
        self.model_id, self.dimensions = model_id, dimensions
        self.name = f"{collection}__{_slug(model_id)}__{dimensions}"
        self._client = chromadb.PersistentClient(path=path)
        self._col = None

    def ensure_collection(self):
        self._col = self._client.get_or_create_collection(
            self.name, metadata={"hnsw:space": "cosine",
                                 "model_id": self.model_id, "dimensions": self.dimensions})

    def info(self):
        return CollectionInfo(self.name, self.dimensions, self.model_id, self._col.count())

    def upsert(self, items):
        self._col.upsert(
            ids=[i.chunk.id for i in items],
            embeddings=[i.vector for i in items],
            documents=[i.chunk.text for i in items],
            metadatas=[i.chunk.metadata for i in items],
        )

    def delete_by_doc(self, doc_id):
        self._col.delete(where={"doc_id": doc_id})

    def search(self, vector, k, filters=None):
        r = self._col.query(query_embeddings=[vector], n_results=k, where=self._to_where(filters))
        return [SearchHit(i, d, 1 - dist, m) for i, d, dist, m in
                zip(r["ids"][0], r["documents"][0], r["distances"][0], r["metadatas"][0])]

    @staticmethod
    def _to_where(filters):
        """Chroma wants exactly one operator: one filter as is, several joined with $and, none as no clause."""
        if not filters:
            return None
        if len(filters) == 1:
            return filters
        return {"$and": [{k: v} for k, v in filters.items()]}
