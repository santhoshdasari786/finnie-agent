

from src.rag.common.interfaces import Embedder
from src.rag.common.registry import register


@register("chunker", "semantic")
class SemanticChunker:
    def __init__(self, embedder: Embedder, breakpoint_percentile=95, min_chars=300, max_chars=1500): ...
