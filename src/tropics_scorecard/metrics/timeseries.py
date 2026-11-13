"""Time series helpers: rolling mean and resampling to a fixed step."""


def rolling_mean(values, window):
    """Mean of each run of `window` consecutive values.

    Returns a list of length len(values) - window + 1.
    ValueError when window < 1 or window > len(values).
    Aim for one pass, not a fresh sum per window.
    """
    if window < 1 or window > len(values):
        raise ValueError("window must be between 1 and len(values)")
    total = sum(values[:window])
    out = [total / window]
    for i in range(window, len(values)):
        total += values[i] - values[i - window]
        out.append(total / window)
    return out


def resample_mean(times, values, step, start):
    """Average irregular readings into fixed bins.

    times: numbers (for example minutes), ascending. values: same length.
    Bin k covers start + k*step <= t < start + (k+1)*step.
    Returns a list of (bin_start, mean) from the bin holding `start` up to the
    bin holding the last time. An empty bin gives (bin_start, None).
    Readings before `start` are ignored. Empty input returns [].
    ValueError when step <= 0 or the lengths differ.
    """
    if step <= 0:
        raise ValueError("step must be positive")
    if len(times) != len(values):
        raise ValueError("times and values differ in length")
    sums = {}
    for t, v in zip(times, values):
        if t < start:
            continue
        k = int((t - start) // step)
        s = sums.setdefault(k, [0.0, 0])
        s[0] += v
        s[1] += 1
    if not sums:
        return []
    return [(start + k * step, sums[k][0] / sums[k][1] if k in sums else None) for k in range(max(sums) + 1)]
