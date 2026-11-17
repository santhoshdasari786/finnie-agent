from typing import Protocol

from src.data.news.models import NewsItem


class NewsError(Exception):
    """The news source failed or answered with something unreadable."""


class NewsProvider(Protocol):
    name: str

    async def search(self, query: str, days: int, limit: int) -> list[NewsItem]: ...


NEWS_PROVIDERS: dict[str, type] = {}


def register_news_provider(name: str):
    def deco(cls):
        if name in NEWS_PROVIDERS:
            raise ValueError(f"news provider '{name}' already registered")
        NEWS_PROVIDERS[name] = cls
        return cls
    return deco
