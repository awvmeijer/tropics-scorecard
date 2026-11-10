import random

import pytest

from tropics_scorecard.metrics.bootstrap import (
    block_bootstrap_ci_mean_diff,
    bootstrap_ci_mean_diff,
)

# The percentile rule can be written in more than one correct way, so these
# tests check properties, not exact interval ends.


def noisy_pair(n=200, shift=0.5, seed=1):
    rng = random.Random(seed)
    b = [rng.gauss(0, 1) for _ in range(n)]
    a = [x + shift + rng.gauss(0, 0.5) for x in b]
    return a, b


@pytest.mark.parametrize("fn", [bootstrap_ci_mean_diff, lambda a, b, **k: block_bootstrap_ci_mean_diff(a, b, 5, **k)])
def test_identical_series_give_zero(fn):
    a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert fn(a, a) == (0, 0, 0)


@pytest.mark.parametrize("fn", [bootstrap_ci_mean_diff, lambda a, b, **k: block_bootstrap_ci_mean_diff(a, b, 3, **k)])
def test_constant_difference_has_zero_width(fn):
    b = [1.0, 5.0, 2.0, 8.0, 3.0, 9.0]
    a = [x + 2.0 for x in b]
    mean, low, high = fn(a, b)
    assert mean == pytest.approx(2.0)
    assert low == pytest.approx(2.0)
    assert high == pytest.approx(2.0)


def test_mean_is_inside_interval_and_interval_finds_the_shift():
    a, b = noisy_pair()
    mean, low, high = bootstrap_ci_mean_diff(a, b)
    assert low <= mean <= high
    assert low < 0.5 < high
    assert low > 0  # a shift of 0.5 with n = 200 is clearly detectable


def test_same_seed_same_answer_different_seed_different_answer():
    a, b = noisy_pair()
    assert bootstrap_ci_mean_diff(a, b, seed=7) == bootstrap_ci_mean_diff(a, b, seed=7)
    assert bootstrap_ci_mean_diff(a, b, seed=7) != bootstrap_ci_mean_diff(a, b, seed=8)


def test_wider_level_gives_wider_interval():
    a, b = noisy_pair()
    _, low95, high95 = bootstrap_ci_mean_diff(a, b, alpha=0.05)
    _, low50, high50 = bootstrap_ci_mean_diff(a, b, alpha=0.5)
    assert (high95 - low95) > (high50 - low50)


def test_block_bootstrap_is_wider_on_correlated_errors():
    # Differences that drift slowly: neighbours are alike, so there is less
    # independent information than the count suggests.
    rng = random.Random(3)
    level, diffs = 0.0, []
    for _ in range(400):
        level = 0.95 * level + rng.gauss(0, 1)
        diffs.append(level)
    zeros = [0.0] * len(diffs)
    _, low_iid, high_iid = bootstrap_ci_mean_diff(diffs, zeros)
    _, low_blk, high_blk = block_bootstrap_ci_mean_diff(diffs, zeros, block_length=40)
    assert (high_blk - low_blk) > (high_iid - low_iid)


def test_errors():
    with pytest.raises(ValueError):
        bootstrap_ci_mean_diff([1.0], [1.0, 2.0])
    with pytest.raises(ValueError):
        bootstrap_ci_mean_diff([], [])
    with pytest.raises(ValueError):
        block_bootstrap_ci_mean_diff([1.0, 2.0], [1.0, 2.0], block_length=0)
    with pytest.raises(ValueError):
        block_bootstrap_ci_mean_diff([1.0, 2.0], [1.0, 2.0], block_length=3)
