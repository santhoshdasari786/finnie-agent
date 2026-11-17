import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.rag.common.models import Chunk
from src.rag.common.registry import register

def flatten_metadata(meta: dict) -> dict:
    """Chroma accepts only str/int/float/bool. Drop None, join lists, skip dicts."""
    out = {}
    for k, v in meta.items():
        if v is None or isinstance(v, dict):
            continue
        out[k] = ", ".join(map(str, v)) if isinstance(v, list) else v
    return out

@register("chunker", "recursive")
class RecursiveChunker:
    def __init__(self, chunk_size=800, chunk_overlap=100):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
        )

    def chunk(self, doc):
        base = flatten_metadata(doc.metadata)
        out = []
        for i, text in enumerate(self._splitter.split_text(doc.text)):
            h = hashlib.sha1(text.encode()).hexdigest()[:8]
            out.append(Chunk(
                id=f"{doc.id}:{i}:{h}", doc_id=doc.id, text=text,
                metadata={**base, "doc_id": doc.id, "chunk_index": i, "chunker": "recursive"},
            ))
        return out
