from typing import Literal, Protocol
from pydantic import BaseModel
from src.data.portfolio.models import Holding

SourceStatus = Literal["connected", "needs_login", "available"]

class ConnectInfo(BaseModel):
    connected: bool
    message: str                       # what to tell the user next
    login_url: str | None = None       # set when the user must log in somewhere

class PortfolioSource(Protocol):
    name: str                          # registry key, e.g. "kite"
    label: str                         # shown in the menu, e.g. "Zerodha (live account)"
    async def status(self) -> SourceStatus: ...
    async def connect(self, **params) -> ConnectInfo: ...
    async def holdings(self) -> list[Holding]: ...

SOURCES: dict[str, type] = {}

def register_source(name: str):
    def deco(cls):
        if name in SOURCES:
            raise ValueError(f"portfolio source '{name}' already registered")
        SOURCES[name] = cls
        return cls
    return deco


class SessionExpired(Exception):
    """A live source lost its session (or never had one). The caller should ask the user to log in again."""
    def __init__(self, source: str):
        super().__init__(f"{source} session expired")
        self.source = source
