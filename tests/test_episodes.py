import pytest

from tropics_scorecard.metrics.episodes import merge_intervals


def test_overlapping_intervals_merge():
    assert merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)]) == [(1, 6), (8, 10), (15, 18)]


def test_touching_intervals_merge():
    assert merge_intervals([(1, 4), (4, 5)]) == [(1, 5)]


def test_unsorted_input_and_containment():
    assert merge_intervals([(8, 10), (1, 10), (2, 3)]) == [(1, 10)]


def test_max_gap_joins_nearby_intervals():
    alerts = [(0, 10), (12, 20), (40, 45)]
    assert merge_intervals(alerts, max_gap=0) == [(0, 10), (12, 20), (40, 45)]
    assert merge_intervals(alerts, max_gap=2) == [(0, 20), (40, 45)]
    assert merge_intervals(alerts, max_gap=20) == [(0, 45)]


def test_empty_and_single():
    assert merge_intervals([]) == []
    assert merge_intervals([(5, 5)]) == [(5, 5)]


def test_input_is_not_modified():
    original = [(3, 4), (1, 2)]
    merge_intervals(original)
    assert original == [(3, 4), (1, 2)]


def test_bad_interval_raises():
    with pytest.raises(ValueError):
        merge_intervals([(5, 1)])
