from datetime import datetime
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
