from datetime import datetime

from pydantic import BaseModel


class NewsItem(BaseModel):
    title: str
    publisher: str
    url: str
    published_at: datetime       # timezone-aware, UTC
