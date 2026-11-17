"""compute_portfolio_metrics: pure Python, golden numbers. The LLM never does this arithmetic.

Run:  .venv/bin/python -m pytest tests/data/portfolio_metrics_test.py -v
Rules pinned here:
  * value = quantity * current_price; allocation_pct = value / total * 100 (2 dp)
  * diversification_score = 1 - sum(weight^2)   (1 - Herfindahl index; 0 = one holding, ->1 = well spread)
  * holdings with no price are EXCLUDED from the maths and listed in `unpriced` (never guessed)
  * risk bucket from the equity-like share: >=70 aggressive, >=40 moderate, else conservative;
    one holding >= 50% bumps the bucket up one level (concentration)
"""
import pytest

from src.data.market.models import Instrument
from src.data.portfolio.metrics import compute_portfolio_metrics
from src.data.portfolio.models import Holding


def h(symbol, qty, price, asset_class="equity", avg=None):
    return Holding(instrument=Instrument(symbol=symbol), quantity=qty, current_price=price,
                   avg_price=avg, asset_class=asset_class)


# ---------------------------------------------------------------- totals and allocation
def test_total_value_is_the_sum_of_quantity_times_price():
    m = compute_portfolio_metrics([h("TCS", 10, 2500), h("INFY", 20, 1500)])
    assert m.total_value == 55000.0

def test_allocation_percentages_and_sort_order():
    m = compute_portfolio_metrics([h("INFY", 20, 1500), h("TCS", 10, 2500)])       # 30000 and 25000
    assert [x.symbol for x in m.holdings] == ["INFY", "TCS"]                       # biggest first
    assert [x.allocation_pct for x in m.holdings] == [54.55, 45.45]

def test_allocations_sum_to_about_100():
    m = compute_portfolio_metrics([h("A", 1, 1), h("B", 1, 2), h("C", 1, 4)])
    assert sum(x.allocation_pct for x in m.holdings) == pytest.approx(100, abs=0.05)

def test_holding_metric_carries_value_and_price():
    [x] = compute_portfolio_metrics([h("TCS", 10, 2500)]).holdings
    assert (x.symbol, x.quantity, x.price, x.value) == ("TCS", 10, 2500, 25000)

def test_top_holding_pct():
    assert compute_portfolio_metrics([h("A", 1, 75), h("B", 1, 25)]).top_holding_pct == 75.0


# ---------------------------------------------------------------- diversification (1 - HHI)
@pytest.mark.parametrize("n, expected", [(1, 0.0), (2, 0.5), (4, 0.75)])
def test_equal_weights_diversification(n, expected):
    m = compute_portfolio_metrics([h(f"S{i}", 1, 100) for i in range(n)])
    assert m.diversification_score == expected

def test_concentrated_portfolio_scores_lower_than_balanced():
    skewed = compute_portfolio_metrics([h("A", 1, 90), h("B", 1, 10)])
    balanced = compute_portfolio_metrics([h("A", 1, 50), h("B", 1, 50)])
    assert skewed.diversification_score < balanced.diversification_score
    assert skewed.diversification_score == 0.18             # 1 - (0.81 + 0.01)


# ---------------------------------------------------------------- profit and loss
def test_pnl_pct_from_average_price():
    [x] = compute_portfolio_metrics([h("TCS", 10, 2500, avg=2000)]).holdings
    assert x.pnl_pct == 25.0

def test_pnl_is_none_without_an_average_price():
    [x] = compute_portfolio_metrics([h("TCS", 10, 2500)]).holdings
    assert x.pnl_pct is None


# ---------------------------------------------------------------- asset classes and risk
def test_allocation_by_asset_class():
    m = compute_portfolio_metrics([h("A", 1, 60, "equity"), h("B", 1, 30, "debt_fund"), h("C", 1, 10, "gold")])
    assert m.by_asset_class == {"equity": 60.0, "debt_fund": 30.0, "gold": 10.0}

