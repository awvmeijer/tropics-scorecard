import pytest

from tropics_scorecard.metrics.categorical import contingency, csi, ets, far, pod

FORECAST = [True, True, False, False, True, False, True, False]
OBSERVED = [True, False, True, False, True, False, False, False]


def test_contingency_counts():
    assert contingency(FORECAST, OBSERVED) == (2, 1, 2, 3)


def test_contingency_length_mismatch():
    with pytest.raises(ValueError):
        contingency([True], [True, False])


def test_scores_on_worked_example():
    table = (2, 1, 2, 3)
    assert pod(*table) == pytest.approx(2 / 3)
    assert far(*table) == pytest.approx(0.5)
    assert csi(*table) == pytest.approx(0.4)
    # hits_random = 3 * 4 / 8 = 1.5, so ets = 0.5 / 3.5
    assert ets(*table) == pytest.approx(1 / 7)


def test_perfect_forecast():
    table = (4, 0, 0, 6)
    assert pod(*table) == 1
    assert far(*table) == 0
    assert csi(*table) == 1
    assert ets(*table) == pytest.approx(1.0)


def test_undefined_scores_return_none():
    nothing_happened_nothing_forecast = (0, 0, 0, 5)
    assert pod(*nothing_happened_nothing_forecast) is None
    assert far(*nothing_happened_nothing_forecast) is None
    assert csi(*nothing_happened_nothing_forecast) is None
    assert ets(*nothing_happened_nothing_forecast) is None
