from typing import Protocol
from src.data.market.models import Instrument, PriceHistory, Quote

class MarketDataProvider(Protocol):
    name: str
    async def quotes(self, instruments: list[Instrument]) -> list[Quote]: ...
    async def history(self, instrument: Instrument, range: str) -> PriceHistory | None: ...


class ProviderUnavailable(Exception):
    """The source is temporarily unreachable (rate limit, network, timeout). Trying again later may work.

    Not the same as "not found": an unknown symbol is an answer (None / no quote), never this."""


PROVIDERS: dict[str, type] = {}

def register_provider(name: str):
    def deco(cls):
        if name in PROVIDERS:
            raise ValueError(f"market provider '{name}' already registered")
        PROVIDERS[name] = cls
        return cls
    return deco
