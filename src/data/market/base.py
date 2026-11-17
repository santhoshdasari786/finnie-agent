from typing import Protocol
from src.data.market.models import Instrument, Quote

class MarketDataProvider(Protocol):
    name: str
    async def quotes(self, instruments: list[Instrument]) -> list[Quote]: ...

PROVIDERS: dict[str, type] = {}

def register_provider(name: str):
    def deco(cls):
        if name in PROVIDERS:
            raise ValueError(f"market provider '{name}' already registered")
        PROVIDERS[name] = cls
        return cls
    return deco
