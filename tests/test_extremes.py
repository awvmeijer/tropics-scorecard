import random

import pytest

from tropics_scorecard.metrics.errors import percent_change
from tropics_scorecard.metrics.extremes import (
    block_bootstrap_ci_relative_quantile_error,
    quantile,
    relative_quantile_error,
)


def test_quantile_interpolates_between_order_statistics():
    xs = [4.0, 1.0, 3.0, 2.0, None]
    assert quantile(xs, 0) == 1.0
    assert quantile(xs, 1) == 4.0
    assert quantile(xs, 0.5) == pytest.approx(2.5)
    assert quantile(xs, 0.9) == pytest.approx(3.7)


def test_quantile_rejects_bad_input():
    with pytest.raises(ValueError):
        quantile([], 0.5)
    with pytest.raises(ValueError):
        quantile([None], 0.5)
    with pytest.raises(ValueError):
        quantile([1.0], 1.5)


def test_relative_quantile_error_sign_and_size():
    observed = [float(i) for i in range(101)]
    assert relative_quantile_error([x / 2 for x in observed], observed, 0.99) == pytest.approx(-0.5)
    assert relative_quantile_error(observed, observed, 0.99) == 0
    with pytest.raises(ValueError):
        relative_quantile_error([1.0], [0.0, 0.0], 0.99)


def test_percent_change():
    assert percent_change(-0.25, 2.0) == pytest.approx(-12.5)
    with pytest.raises(ValueError):
        percent_change(1.0, 0)


def days_of(seed, n_days=60, per_day=50, scale=1.0):
    rng = random.Random(seed)
    return [[rng.expovariate(1.0) * scale for _ in range(per_day)] for _ in range(n_days)]


def test_bootstrap_matches_the_plain_estimate_and_brackets_it():
    obs = days_of(1)
    fc = days_of(2, scale=0.5)
    flat_o = [v for d in obs for v in d]
    flat_f = [v for d in fc for v in d]
    rqe, low, high = block_bootstrap_ci_relative_quantile_error(fc, obs, 0.99, 5, n_resamples=300)
    assert rqe == pytest.approx(relative_quantile_error(flat_f, flat_o, 0.99))
    assert low <= rqe <= high
    assert high < 0  # half the scale: clearly too weak


def test_bootstrap_of_identical_samples_is_zero():
    obs = days_of(3)
    assert block_bootstrap_ci_relative_quantile_error(obs, obs, 0.95, 4, n_resamples=50) == (0, 0, 0)


def test_tail_shortcut_gives_the_same_quantile_as_sorting_everything():
    from tropics_scorecard.metrics.extremes import _Days

    # A few very wet days: resamples that repeat them need more values than the cutoff kept,
    # which exercises the fallback as well as the shortcut.
    rng = random.Random(5)
    days = [[rng.expovariate(1.0) * (20 if d % 10 == 0 else 1) for _ in range(30)] for d in range(80)]
    for q in (0.9, 0.99, 0.999):
        kept = _Days(days, q)
        for trial in range(200):
            picks = [rng.randrange(80) for _ in range(80)] if trial % 2 else [0, 10, 20, 30] * 20
            assert kept.quantile(picks, q) == pytest.approx(quantile([v for d in picks for v in days[d]], q))


def test_bootstrap_rejects_bad_input():
    obs = days_of(4, n_days=5)
    with pytest.raises(ValueError):
        block_bootstrap_ci_relative_quantile_error(obs[:4], obs, 0.99, 2)
    with pytest.raises(ValueError):
        block_bootstrap_ci_relative_quantile_error([], [], 0.99, 1)
    with pytest.raises(ValueError):
        block_bootstrap_ci_relative_quantile_error(obs, obs, 0.99, 6)
    zeros = [[0.0] * 10 for _ in range(5)]
    with pytest.raises(ValueError):
        block_bootstrap_ci_relative_quantile_error(obs, zeros, 0.99, 2)
