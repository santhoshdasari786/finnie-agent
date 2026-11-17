import asyncio
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from src.data.news.base import NewsError, register_news_provider
from src.data.news.models import NewsItem


def _http_get(url: str, timeout: float = 12) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (finnie)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


@register_news_provider("google_news")
class GoogleNewsProvider:
    name = "Google News"

    def __init__(self, fetch=None):
        self._fetch = fetch or _http_get

    @staticmethod
    def _url(query: str, days: int) -> str:
        params = {"q": f"{query} when:{days}d", "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)

    async def search(self, query: str, days: int, limit: int) -> list[NewsItem]:
        if not query.strip():
            raise ValueError("query must not be blank")
        try:
            raw = await asyncio.to_thread(self._fetch, self._url(query.strip(), days))
        except Exception as e:
            raise NewsError(f"could not fetch news: {type(e).__name__}") from e
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            raise NewsError("the news feed was not readable") from e
        items: list[NewsItem] = []
        for node in root.iter("item"):
            title = re.sub(r"[\u200b-\u200d\ufeff]", "", html.unescape(node.findtext("title") or "")).strip()
            link = (node.findtext("link") or "").strip()
            date = (node.findtext("pubDate") or "").strip()
            if not (title and link and date):
                continue
            try:
                published = parsedate_to_datetime(date)
            except (TypeError, ValueError):
                continue
            publisher = (node.findtext("source") or "").strip()
            if publisher and title.endswith(f" - {publisher}"):
                title = title[: -len(publisher) - 3].rstrip()
            elif not publisher and " - " in title:
                title, _, publisher = title.rpartition(" - ")
            items.append(NewsItem(title=title, publisher=publisher or "Unknown", url=link, published_at=published))
            if len(items) >= limit:
                break
        return items
