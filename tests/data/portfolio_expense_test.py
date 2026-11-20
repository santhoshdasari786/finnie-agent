"""Expense ratios in the portfolio: what the funds in it cost each year, computed in code, never guessed.

Run:  .venv/bin/python -m pytest tests/data/portfolio_expense_test.py -v

Rules pinned here
  * Holding.expense_ratio_pct is optional, in percent, 0 to 10; a stock has none
  * annual_fund_cost = sum of value x ratio / 100 over the holdings whose ratio is KNOWN
  * weighted_expense_ratio_pct = annual_fund_cost / value of those holdings x 100 (so a fund with an unknown ratio cannot drag it down)
  * expense_covered_pct = the share of the portfolio's value where the ratio is known
  * expense_unknown names the equity and debt FUNDS whose ratio is not known; plain stocks are never listed (no such thing)
  * nothing known at all -> the three numbers are None, not 0 (0% would claim "free")
  * a broker that does not report ratios (Kite) is reported as "not known", never filled in
"""
import pytest
from pydantic import ValidationError

from src.data.market.models import Instrument
from src.data.portfolio.metrics import compute_portfolio_metrics
from src.data.portfolio.models import Holding
from src.data.portfolio.sample import SampleSource


def h(symbol, qty, price, asset_class="equity", er=None, avg=None):
    return Holding(instrument=Instrument(symbol=symbol), quantity=qty, current_price=price, avg_price=avg,
                   asset_class=asset_class, expense_ratio_pct=er)


# ---------------------------------------------------------------- the field
def test_a_holding_has_no_expense_ratio_by_default():
    assert Holding(instrument=Instrument(symbol="TCS"), quantity=1).expense_ratio_pct is None


@pytest.mark.parametrize("bad", [-0.1, 10.01, 100])
def test_an_impossible_expense_ratio_is_refused(bad):
    with pytest.raises(ValidationError):
        Holding(instrument=Instrument(symbol="X"), quantity=1, expense_ratio_pct=bad)


@pytest.mark.parametrize("ok", [0, 0.05, 2.25, 10])
def test_sensible_ratios_are_accepted(ok):
    assert Holding(instrument=Instrument(symbol="X"), quantity=1, expense_ratio_pct=ok).expense_ratio_pct == ok


# ---------------------------------------------------------------- the arithmetic
FUNDS = [h("NIFTYBEES", 100, 100, "equity_fund", 0.05), h("LIQUIDBEES", 5, 100, "debt_fund", 0.65), h("GOLDBEES", 200, 100, "gold", 0.80),
         h("TCS", 5, 100), h("INFY", 20, 100), h("RELIANCE", 10, 100), h("HDFCBANK", 15, 100)]


def test_the_yearly_cost_is_value_times_ratio_for_each_fund():
    m = compute_portfolio_metrics(FUNDS)
    assert m.annual_fund_cost == 168.25                      # 10,000 x 0.05% + 500 x 0.65% + 20,000 x 0.80%


def test_the_weighted_ratio_is_over_the_funds_with_a_known_ratio_only():
    assert compute_portfolio_metrics(FUNDS).weighted_expense_ratio_pct == 0.55      # 168.25 / 30,500


def test_coverage_is_the_share_of_the_portfolio_where_the_ratio_is_known():
    assert compute_portfolio_metrics(FUNDS).expense_covered_pct == 85.92             # 30,500 / 35,500


def test_each_holding_carries_its_own_ratio():
    m = compute_portfolio_metrics(FUNDS)
    by = {x.symbol: x.expense_ratio_pct for x in m.holdings}
    assert by["GOLDBEES"] == 0.8 and by["NIFTYBEES"] == 0.05 and by["TCS"] is None


def test_a_single_fund_is_its_own_weighted_ratio():
    m = compute_portfolio_metrics([h("FUND", 10, 1000, "equity_fund", 1.25)])
    assert (m.weighted_expense_ratio_pct, m.annual_fund_cost, m.expense_covered_pct) == (1.25, 125.0, 100.0)


def test_a_zero_ratio_is_known_and_costs_nothing():
    m = compute_portfolio_metrics([h("FUND", 10, 1000, "equity_fund", 0.0), h("TCS", 10, 1000)])
    assert (m.weighted_expense_ratio_pct, m.annual_fund_cost, m.expense_covered_pct) == (0.0, 0.0, 50.0)


def test_the_yearly_cost_is_rounded_to_paise_and_the_ratio_to_two_decimals():
    m = compute_portfolio_metrics([h("A", 3, 333.33, "equity_fund", 0.333)])
    assert m.annual_fund_cost == 3.33 and m.weighted_expense_ratio_pct == 0.33