@pytest.mark.parametrize("equity, other, bucket", [
    (80, 20, "aggressive"), (70, 30, "aggressive"),            # boundary: >=70
    (69, 31, "moderate"),   (40, 60, "moderate"),              # boundary: >=40
    (39, 61, "conservative"), (0, 100, "conservative"),
])
def test_risk_bucket_from_equity_share(equity, other, bucket):
    # spread both sides so no single holding reaches 50% (that would trigger the concentration bump)
    parts = [h(f"E{i}", 1, equity / 3) for i in range(3)] if equity else []
    parts += [h(f"D{i}", 1, other / 4, "debt_fund") for i in range(4)]
    assert compute_portfolio_metrics(parts).risk_assessment == bucket

def test_equity_funds_count_as_equity_like():
    m = compute_portfolio_metrics([h("F1", 1, 50, "equity_fund"), h("F2", 1, 50, "equity_fund")])
    assert m.risk_assessment == "aggressive"

def test_unclassified_holdings_are_assumed_risky_and_listed():
    m = compute_portfolio_metrics([h("A", 1, 50, None), h("B", 1, 50, None)])
    assert m.risk_assessment == "aggressive" and m.unclassified == ["A", "B"]

def test_one_big_holding_bumps_the_bucket_up_one_level():
    # 30% equity would be 'conservative', but one 60% debt holding is >= 50% -> moderate
    m = compute_portfolio_metrics([h("D", 1, 60, "debt_fund"), h("E", 1, 30, "equity"), h("G", 1, 10, "gold")])
    assert m.top_holding_pct == 60.0 and m.risk_assessment == "moderate"

def test_concentration_boundary_is_exactly_fifty_percent():
    at = compute_portfolio_metrics([h("D", 1, 50, "debt_fund"), h("E", 1, 25, "equity"), h("G", 1, 25, "gold")])
    below = compute_portfolio_metrics([h("D", 1, 49, "debt_fund"), h("E", 1, 26, "equity"), h("G", 1, 25, "gold")])
    assert at.risk_assessment == "moderate" and below.risk_assessment == "conservative"

def test_concentration_bump_is_capped_at_aggressive():
    assert compute_portfolio_metrics([h("A", 1, 90), h("B", 1, 10)]).risk_assessment == "aggressive"


# ---------------------------------------------------------------- missing prices are never guessed
def test_unpriced_holdings_are_excluded_and_listed():
    m = compute_portfolio_metrics([h("TCS", 10, 2500), h("MYSTERY", 5, None)])
    assert m.total_value == 25000.0 and m.unpriced == ["MYSTERY"] and [x.symbol for x in m.holdings] == ["TCS"]

def test_zero_price_counts_as_unpriced():
    assert compute_portfolio_metrics([h("A", 1, 100), h("B", 1, 0)]).unpriced == ["B"]

@pytest.mark.parametrize("holdings", [[], [h("A", 1, None)]])
def test_nothing_priced_is_a_clear_error(holdings):
    with pytest.raises(ValueError, match="no priced holdings"):
        compute_portfolio_metrics(holdings)

def test_same_symbol_twice_is_merged_into_one_line():
    m = compute_portfolio_metrics([h("TCS", 10, 2500), h("TCS", 5, 2500)])
    assert len(m.holdings) == 1 and m.holdings[0].quantity == 15 and m.total_value == 37500.0

def test_inputs_are_not_mutated():
    holdings = [h("TCS", 10, 2500)]
    before = holdings[0].model_copy()
    compute_portfolio_metrics(holdings)
    assert holdings[0] == before


# ---------------------------------------------------------------- Holding model
def test_holding_rejects_negative_quantity():
    with pytest.raises(Exception):
        h("TCS", -1, 100)

def test_holding_asset_class_defaults_to_none():
    assert Holding(instrument=Instrument(symbol="X"), quantity=1).asset_class is None
