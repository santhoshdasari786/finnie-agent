from collections import defaultdict
from typing import Literal
from pydantic import BaseModel
from src.data.portfolio.models import Holding

EQUITY_LIKE = {"equity", "equity_fund"}
LEVELS = ["conservative", "moderate", "aggressive"]       # an index into this list IS the risk level

class HoldingMetric(BaseModel):
    symbol: str
    quantity: float
    price: float
    value: float
    allocation_pct: float
    pnl_pct: float | None = None

class PortfolioMetrics(BaseModel):
    total_value: float
    holdings: list[HoldingMetric]
    by_asset_class: dict[str, float]
    top_holding_pct: float
    diversification_score: float
    risk_assessment: Literal["conservative", "moderate", "aggressive"]
    unpriced: list[str] = []
    unclassified: list[str] = []

def _merge(holdings: list[Holding]) -> list[Holding]:
    merged: dict[str, Holding] = {}
    for x in holdings:
        key = x.instrument.symbol
        if key not in merged:
            merged[key] = x.model_copy()            # a copy, so the caller's objects are never mutated
            continue
        m = merged[key]
        total_qty = m.quantity + x.quantity
        if m.avg_price is not None and x.avg_price is not None and total_qty:
            m.avg_price = (m.avg_price * m.quantity + x.avg_price * x.quantity) / total_qty   # weighted average
        else:
            m.avg_price = None                       # can't average with an unknown, so don't pretend
        m.quantity = total_qty
    return list(merged.values())


def compute_portfolio_metrics(holdings: list[Holding]) -> PortfolioMetrics:
    merged = _merge(holdings)
    priced = [x for x in merged if x.current_price]              # None and 0 are both "no price"
    unpriced = [x.instrument.symbol for x in merged if not x.current_price]
    if not priced:
        raise ValueError("no priced holdings")
    values = [x.quantity * x.current_price for x in priced]
    total = sum(values)

    rows = []
    for x, v in zip(priced, values):
        pnl = round((x.current_price - x.avg_price) / x.avg_price * 100, 2) if x.avg_price else None
        rows.append(HoldingMetric(symbol=x.instrument.symbol, quantity=x.quantity, price=x.current_price,
                                  value=round(v, 2), allocation_pct=round(v / total * 100, 2), pnl_pct=pnl))
    rows.sort(key=lambda r: r.value, reverse=True)

    by_class: dict[str, float] = defaultdict(float)
    equity_like = 0.0
    for x, v in zip(priced, values):
        by_class[x.asset_class or "unclassified"] += v
        if x.asset_class is None or x.asset_class in EQUITY_LIKE:      # unknown is assumed risky
            equity_like += v
    equity_pct = equity_like / total * 100
    top = max(values) / total * 100
    level = 2 if equity_pct >= 70 else 1 if equity_pct >= 40 else 0
    if top >= 50:
        level = min(level + 1, 2)                                     # concentration bump, capped

    return PortfolioMetrics(
        total_value=round(total, 2), holdings=rows,
        by_asset_class={k: round(v / total * 100, 2) for k, v in by_class.items()},
        top_holding_pct=round(top, 2),
        diversification_score=round(1 - sum((v / total) ** 2 for v in values), 4),
        risk_assessment=LEVELS[level], unpriced=unpriced,
        unclassified=[x.instrument.symbol for x in priced if x.asset_class is None])
