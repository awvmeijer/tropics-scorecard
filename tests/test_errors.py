import math

import pytest

from tropics_scorecard.metrics.errors import bias, mae, rmse, rmse_by_lead_time


def test_bias_is_forecast_minus_observed():
    assert bias([3, 5, 7], [1, 5, 10]) == pytest.approx(-1 / 3)


def test_mae():
    assert mae([3, 5, 7], [1, 5, 10]) == pytest.approx(5 / 3)


def test_rmse():
    assert rmse([3, 5, 7], [1, 5, 10]) == pytest.approx(math.sqrt(13 / 3))


def test_perfect_forecast_scores_zero():
    assert bias([1.5, 2.5], [1.5, 2.5]) == 0
    assert mae([1.5, 2.5], [1.5, 2.5]) == 0
    assert rmse([1.5, 2.5], [1.5, 2.5]) == 0


def test_pairs_with_none_are_skipped():
    assert bias([3, None, 7], [1, 5, None]) == pytest.approx(2.0)
    assert rmse([3, None, 7], [1, 5, None]) == pytest.approx(2.0)


def test_no_valid_pair_raises():
    with pytest.raises(ValueError):
        rmse([None, 2], [1, None])
    with pytest.raises(ValueError):
        mae([], [])


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        bias([1, 2], [1])


def test_rmse_by_lead_time_groups_and_orders():
    records = [
        (24, 12.0, 10.0),
        (1, 10.0, 11.0),
        (24, 10.0, 14.0),
        (1, 12.0, 11.0),
        (1, None, 9.0),
        (48, None, 9.0),
    ]
    result = rmse_by_lead_time(records)
    assert list(result.keys()) == [1, 24]
    assert result[1] == pytest.approx(1.0)
    assert result[24] == pytest.approx(math.sqrt(10))
