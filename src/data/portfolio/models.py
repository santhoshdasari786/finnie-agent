from pydantic import BaseModel, Field
from src.data.market.models import Instrument

class Holding(BaseModel):
    instrument: Instrument
    quantity: float = Field(ge=0)
    avg_price: float | None = None
    asset_class: str | None = None          # equity | equity_fund | debt_fund | gold | cash ...
    current_price: float | None = None      # filled from a MarketDataProvider when the source has none
