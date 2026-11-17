import re
from dataclasses import dataclass

from src.data.news.models import NewsItem

_NOISE = re.compile(r"stock price,? news,? quote|quote (&|and) history|historical prices|stock quote|"
                    r"price prediction|target price|stocks? to buy|buy or sell|should you buy|multibagger|hot stock", re.I)
_SOCIAL = {"instagram", "facebook", "youtube", "x", "twitter", "reddit", "tiktok", "linkedin"}
_SUFFIX = re.compile(r"\s[-–|]\s[^-–|]{2,40}$")
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def is_noise(title: str, publisher: str = "") -> bool:
    """Aggregator pages, stock tips and predictions, and social media posts are not news."""
    return bool(_NOISE.search(title)) or publisher.strip().lower() in _SOCIAL


def normalize_title(title: str) -> str:
    return " ".join(_TOKEN.findall(_SUFFIX.sub("", title).lower()))


@dataclass(frozen=True)
class Cluster:
    members: tuple[NewsItem, ...]          # newest first

    @property
    def lead(self) -> NewsItem:
        return self.members[0]

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def publishers(self) -> list[str]:
        return list(dict.fromkeys(m.publisher for m in self.members))


def _similarity(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def cluster_items(items: list[NewsItem], threshold: float = 0.6) -> list[Cluster]:
    """Group near-duplicate headlines (same story, different outlet or wording). Newest cluster first."""
    groups: list[list[NewsItem]] = []
    keys: list[set[str]] = []
    for it in sorted(items, key=lambda i: i.published_at, reverse=True):
        tokens = set(normalize_title(it.title).split())
        for group, key in zip(groups, keys):
            if _similarity(tokens, key) >= threshold:
                group.append(it)
                break
        else:
            groups.append([it])
            keys.append(tokens)
    return [Cluster(tuple(g)) for g in groups]
