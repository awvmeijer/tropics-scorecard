import pytest

from tropics_scorecard.metrics.probabilistic import (
    brier_score,
    crps_ensemble,
    reliability_table,
)


def test_brier_worked_example():
    assert brier_score([0.9, 0.1, 0.7, 0.3], [True, False, False, True]) == pytest.approx(0.25)


def test_brier_extremes():
    assert brier_score([1.0, 0.0], [True, False]) == 0
    assert brier_score([0.0, 1.0], [True, False]) == 1


def test_brier_errors():
    with pytest.raises(ValueError):
        brier_score([], [])
    with pytest.raises(ValueError):
        brier_score([0.5], [True, False])
    with pytest.raises(ValueError):
        brier_score([1.2], [True])


def test_reliability_table():
    probs = [0.1, 0.2, 0.6, 0.8, 1.0]
    outcomes = [False, True, True, True, False]
    table = reliability_table(probs, outcomes, n_bins=2)
    assert len(table) == 2
    lower, upper, count, mean_p, freq = table[0]
    assert (lower, upper, count) == (pytest.approx(0.0), pytest.approx(0.5), 2)
    assert mean_p == pytest.approx(0.15)
    assert freq == pytest.approx(0.5)
    lower, upper, count, mean_p, freq = table[1]
    assert (lower, upper, count) == (pytest.approx(0.5), pytest.approx(1.0), 3)
    assert mean_p == pytest.approx(0.8)
    assert freq == pytest.approx(2 / 3)


def test_reliability_table_skips_empty_bins():
    table = reliability_table([0.05, 0.95], [False, True], n_bins=10)
    assert [row[2] for row in table] == [1, 1]
    assert table[0][0] == pytest.approx(0.0)
    assert table[1][0] == pytest.approx(0.9)


def test_crps_worked_example():
    # mean |x - y| = 2/3; sum over all ordered pairs of |xi - xj| = 8; 8 / (2 * 9) = 4/9
    assert crps_ensemble([1, 2, 3], 2) == pytest.approx(2 / 9)


def test_crps_single_member_is_absolute_error():
    assert crps_ensemble([5.0], 3.0) == pytest.approx(2.0)


def test_crps_identical_members_is_absolute_error():
    assert crps_ensemble([4.0, 4.0, 4.0], 1.0) == pytest.approx(3.0)


def test_crps_empty_raises():
    with pytest.raises(ValueError):
        crps_ensemble([], 1.0)
