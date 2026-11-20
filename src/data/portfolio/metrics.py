from collections import defaultdict
from typing import Literal
from pydantic import BaseModel
from src.data.portfolio.models import Holding

EQUITY_LIKE = {"equity", "equity_fund"}
FUND_CLASSES = {"equity_fund", "debt_fund"}               # holdings that have an expense ratio to know
LEVELS = ["conservative", "moderate", "aggressive"]       # an index into this list IS the risk level

class HoldingMetric(BaseModel):
    symbol: str
    quantity: float
    price: float
    value: float
    allocation_pct: float
    pnl_pct: float | None = None
    expense_ratio_pct: float | None = None

class PortfolioMetrics(BaseModel):
    total_value: float
    holdings: list[HoldingMetric]
    by_asset_class: dict[str, float]
    top_holding_pct: float
    diversification_score: float
    risk_assessment: Literal["conservative", "moderate", "aggressive"]
    unpriced: list[str] = []
    unclassified: list[str] = []
    weighted_expense_ratio_pct: float | None = None     # over the holdings whose ratio is known
    annual_fund_cost: float | None = None               # rupees a year, same holdings
    expense_covered_pct: float | None = None            # share of the portfolio's value where the ratio is known
    expense_unknown: list[str] = []                     # funds whose ratio is not known, biggest first

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
        if m.expense_ratio_pct is None:
            m.expense_ratio_pct = x.expense_ratio_pct
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
                                  value=round(v, 2), allocation_pct=round(v / total * 100, 2), pnl_pct=pnl,
                                  expense_ratio_pct=x.expense_ratio_pct))
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

    known = [(v, x.expense_ratio_pct) for x, v in zip(priced, values) if x.expense_ratio_pct is not None]
    cost = sum(v * r / 100 for v, r in known)
    known_value = sum(v for v, _ in known)
    unknown = sorted(((v, x.instrument.symbol) for x, v in zip(priced, values)
                      if x.expense_ratio_pct is None and x.asset_class in FUND_CLASSES), reverse=True)

    return PortfolioMetrics(
        total_value=round(total, 2), holdings=rows,
        by_asset_class={k: round(v / total * 100, 2) for k, v in by_class.items()},
        top_holding_pct=round(top, 2),
        diversification_score=round(1 - sum((v / total) ** 2 for v in values), 4),
        risk_assessment=LEVELS[level], unpriced=unpriced,
        unclassified=[x.instrument.symbol for x in priced if x.asset_class is None],
        weighted_expense_ratio_pct=round(cost / known_value * 100, 2) if known_value else None,
        annual_fund_cost=round(cost, 2) if known else None,
        expense_covered_pct=round(known_value / total * 100, 2) if known else None,
        expense_unknown=[sym for _, sym in unknown])
