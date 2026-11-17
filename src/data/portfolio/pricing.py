from datetime import datetime
from pydantic import BaseModel
from src.data.market.base import MarketDataProvider
from src.data.market.models import Instrument, Quote
from src.data.portfolio.models import Holding


class PricingResult(BaseModel):
    holdings: list[Holding]
    as_of: datetime | None = None          # oldest quote time used; None = nothing was fetched
    sources: list[str] = []                # which providers answered, e.g. ["yfinance"]
    unquoted: list[str] = []               # symbols the provider had no price for


def _fill(h: Holding, quotes: dict[Instrument, Quote]) -> Holding:
    """A copy of `h`, priced from `quotes` only if it had no price of its own."""
    q = None if h.current_price else quotes.get(h.instrument)
    return h.model_copy(update={"current_price": q.price} if q else {})


async def price_holdings(holdings: list[Holding], provider: MarketDataProvider) -> PricingResult:
    """Fill missing prices from `provider`. Existing prices are kept; unknown prices stay unknown."""
    need = list(dict.fromkeys(h.instrument for h in holdings if not h.current_price))   # unique, in order
    quotes = {q.instrument: q for q in await provider.quotes(need)} if need else {}
    used = [quotes[i] for i in need if i in quotes]
    return PricingResult(
        holdings=[_fill(h, quotes) for h in holdings],
        as_of=min((q.as_of for q in used), default=None),
        sources=sorted({q.source for q in used}),
        unquoted=[i.symbol for i in need if i not in quotes])
