from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel

class Instrument(BaseModel, frozen=True):
    symbol: str                                   # canonical: "RELIANCE", "NIFTY50"
    exchange: Literal["NSE", "BSE", "US", "INDEX", "MF"] = "NSE"


class Quote(BaseModel):
    instrument: Instrument
    price: float
    change_pct: float | None = None
    currency: str
    as_of: datetime
    source: str                                   # "yfinance"; agents must show this
    stale: bool = False

class PricePoint(BaseModel):
    date: date
    close: float


class PriceHistory(BaseModel):
    instrument: Instrument
    range: str                                    # "1m" | "3m" | "6m" | "1y"
    currency: str
    points: list[PricePoint]                      # oldest first, one per trading day
    as_of: datetime
    source: str
    stale: bool = False                           # an older copy, served because a refresh failed
