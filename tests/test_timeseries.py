import pytest

from tropics_scorecard.metrics.timeseries import resample_mean, rolling_mean


def test_rolling_mean_basic():
    assert rolling_mean([1, 2, 3, 4, 5], 2) == pytest.approx([1.5, 2.5, 3.5, 4.5])


def test_rolling_mean_window_one_and_full():
    assert rolling_mean([4, 8], 1) == pytest.approx([4, 8])
    assert rolling_mean([1, 2, 3], 3) == pytest.approx([2.0])


def test_rolling_mean_bad_window():
    with pytest.raises(ValueError):
        rolling_mean([1, 2], 0)
    with pytest.raises(ValueError):
        rolling_mean([1, 2], 3)


def test_resample_mean_bins_and_gaps():
    times = [0, 4, 9, 10, 31]
    values = [1.0, 3.0, 5.0, 7.0, 2.0]
    assert resample_mean(times, values, step=10, start=0) == [
        (0, pytest.approx(3.0)),
        (10, pytest.approx(7.0)),
        (20, None),
        (30, pytest.approx(2.0)),
    ]


def test_resample_mean_ignores_readings_before_start():
    assert resample_mean([5, 12, 14], [100.0, 2.0, 4.0], step=10, start=10) == [
        (10, pytest.approx(3.0)),
    ]


def test_resample_mean_empty_and_errors():
    assert resample_mean([], [], step=10, start=0) == []
    with pytest.raises(ValueError):
        resample_mean([1], [1.0], step=0, start=0)
    with pytest.raises(ValueError):
        resample_mean([1, 2], [1.0], step=10, start=0)
