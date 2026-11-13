"""Confidence intervals for a paired difference in means.

a and b are scores of two forecasts on the same cases, in the same order.
The quantity of interest is mean(a_i - b_i).
"""
import random


def _differences(a, b):
    if len(a) != len(b):
        raise ValueError("a and b differ in length")
    if len(a) == 0:
        raise ValueError("empty input")
    return [x - y for x, y in zip(a, b)]


def _interval(means, alpha):
    means.sort()
    n = len(means)
    low = means[min(n - 1, max(0, int(alpha / 2 * n)))]
    high = means[min(n - 1, max(0, int((1 - alpha / 2) * n) - 1))]
    return low, high


def bootstrap_ci_mean_diff(a, b, n_resamples=2000, alpha=0.05, seed=0):
    """Percentile bootstrap on the paired differences.

    Resample the differences with replacement n_resamples times, take the mean
    each time, and return (mean_diff, low, high) where low and high are the
    alpha/2 and 1 - alpha/2 percentiles. Use random.Random(seed) so the result
    is repeatable. ValueError when lengths differ or the input is empty.
    """
    d = _differences(a, b)
    n = len(d)
    rng = random.Random(seed)
    means = [sum(rng.choices(d, k=n)) / n for _ in range(n_resamples)]
    low, high = _interval(means, alpha)
    return sum(d) / n, low, high


def block_bootstrap_ci_mean_diff(a, b, block_length, n_resamples=2000, alpha=0.05, seed=0):
    """Moving-block bootstrap on the paired differences.

    Weather errors are correlated in time, so resampling single cases gives
    intervals that are too narrow. Instead draw blocks of block_length
    consecutive differences, with random start positions, and join them until
    the resample is as long as the original (trim the excess).
    Returns (mean_diff, low, high) as above.
    ValueError when lengths differ, the input is empty, block_length < 1, or
    block_length > len(a).
    """
    d = _differences(a, b)
    n = len(d)
    if block_length < 1 or block_length > n:
        raise ValueError("block_length must be between 1 and len(a)")
    # Prefix sums give each block's total in one subtraction.
    prefix = [0.0]
    for x in d:
        prefix.append(prefix[-1] + x)
    starts = n - block_length + 1
    full, rest = divmod(n, block_length)
    rng = random.Random(seed)
    means = []
    for _ in range(n_resamples):
        total = 0.0
        for _ in range(full):
            s = rng.randrange(starts)
            total += prefix[s + block_length] - prefix[s]
        if rest:  # the last block is trimmed to fill the length exactly
            s = rng.randrange(starts)
            total += prefix[s + rest] - prefix[s]
        means.append(total / n)
    low, high = _interval(means, alpha)
    return sum(d) / n, low, high
