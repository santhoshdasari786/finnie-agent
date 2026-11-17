from collections import defaultdict
from difflib import get_close_matches
from pathlib import Path
import yaml

from src.rag.common.models import GlossaryEntry, GlossaryMatch
from src.rag.common.registry import register
from src.rag.glossary.matching import extract_candidate, normalize


@register("glossary", "yaml")
class YamlGlossary:
    def __init__(self, path, fuzzy_cutoff=0.0):
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Glossary file not found: {p.resolve()}")
        self.fuzzy_cutoff = fuzzy_cutoff
        self._by_key: dict[str, list[GlossaryEntry]] = defaultdict(list)
        self._alias_keys: set[str] = set()
        for raw in yaml.safe_load(p.read_text(encoding="utf-8")) or []:
            self._add(raw)

    def _add(self, raw):
        entry = GlossaryEntry(
            term=raw["term"], definition=" ".join(raw["definition"].split()),
            sense=raw.get("sense"), aliases=tuple(raw.get("aliases", [])),
            topic=raw.get("topic"), source_urls=tuple(raw.get("source_urls", [])),
            related_articles=tuple(raw.get("related_articles", [])),
        )
        self._by_key[normalize(entry.term)].append(entry)
        for a in entry.aliases:
            key = normalize(a)
            self._alias_keys.add(key)
            if entry not in self._by_key[key]:
                self._by_key[key].append(entry)

    def lookup(self, question):
        cand = extract_candidate(question)
        if cand is None:
            return None
        for key, kind in ((cand, None), (self._singular(cand), None)):
            if key in self._by_key:
                kind = "alias" if key in self._alias_keys else "exact"
                return GlossaryMatch(self._by_key[key], kind, cand)
        if self.fuzzy_cutoff > 0:
            close = get_close_matches(cand, self._by_key, n=1, cutoff=self.fuzzy_cutoff)
            if close:
                return GlossaryMatch(self._by_key[close[0]], "fuzzy", cand)
        return None

    @staticmethod
    def _singular(s):
        return s[:-1] if s.endswith("s") and len(s) > 3 else s
