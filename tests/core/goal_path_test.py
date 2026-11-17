"""goal_math.balance_path: the year-by-year balance behind the Goals chart.

Run:  .venv/bin/python -m pytest tests/core/goal_path_test.py -v

Contract
  balance_path(start, monthly, annual_rate_pct, years) -> [(year, balance), ...]
  * one point per whole year from 0, plus the exact horizon when it is not a whole number of years
  * every balance is future_value(...) at that year, so the last point equals the scenario's projection
"""
import pytest

from src.core.goal_math import MAX_YEARS, balance_path, future_value


def test_one_point_per_year_including_year_zero():
    path = balance_path(0, 1000, 8, 10)
    assert [y for y, _ in path] == list(range(11))


def test_year_zero_is_the_starting_balance():
    assert balance_path(50_000, 1000, 8, 5)[0] == (0, 50_000)


def test_every_balance_is_the_future_value_at_that_year():
    for y, v in balance_path(10_000, 2_000, 9, 12):
        assert v == pytest.approx(future_value(10_000, 2_000, 9, y), rel=1e-12)


def test_the_last_point_is_the_projection_exactly():
    path = balance_path(10_000, 2_000, 9, 12)
    assert path[-1] == (12, future_value(10_000, 2_000, 9, 12))


def test_a_fractional_horizon_ends_with_the_exact_horizon():
    path = balance_path(0, 1000, 8, 7.5)
    assert [y for y, _ in path] == [0, 1, 2, 3, 4, 5, 6, 7, 7.5]
    assert path[-1][1] == future_value(0, 1000, 8, 7.5)


def test_less_than_a_year_has_two_points():
    assert [y for y, _ in balance_path(0, 1000, 8, 0.5)] == [0, 0.5]


def test_exactly_one_year_has_two_points_not_three():
    assert [y for y, _ in balance_path(0, 1000, 8, 1)] == [0, 1]


def test_a_zero_rate_grows_in_a_straight_line():
    assert [v for _, v in balance_path(1000, 100, 0, 3)] == [1000, 2200, 3400, 4600]


def test_balances_never_fall_when_the_inputs_are_not_negative():
    values = [v for _, v in balance_path(5_000, 500, 6, 30)]
    assert values == sorted(values)


@pytest.mark.parametrize("years", [0, -1, MAX_YEARS + 1, float("nan"), float("inf")])
def test_a_horizon_outside_the_supported_range_is_rejected(years):
    with pytest.raises(ValueError):
        balance_path(0, 1000, 8, years)


def test_the_longest_horizon_is_allowed():
    assert len(balance_path(0, 1000, 8, MAX_YEARS)) == MAX_YEARS + 1
