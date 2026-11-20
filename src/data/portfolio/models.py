from pydantic import BaseModel, Field
from src.data.market.models import Instrument

class Holding(BaseModel):
    instrument: Instrument
    quantity: float = Field(ge=0)
    avg_price: float | None = None
    asset_class: str | None = None          # equity | equity_fund | debt_fund | gold | cash ...
    current_price: float | None = None      # filled from a MarketDataProvider when the source has none
    expense_ratio_pct: float | None = Field(default=None, ge=0, le=10)   # yearly fund cost in percent; None = not known (never guessed)
