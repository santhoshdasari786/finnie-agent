import hashlib
from pathlib import Path
import yaml
from src.rag.common.models import Document
from src.rag.common.registry import register

def _split_front_matter(raw: str) -> tuple[dict, str]:
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        return (yaml.safe_load(fm) or {}), body.strip()
    return {}, raw.strip()

@register("loader", "markdown")
class MarkdownLoader:
    def __init__(self, path, glob="**/*.md"):
        self.root, self.glob = Path(path), glob

    def load(self):
        for p in sorted(self.root.glob(self.glob)):
            meta, body = _split_front_matter(p.read_text(encoding="utf-8"))
            doc_id = meta.get("article_id") or str(p.relative_to(self.root))
            meta.setdefault("title", p.stem.replace("-", " ").title())
            meta["source"] = str(p)
            yield Document(
                id=doc_id, text=body, metadata=meta,
                content_hash=hashlib.sha256(body.encode()).hexdigest(),
            )
