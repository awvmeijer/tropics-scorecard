import random

import pytest

from tropics_scorecard.metrics.bootstrap import block_bootstrap_ci_statistic
from tropics_scorecard.metrics.categorical import relative_economic_value


def test_perfect_forecast_keeps_all_the_value():
    for a in (0.05, 0.2, 0.5, 0.9):
        assert relative_economic_value(10, 0, 0, 90, a) == pytest.approx(1.0)


def test_never_yes_is_worth_nothing_when_never_protecting_is_best():
    # base rate 0.1: for a cost-loss ratio above it, never protecting is the best fixed choice
    assert relative_economic_value(0, 10, 0, 90, 0.3) == pytest.approx(0.0)
    # below the base rate, always protecting is best, and a forecast that never says yes loses
    assert relative_economic_value(0, 10, 0, 90, 0.05) < 0


def test_value_peaks_at_the_base_rate_with_hit_rate_minus_false_alarm_rate():
    hits, misses, fa, cn = 6, 4, 9, 81  # H = 0.6, F = 0.1, s = 0.1
    assert relative_economic_value(hits, misses, fa, cn, 0.1) == pytest.approx(0.6 - 0.1)
    assert relative_economic_value(hits, misses, fa, cn, 0.4) < 0.5


def test_worked_example():
    # s = 0.2, H = 0.5, F = 0.125, a = 0.25: forecast expense 0.125*0.25*0.8 - 0.5*0.2*0.75 + 0.2 = 0.15,
    # best fixed 0.2, perfect 0.05, value (0.2 - 0.15) / (0.2 - 0.05) = 1/3
    assert relative_economic_value(10, 10, 10, 70, 0.25) == pytest.approx(1 / 3)


def test_value_rejects_bad_input():
    assert relative_economic_value(0, 0, 5, 95, 0.2) is None
    assert relative_economic_value(5, 5, 0, 0, 0.2) is None
    with pytest.raises(ValueError):
        relative_economic_value(1, 1, 1, 1, 0)
    with pytest.raises(ValueError):
        relative_economic_value(1, 1, 1, 1, 1)


def test_bootstrap_of_totals_matches_the_plain_statistic_and_brackets_it():
    rng = random.Random(2)
    rows = [(rng.randint(0, 3), rng.randint(0, 3), rng.randint(0, 5), rng.randint(20, 30)) for _ in range(120)]

    def stat(t):
        return relative_economic_value(*t, 0.1)

    totals = tuple(sum(r[k] for r in rows) for k in range(4))
    point, low, high = block_bootstrap_ci_statistic(rows, stat, 5, n_resamples=300)
    assert point == pytest.approx(stat(totals))
    assert low <= point <= high
    assert low < high


def test_bootstrap_of_constant_days_has_zero_width():
    rows = [(1, 2, 3, 4)] * 20
    point, low, high = block_bootstrap_ci_statistic(rows, lambda t: t[0] / sum(t), 4, n_resamples=50)
    assert point == pytest.approx(0.1)
    assert low == pytest.approx(0.1)
    assert high == pytest.approx(0.1)


def test_bootstrap_of_totals_rejects_bad_input():
    with pytest.raises(ValueError):
        block_bootstrap_ci_statistic([], sum, 1)
    with pytest.raises(ValueError):
        block_bootstrap_ci_statistic([(1, 2), (1,)], sum, 1)
    with pytest.raises(ValueError):
        block_bootstrap_ci_statistic([(1, 2)] * 3, sum, 4)
    with pytest.raises(ValueError):
        block_bootstrap_ci_statistic([(1, 2)] * 3, lambda t: None, 1)
