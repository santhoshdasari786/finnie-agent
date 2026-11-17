import re
from src.rag.common.registry import register


def _shingles(text: str, n: int) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", text.lower())
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


@register("postprocessor", "dedupe")
class Deduplicator:
    def __init__(self, similarity=0.9, shingle_size=3):
        if not 0 < similarity <= 1:
            raise ValueError("similarity must be in (0, 1]")
        self.similarity = similarity
        self.shingle_size = shingle_size

    def process(self, query, hits):
        kept, kept_shingles = [], []
        for h in hits:                                   # hits arrive best-first
            sh = _shingles(h.text, self.shingle_size)
            if any(_jaccard(sh, other) >= self.similarity for other in kept_shingles):
                continue                                 # near-duplicate of a better hit
            kept.append(h)
            kept_shingles.append(sh)
        return kept
