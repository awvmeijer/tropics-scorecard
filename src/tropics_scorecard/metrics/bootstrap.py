"""Confidence intervals for a paired difference in means.

a and b are scores of two forecasts on the same cases, in the same order.
The quantity of interest is mean(a_i - b_i).
"""


def bootstrap_ci_mean_diff(a, b, n_resamples=2000, alpha=0.05, seed=0):
    """Percentile bootstrap on the paired differences.

    Resample the differences with replacement n_resamples times, take the mean
    each time, and return (mean_diff, low, high) where low and high are the
    alpha/2 and 1 - alpha/2 percentiles. Use random.Random(seed) so the result
    is repeatable. ValueError when lengths differ or the input is empty.
    """
    raise NotImplementedError("write me by hand: metrics.bootstrap.bootstrap_ci_mean_diff")


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
    raise NotImplementedError("write me by hand: metrics.bootstrap.block_bootstrap_ci_mean_diff")
