from src.rag.common.registry import register

@register("postprocessor", "per_doc_cap")
class PerDocCap:
    def __init__(self, max_per_doc):
        self.max_per_doc = max_per_doc

    def process(self, query, hits):
        seen, out = {}, []
        for h in hits:                      # hits arrive best-first
            key = h.metadata.get("doc_id", h.chunk_id)
            if seen.get(key, 0) < self.max_per_doc:
                seen[key] = seen.get(key, 0) + 1
                out.append(h)
        return out
