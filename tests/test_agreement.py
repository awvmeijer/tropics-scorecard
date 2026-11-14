import pytest

from tropics_scorecard.metrics.agreement import (
    anomaly_correlation,
    correlation,
    index_of_agreement,
    normalised_mean_bias,
)


def test_normalised_mean_bias():
    assert normalised_mean_bias([2.0, 4.0], [1.0, 3.0]) == pytest.approx(0.5)
    assert normalised_mean_bias([1.0, None], [1.0, 5.0]) == 0
    assert normalised_mean_bias([1.0], [0.0]) is None


def test_correlation():
    assert correlation([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0)
    assert correlation([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)
    assert correlation([1.0, 1.0], [1.0, 2.0]) is None
    with pytest.raises(ValueError):
        correlation([1.0], [1.0, 2.0])


def test_index_of_agreement():
    obs = [1.0, 2.0, 3.0, 4.0]
    assert index_of_agreement(obs, obs) == pytest.approx(1.0)
    # a forecast stuck at the observed mean: numerator 5, denominator 5, so no agreement
    assert index_of_agreement([2.5] * 4, obs) == pytest.approx(0.0)
    # a constant offset of 1: numerator 4, denominator from the definition
    f = [2.0, 3.0, 4.0, 5.0]
    bottom = sum((abs(a - 2.5) + abs(b - 2.5)) ** 2 for a, b in zip(f, obs))
    assert index_of_agreement(f, obs) == pytest.approx(1 - 4 / bottom)


def test_anomaly_correlation_removes_the_cycle():
    clim = [10.0, 20.0, 10.0, 20.0]
    obs = [11.0, 19.0, 9.0, 21.0]
    assert correlation(clim, obs) > 0.9  # the cycle alone looks like skill
    assert anomaly_correlation(clim, obs, clim) is None  # but it has no anomaly at all
    assert anomaly_correlation([11.0, 19.0, 9.0, 21.0], obs, clim) == pytest.approx(1.0)
    assert anomaly_correlation([9.0, 21.0, 11.0, 19.0], obs, clim) == pytest.approx(-1.0)
