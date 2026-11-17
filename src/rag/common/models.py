# core/models.py
from dataclasses import dataclass
from typing import Literal

from src.common.models import QASettings

from src.core.contracts import Citation   # canonical home; re-exported so existing imports keep working


@dataclass(frozen=True)
class Document:
    id: str                    # stable: hash of source path/URL
    text: str
    metadata: dict
    content_hash: str          # for change detection

@dataclass(frozen=True)
class Chunk:
    id: str                    # f"{doc.id}:{index}:{chunk_hash[:8]}"
    doc_id: str
    text: str
    metadata: dict             # source, title, section, position, ...

@dataclass
class EmbeddedChunk:
    chunk: Chunk
    vector: list[float]

@dataclass(frozen=True)
class CollectionInfo:
    name: str
    dimensions: int
    model_id: str
    count: int

@dataclass(frozen=True)
class SearchHit:
    chunk_id: str
    text: str
    score: float
    metadata: dict

# RETRIVAL



@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    category: str | None = None        # from QARequest.category_hint
    k: int = 5
    filters: dict | None = None        # escape hatch for other metadata

@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float                       # similarity, 0..1 (higher is better)
    source: str                        # file path or URL
    title: str
    metadata: dict

@dataclass(frozen=True)
class RetrievalResult:
    status: Literal["ok", "no_source"]
    chunks: list[RetrievedChunk]       # empty when no_source
    best_score: float | None           # useful for logging and tuning
    query: RetrievalQuery


# common/models.py
@dataclass(frozen=True)
class GlossaryEntry:
    term: str
    definition: str
    sense: str | None = None
    aliases: tuple[str, ...] = ()
    topic: str | None = None
    source_urls: tuple[str, ...] = ()
    related_articles: tuple[str, ...] = ()

@dataclass(frozen=True)
class GlossaryMatch:
    entries: list[GlossaryEntry]                      # >1 means ambiguous
    match_type: Literal["exact", "alias", "fuzzy"]
    matched_text: str

    @property
    def ambiguous(self) -> bool:
        return len(self.entries) > 1



@dataclass
class Rag:
    retriever: object
    glossary: object
    settings: QASettings

@dataclass(frozen=True)
class ContextSource:
    n: int                 # the [n] number shown to the LLM
    title: str
    text: str
    citation: Citation
    verified: str | None = None   # last_verified_at, if known
    risk_level: str | None = None
