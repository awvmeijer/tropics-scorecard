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


def block_bootstrap_ci_statistic(daily_rows, statistic, block_length, n_resamples=2000, alpha=0.05, seed=0):
    """Moving-block bootstrap for a statistic of totals, such as a score from a contingency table.

    daily_rows holds one tuple of numbers per day, in time order, all the same length (for
    example the day's hits, misses, false alarms and correct negatives). Each resample draws
    blocks of block_length consecutive days in the same way as block_bootstrap_ci_mean_diff,
    adds up the chosen days' tuples, and applies statistic to the totals. A resample whose
    statistic is None is skipped.
    Returns (statistic of all the days, low, high), with low and high the alpha/2 and
    1 - alpha/2 percentiles of the resampled values.
    ValueError when daily_rows is empty, the tuples differ in length, block_length is outside
    1 .. len(daily_rows), or the statistic of all the days or of every resample is None.
    """
    n = len(daily_rows)
    if n == 0:
        raise ValueError("empty input")
    width = len(daily_rows[0])
    if any(len(r) != width for r in daily_rows):
        raise ValueError("rows differ in length")
    if block_length < 1 or block_length > n:
        raise ValueError("block_length must be between 1 and len(daily_rows)")
    prefix = [[0.0] * (n + 1) for _ in range(width)]
    for k in range(width):
        p = prefix[k]
        for i, r in enumerate(daily_rows):
            p[i + 1] = p[i] + r[k]
    point = statistic(tuple(prefix[k][n] for k in range(width)))
    if point is None:
        raise ValueError("the statistic of all the days is None")
    starts = n - block_length + 1
    full, rest = divmod(n, block_length)
    rng = random.Random(seed)
    values = []
    for _ in range(n_resamples):
        totals = [0.0] * width
        for _ in range(full):
            s = rng.randrange(starts)
            for k in range(width):
                totals[k] += prefix[k][s + block_length] - prefix[k][s]
        if rest:
            s = rng.randrange(starts)
            for k in range(width):
                totals[k] += prefix[k][s + rest] - prefix[k][s]
        v = statistic(tuple(totals))
        if v is not None:
            values.append(v)
    if not values:
        raise ValueError("the statistic is None for every resample")
    low, high = _interval(values, alpha)
    return point, low, high
