# src/rag/retrieval/citations.py
import re
from src.core.contracts import Citation

def primary_url(meta: dict) -> str:
    """Best user-facing reference. source_urls was flattened to 'a, b, c' at ingestion."""
    urls = meta.get("source_urls") or ""
    first = urls.split(", ")[0].strip() if urls else ""
    return first or meta.get("title", "") or meta.get("source", "")

def make_excerpt(text: str, max_chars: int = 200) -> str:
    t = re.sub(r"^#+\s*", "", text, flags=re.M)        # drop markdown heading marks
    t = re.sub(r"[*_`>]+", "", t)                       # drop emphasis / quote marks
    t = " ".join(t.split())
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if end >= max_chars * 0.5:                          # prefer ending on a sentence
        return cut[:end + 1]
    return cut.rsplit(" ", 1)[0] + "…"

def cite_chunk(chunk) -> Citation:
    m = chunk.metadata
    return Citation(source=primary_url(m), title=chunk.title,
                    excerpt=make_excerpt(chunk.text), verified_at=m.get("last_verified_at"))

def cite_glossary(entry) -> Citation:
    src = entry.source_urls[0] if entry.source_urls else entry.term
    return Citation(source=src, title=entry.term, excerpt=make_excerpt(entry.definition))

def merge_by_source(citations: list[Citation]) -> list[Citation]:
    """Two cited chunks from one article should show as one reference."""
    seen, out = set(), []
    for c in citations:
        if c.source not in seen:
            seen.add(c.source)
            out.append(c)
    return out

_MARKER = re.compile(r"\[([\d,\s]+)\]")
_MARKER_WITH_SPACE = re.compile(r"(\s?)\[([\d,\s]+)\]")


def used_markers(answer: str, valid: set[int]) -> list[int]:
    """[1] and [1, 2] both occur in LLM output. Return valid numbers in first-use order."""
    order = []
    for group in _MARKER.findall(answer):
        for n in (int(x) for x in group.split(",") if x.strip()):
            if n in valid and n not in order:
                order.append(n)
    return order

def renumber_markers(text: str, used: list[int], sources_by_n: dict) -> str:
    """Rewrite [n] markers to match the merged citation list (1-based, one per distinct source)."""
    urls, pos = [], {}
    for n in used:
        u = sources_by_n[n].citation.source
        if u not in urls:
            urls.append(u)
        pos[n] = urls.index(u) + 1

    # def sub(m):
    #     nums = [int(x) for x in m.group(1).split(",") if x.strip()]
    #     mapped = sorted({pos[n] for n in nums if n in pos})
    #     return "".join(f"[{p}]" for p in mapped)       # unknown markers like [9] vanish

    def sub(m):
        nums = [int(x) for x in m.group(2).split(",") if x.strip()]      # group 2 now (was group 1)
        mapped = sorted({pos[n] for n in nums if n in pos})
        if not mapped:
            return ""                                                    # invented marker: drop it AND its space
        return m.group(1) + "".join(f"[{p}]" for p in mapped)           # real marker: keep its space

    # return _MARKER.sub(sub, text)
    out = _MARKER_WITH_SPACE.sub(sub, text)
    return re.sub(r"(\[\d+\])(?:\1)+", r"\1", out)       # [1][1] -> [1]