def test_an_unknown_ratio_does_not_drag_the_weighted_ratio_down():
    known_only = compute_portfolio_metrics([h("A", 10, 1000, "equity_fund", 1.0)])
    with_unknown = compute_portfolio_metrics([h("A", 10, 1000, "equity_fund", 1.0), h("B", 10, 1000, "debt_fund")])
    assert known_only.weighted_expense_ratio_pct == with_unknown.weighted_expense_ratio_pct == 1.0
    assert with_unknown.expense_covered_pct == 50.0


# ---------------------------------------------------------------- what is not known
def test_funds_without_a_ratio_are_named_biggest_first():
    m = compute_portfolio_metrics([h("SMALL", 1, 100, "debt_fund"), h("BIG", 10, 1000, "equity_fund"), h("A", 1, 100, "equity_fund", 1.0)])
    assert m.expense_unknown == ["BIG", "SMALL"]


def test_plain_stocks_are_never_listed_as_unknown():
    m = compute_portfolio_metrics([h("TCS", 10, 100), h("INFY", 10, 100)])
    assert m.expense_unknown == []


def test_gold_is_listed_only_when_it_is_a_fund_with_a_known_ratio_and_otherwise_ignored():
    assert compute_portfolio_metrics([h("COIN", 1, 100, "gold")]).expense_unknown == []


def test_nothing_known_means_none_not_zero():
    m = compute_portfolio_metrics([h("TCS", 10, 100), h("FUND", 10, 100, "equity_fund")])
    assert (m.weighted_expense_ratio_pct, m.annual_fund_cost, m.expense_covered_pct) == (None, None, None) and m.expense_unknown == ["FUND"]


def test_a_stocks_only_portfolio_has_no_expense_section_at_all():
    m = compute_portfolio_metrics([h("TCS", 10, 100)])
    assert (m.weighted_expense_ratio_pct, m.annual_fund_cost, m.expense_covered_pct, m.expense_unknown) == (None, None, None, [])


def test_an_unpriced_fund_is_left_out_like_every_other_unpriced_holding():
    m = compute_portfolio_metrics([h("A", 10, 1000, "equity_fund", 1.0), h("NOPRICE", 5, None, "debt_fund", 2.0)])
    assert m.annual_fund_cost == 100.0 and m.unpriced == ["NOPRICE"] and m.expense_unknown == []


# ---------------------------------------------------------------- merging the same fund from two sources
def test_a_known_ratio_survives_merging_two_lots_of_one_fund():
    m = compute_portfolio_metrics([h("F", 10, 100, "equity_fund", 0.5), h("F", 10, 100, "equity_fund", 0.5)])
    assert m.annual_fund_cost == 10.0 and [x.expense_ratio_pct for x in m.holdings] == [0.5]


def test_a_ratio_known_in_only_one_lot_is_used():
    m = compute_portfolio_metrics([h("F", 10, 100, "equity_fund"), h("F", 10, 100, "equity_fund", 0.5)])
    assert m.weighted_expense_ratio_pct == 0.5 and m.expense_unknown == []


def test_the_callers_holdings_are_not_changed():
    lots = [h("F", 10, 100, "equity_fund"), h("F", 10, 100, "equity_fund", 0.5)]
    compute_portfolio_metrics(lots)
    assert lots[0].expense_ratio_pct is None


# ---------------------------------------------------------------- the demo portfolio
@pytest.mark.asyncio
async def test_the_three_funds_in_the_sample_portfolio_carry_illustrative_ratios():
    held = {x.instrument.symbol: x for x in await SampleSource().holdings()}
    assert [held[s].expense_ratio_pct for s in ("NIFTYBEES", "LIQUIDBEES", "GOLDBEES")] == [0.05, 0.65, 0.80]
    assert all(held[s].expense_ratio_pct is None for s in ("RELIANCE", "TCS", "INFY", "HDFCBANK"))


@pytest.mark.asyncio
async def test_the_sample_portfolio_has_nothing_unknown():
    m = compute_portfolio_metrics([x.model_copy(update={"current_price": 100.0}) for x in await SampleSource().holdings()])
    assert m.expense_unknown == [] and m.annual_fund_cost == 168.25


def test_the_metrics_serialise_for_the_api():
    d = compute_portfolio_metrics(FUNDS).model_dump(mode="json")
    assert d["weighted_expense_ratio_pct"] == 0.55 and d["annual_fund_cost"] == 168.25 and d["expense_unknown"] == []
