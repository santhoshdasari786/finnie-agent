import math
from dataclasses import dataclass

RATES: dict[str, tuple[float, float, float]] = {       # annual %, (pessimistic, expected, optimistic). Illustrative.
    "conservative": (2.0, 4.5, 7.0),
    "moderate": (3.0, 7.0, 11.0),
    "aggressive": (4.0, 10.0, 16.0),
}
SCENARIOS = ("pessimistic", "expected", "optimistic")
MAX_YEARS = 60


def future_value(start: float, monthly: float, annual_rate_pct: float, years: float) -> float:
    r, n = annual_rate_pct / 100 / 12, years * 12
    if r == 0:
        return start + monthly * n
    g = (1 + r) ** n
    return start * g + monthly * (g - 1) / r

def balance_path(start: float, monthly: float, annual_rate_pct: float, years: float) -> list[tuple[float, float]]:
    """(year, balance) at every whole year from 0, plus the exact horizon when it is not a whole number."""
    if not math.isfinite(years) or not 0 < years <= MAX_YEARS:
        raise ValueError(f"the horizon must be between 0 and {MAX_YEARS} years")
    marks: list[float] = list(range(int(years) + 1))
    if years != int(years):
        marks.append(years)
    return [(y, future_value(start, monthly, annual_rate_pct, y)) for y in marks]


def required_monthly(target: float, start: float, annual_rate_pct: float, years: float) -> float:
    r, n = annual_rate_pct / 100 / 12, years * 12
    if r == 0:
        return max(0.0, (target - start) / n)
    g = (1 + r) ** n
    remaining = target - start * g
    return 0.0 if remaining <= 0 else remaining * r / (g - 1)

def years_to_reach(target: float, start: float, monthly: float, annual_rate_pct: float) -> float | None:
    """Years until start + monthly saving grows to target; None if never, or not within MAX_YEARS."""
    if start >= target:
        return 0.0
    r = annual_rate_pct / 100 / 12
    if r == 0:
        if monthly <= 0:
            return None
        months = (target - start) / monthly
    else:
        denominator = start * r + monthly
        if denominator <= 0:
            return None
        months = math.log((target * r + monthly) / denominator) / math.log(1 + r)
    years = months / 12
    return years if years <= MAX_YEARS else None


@dataclass(frozen=True)
class Scenario:
    name: str
    annual_rate_pct: float
    projected: float | None            # None when the horizon is what we are solving for
    gap: float | None                  # projected - target; None when there is no target
    required_monthly: float | None     # monthly saving that reaches the target at this rate
    years_needed: float | None = None  # only when the horizon was not given


@dataclass(frozen=True)
class GoalPlan:
    years: float | None
    monthly: float
    start: float
    target: float | None
    risk: str
    scenarios: tuple[Scenario, ...]
    already_met: bool

MAX_RATE_PCT = 30.0


def plan_goal(*, years: float | None, risk: str, monthly: float = 0.0, start: float = 0.0,
              target: float | None = None, rate_pct: float | None = None) -> GoalPlan:
    checks = [("monthly", monthly), ("start", start)]
    checks += [(n, v) for n, v in (("years", years), ("target", target), ("rate", rate_pct)) if v is not None]
    for label, v in checks:
        if not math.isfinite(v):
            raise ValueError(f"{label} must be a real number")
    if risk not in RATES:
        raise ValueError(f"risk must be one of {', '.join(RATES)}")
    if years is not None and not 0 < years <= MAX_YEARS:
        raise ValueError(f"the horizon must be between 0 and {MAX_YEARS} years")
    if monthly < 0 or start < 0:
        raise ValueError("amounts cannot be negative")
    if target is not None and target <= 0:
        raise ValueError("the target must be more than zero")
    if rate_pct is not None and not 0 <= rate_pct <= MAX_RATE_PCT:
        raise ValueError(f"the yearly return must be between 0% and {MAX_RATE_PCT:g}%")
    if years is None:
        if target is None:
            raise ValueError("to work out how long it takes I need a target amount")
        if monthly == 0 and start == 0:
            raise ValueError("to work out how long it takes I need a monthly amount or a starting balance")
    elif target is None and monthly == 0 and start == 0:
        raise ValueError("I need a monthly amount, a starting balance or a target to work with")

    rates = (("your rate", rate_pct),) if rate_pct is not None else tuple(zip(SCENARIOS, RATES[risk]))
    scenarios = []
    for name, rate in rates:
        if years is None:
            scenarios.append(Scenario(name, rate, None, None, None, years_to_reach(target, start, monthly, rate)))
        else:
            fv = future_value(start, monthly, rate, years)
            scenarios.append(Scenario(name, rate, fv,
                                      None if target is None else fv - target,
                                      None if target is None else required_monthly(target, start, rate, years)))
    return GoalPlan(years, monthly, start, target, risk, tuple(scenarios), target is not None and start >= target)
