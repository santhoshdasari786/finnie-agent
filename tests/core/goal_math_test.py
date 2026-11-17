"""Goal projection maths: pure Python, no mocks, no LLM.

Run:  .venv/bin/python -m pytest tests/core/goal_math_test.py -v

Formula (monthly compounding, r = annual rate / 12, n = months):
    FV = P*(1+r)^n + PMT*(((1+r)^n - 1) / r)           and  FV = P + PMT*n  when r = 0
Hand-checked anchor: 1,000 a month for 1 year at 12% a year is 12,682.50 (the textbook figure).
"""
import math

import pytest

from src.core.goal_math import RATES, SCENARIOS, future_value, plan_goal, required_monthly, years_to_reach


# ================================================================ future_value
def test_the_textbook_anchor():
    assert future_value(0, 1000, 12, 1) == pytest.approx(12682.50, abs=0.01)

def test_a_lump_sum_only():
    assert future_value(100_000, 0, 12, 1) == pytest.approx(112_682.50, abs=0.01)

def test_start_and_contributions_add_up():
    both = future_value(100_000, 1000, 12, 1)
    assert both == pytest.approx(future_value(100_000, 0, 12, 1) + future_value(0, 1000, 12, 1))

def test_zero_rate_is_simple_addition():
    assert future_value(1000, 100, 0, 2) == 1000 + 100 * 24

def test_a_higher_rate_gives_a_higher_value():
    assert future_value(0, 1000, 5, 10) < future_value(0, 1000, 8, 10) < future_value(0, 1000, 12, 10)

def test_a_longer_horizon_gives_a_higher_value():
    assert future_value(0, 1000, 8, 5) < future_value(0, 1000, 8, 10)

def test_fractional_years_are_months():
    assert future_value(0, 1000, 0, 1.5) == 18_000


# ================================================================ required_monthly
def test_required_monthly_inverts_the_anchor():
    assert required_monthly(12682.50, 0, 12, 1) == pytest.approx(1000, abs=0.01)

def test_zero_rate_required_monthly():
    assert required_monthly(3400, 1000, 0, 2) == 100

def test_nothing_is_needed_when_the_start_already_grows_past_the_target():
    assert required_monthly(100_000, 100_000, 8, 5) == 0

@pytest.mark.parametrize("target,start,rate,years", [
    (5_000_000, 0, 7, 10), (1_000_000, 50_000, 4.5, 8), (250_000, 10_000, 11, 3), (9_000_000, 200_000, 3, 25),
    (500_000, 0, 0, 5),
])
def test_round_trip_saving_the_required_amount_hits_the_target(target, start, rate, years):
    pmt = required_monthly(target, start, rate, years)
    assert future_value(start, pmt, rate, years) == pytest.approx(target, rel=1e-9)


# ================================================================ the rate table
def test_every_risk_level_has_three_ordered_rates():
    for risk, (low, mid, high) in RATES.items():
        assert 0 <= low < mid < high, risk

def test_riskier_means_higher_assumed_rates_at_each_scenario():
    c, m, a = RATES["conservative"], RATES["moderate"], RATES["aggressive"]
    assert all(c[i] < m[i] < a[i] for i in range(3))

def test_scenario_names_are_fixed_and_ordered():
    assert SCENARIOS == ("pessimistic", "expected", "optimistic")


# ================================================================ plan_goal
def plan(**kw):
    base = dict(years=10, risk="moderate", monthly=20_000, start=0.0, target=5_000_000)
    return plan_goal(**{**base, **kw})

def test_three_scenarios_in_order_with_the_tables_rates():
    p = plan()
    assert [s.name for s in p.scenarios] == list(SCENARIOS)
    assert [s.annual_rate_pct for s in p.scenarios] == list(RATES["moderate"])

def test_each_projection_is_the_future_value():
    p = plan(start=100_000)
    for s in p.scenarios:
        assert s.projected == pytest.approx(future_value(100_000, 20_000, s.annual_rate_pct, 10))

def test_projections_rise_from_pessimistic_to_optimistic():
    v = [s.projected for s in plan().scenarios]
    assert v == sorted(v) and len(set(v)) == 3

def test_gap_is_projected_minus_target():
    for s in plan().scenarios:
        assert s.gap == pytest.approx(s.projected - 5_000_000)

def test_required_monthly_per_scenario_reaches_the_target():
    p = plan()
    for s in p.scenarios:
        assert future_value(0, s.required_monthly, s.annual_rate_pct, 10) == pytest.approx(5_000_000, rel=1e-9)

def test_without_a_target_there_is_no_gap_and_no_required_amount():
    p = plan(target=None)
    assert all(s.gap is None and s.required_monthly is None for s in p.scenarios)

def test_already_met_when_the_start_covers_the_target():
    assert plan(start=6_000_000).already_met is True
    assert plan(start=100).already_met is False
    assert plan(target=None, start=6_000_000).already_met is False

def test_a_start_exactly_equal_to_the_target_counts_as_met():
    assert plan(start=5_000_000).already_met is True

def test_the_inputs_are_echoed_back():
    p = plan(start=5, monthly=7)
    assert (p.years, p.monthly, p.start, p.target, p.risk) == (10, 7, 5, 5_000_000, "moderate")

