"""Time series helpers: rolling mean and resampling to a fixed step."""


def rolling_mean(values, window):
    """Mean of each run of `window` consecutive values.

    Returns a list of length len(values) - window + 1.
    ValueError when window < 1 or window > len(values).
    Aim for one pass, not a fresh sum per window.
    """
    raise NotImplementedError("write me by hand: metrics.timeseries.rolling_mean")


def resample_mean(times, values, step, start):
    """Average irregular readings into fixed bins.

    times: numbers (for example minutes), ascending. values: same length.
    Bin k covers start + k*step <= t < start + (k+1)*step.
    Returns a list of (bin_start, mean) from the bin holding `start` up to the
    bin holding the last time. An empty bin gives (bin_start, None).
    Readings before `start` are ignored. Empty input returns [].
    ValueError when step <= 0 or the lengths differ.
    """
    raise NotImplementedError("write me by hand: metrics.timeseries.resample_mean")