def test_no_monthly_saving_with_a_start_still_projects():
    p = plan(monthly=0, start=100_000, target=None)
    assert p.scenarios[1].projected == pytest.approx(future_value(100_000, 0, RATES["moderate"][1], 10))

def test_a_target_with_nothing_saved_still_gives_the_required_amount():
    p = plan(monthly=0, start=0)
    assert all(s.projected == 0 and s.required_monthly > 0 for s in p.scenarios)


# ================================================================ validation
@pytest.mark.parametrize("kw", [
    dict(years=0), dict(years=-5), dict(years=61), dict(monthly=-1), dict(start=-1), dict(target=0), dict(target=-100),
    dict(risk="reckless"), dict(years=float("nan")), dict(monthly=float("inf")), dict(target=float("nan")),
    dict(monthly=0, start=0, target=None),            # nothing to project
])
def test_bad_inputs_are_rejected_with_a_message(kw):
    with pytest.raises(ValueError) as e:
        plan(**kw)
    assert str(e.value)

def test_the_maximum_horizon_is_allowed():
    assert plan(years=60).years == 60

def test_results_are_finite_numbers():
    p = plan(years=60, monthly=1_000_000, target=10**12)
    assert all(math.isfinite(s.projected) and math.isfinite(s.required_monthly) for s in p.scenarios)


# ================================================================ years_to_reach ("how long?")
def test_years_to_reach_inverts_the_anchor():
    assert years_to_reach(12682.50, 0, 1000, 12) == pytest.approx(1.0, abs=1e-4)

def test_zero_rate_years():
    assert years_to_reach(3400, 1000, 100, 0) == 2.0

@pytest.mark.parametrize("target,start,monthly,rate", [
    (2_500_000, 500_000, 10_000, 7), (10_000_000, 0, 20_000, 11), (1_000_000, 100_000, 5_000, 3),
    (5_000_000, 2_000_000, 0, 8), (800_000, 0, 10_000, 0),
])
def test_round_trip_the_years_found_reach_the_target(target, start, monthly, rate):
    y = years_to_reach(target, start, monthly, rate)
    assert future_value(start, monthly, rate, y) == pytest.approx(target, rel=1e-9)

def test_already_there_takes_no_time():
    assert years_to_reach(100, 100, 0, 7) == 0.0 and years_to_reach(100, 500, 0, 7) == 0.0

def test_already_there_takes_no_time_even_at_a_zero_rate_with_no_saving():
    assert years_to_reach(100, 100, 0, 0) == 0.0

def test_nothing_saved_never_arrives():
    assert years_to_reach(1_000_000, 0, 0, 7) is None
    assert years_to_reach(1_000_000, 0, 0, 0) is None

def test_beyond_the_maximum_horizon_is_none():
    assert years_to_reach(10**9, 0, 1, 7) is None

def test_a_higher_rate_gets_there_sooner():
    assert years_to_reach(5_000_000, 0, 20_000, 11) < years_to_reach(5_000_000, 0, 20_000, 7) < \
           years_to_reach(5_000_000, 0, 20_000, 3)


# ================================================================ plan_goal: unknown horizon, and the user's own rate
def test_without_a_horizon_each_scenario_says_how_many_years():
    p = plan(years=None)
    assert p.years is None
    for s in p.scenarios:
        assert s.years_needed == pytest.approx(years_to_reach(5_000_000, 0, 20_000, s.annual_rate_pct))
        assert s.projected is None and s.gap is None and s.required_monthly is None

def test_a_better_scenario_needs_fewer_years():
    y = [s.years_needed for s in plan(years=None).scenarios]
    assert y == sorted(y, reverse=True)

def test_without_a_horizon_a_target_is_required():
    with pytest.raises(ValueError):
        plan(years=None, target=None)

def test_without_a_horizon_something_must_be_saved():
    with pytest.raises(ValueError):
        plan(years=None, monthly=0, start=0)

def test_without_a_horizon_but_already_met():
    p = plan(years=None, start=6_000_000)
    assert p.already_met and all(s.years_needed == 0 for s in p.scenarios)

def test_an_unreachable_goal_has_no_years():
    p = plan(years=None, monthly=1, target=10**9)
    assert all(s.years_needed is None for s in p.scenarios)

def test_a_users_own_rate_gives_one_scenario():
    p = plan(rate_pct=12)
    assert [(s.name, s.annual_rate_pct) for s in p.scenarios] == [("your rate", 12)]
    assert p.scenarios[0].projected == pytest.approx(future_value(0, 20_000, 12, 10))

def test_a_users_rate_also_works_for_required_and_time():
    assert plan(rate_pct=12).scenarios[0].required_monthly == pytest.approx(required_monthly(5_000_000, 0, 12, 10))
    assert plan(years=None, rate_pct=12).scenarios[0].years_needed == pytest.approx(years_to_reach(5_000_000, 0, 20_000, 12))

def test_a_zero_rate_is_allowed():
    assert plan(rate_pct=0).scenarios[0].projected == 20_000 * 120

@pytest.mark.parametrize("rate", [-1, 31, 100, float("nan"), float("inf")])
def test_an_unrealistic_rate_is_rejected(rate):
    with pytest.raises(ValueError):
        plan(rate_pct=rate)
