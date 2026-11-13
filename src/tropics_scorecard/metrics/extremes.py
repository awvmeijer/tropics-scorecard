"""Extremes: do a forecast's heaviest values reach the heaviest values observed?

A forecast can be close on average and still never produce the rare, heavy values that
matter most. These functions compare the upper quantiles of two samples that describe the
same cases, with the relative quantile error used to assess extremes in weather-model
studies:

    (forecast quantile - observed quantile) / observed quantile

Zero means the forecast's extremes are as heavy as the observed ones; negative means they
are too weak. The samples are compared as distributions, not value by value.
"""
import math
import random

from .bootstrap import _interval


def _check_q(q):
    if not 0 <= q <= 1:
        raise ValueError(f"q {q} is outside [0, 1]")


def _from_sorted(xs, q):
    n = len(xs)
    h = (n - 1) * q
    i = int(math.floor(h))
    if i + 1 >= n:
        return xs[n - 1]
    return xs[i] + (h - i) * (xs[i + 1] - xs[i])


def quantile(values, q):
    """The q-quantile, by linear interpolation between order statistics.

    With the values sorted ascending as x[0] .. x[n-1], the position is h = (n - 1) * q and
    the result is x[i] + (h - i) * (x[i + 1] - x[i]) with i = floor(h). This is the common
    default rule. None values are skipped.
    ValueError when no value remains or q is outside [0, 1].
    """
    _check_q(q)
    xs = sorted(v for v in values if v is not None)
    if not xs:
        raise ValueError("no values")
    return _from_sorted(xs, q)


def relative_quantile_error(forecast, observed, q):
    """(quantile(forecast, q) - quantile(observed, q)) / quantile(observed, q).

    ValueError when either sample is empty, q is outside [0, 1], or the observed quantile
    is zero.
    """
    o = quantile(observed, q)
    if o == 0:
        raise ValueError("the observed quantile is zero")
    return (quantile(forecast, q) - o) / o


class _Days:
    """One sample split by day, keeping each day's values at or above a cutoff.

    The top of any resample of days is then found by sorting only those values. The
    cutoff sits at the 1 - 4(1 - q) quantile of all the data, so the kept values are about
    four times as many as the quantile needs; when a resample needs more, every value of
    the chosen days is used instead.
    """

    def __init__(self, days, q):
        self.days = [[v for v in d if v is not None] for d in days]
        flat = sorted(v for d in self.days for v in d)
        if not flat:
            raise ValueError("no values")
        self.full = _from_sorted(flat, q)
        cut = _from_sorted(flat, max(0.0, 1 - 4 * (1 - q)))
        self.counts = [len(d) for d in self.days]
        self.tails = [[v for v in d if v >= cut] for d in self.days]

    def quantile(self, picks, q):
        n = sum(self.counts[d] for d in picks)
        if n == 0:
            return None
        h = (n - 1) * q
        i = int(math.floor(h))
        need = n - i  # the values at ascending positions i .. n-1
        top = [v for d in picks for v in self.tails[d]]
        if len(top) < need:
            top = [v for d in picks for v in self.days[d]]
        top.sort(reverse=True)
        a = top[n - 1 - i]
        b = top[n - 2 - i] if i + 1 < n else a
        return a + (h - i) * (b - a)


def block_bootstrap_ci_relative_quantile_error(forecast_days, observed_days, q, block_length,
                                               n_resamples=2000, alpha=0.05, seed=0):
    """Moving-block bootstrap over days for the relative quantile error.

    forecast_days and observed_days hold one list of values per day, in time order, for the
    same days. Each resample draws blocks of block_length consecutive days with random start
    positions, joined and trimmed to the original number of days, in the same way as
    bootstrap.block_bootstrap_ci_mean_diff, and uses the same days for both samples.
    Returns (rqe, low, high): rqe from all the data, low and high the alpha/2 and
    1 - alpha/2 percentiles of the resampled values. A resample whose observed quantile is
    zero is skipped.
    ValueError when the day lists differ in length or are empty, block_length is outside
    1 .. number of days, q is outside [0, 1], or the observed quantile of all the data is
    zero.
    """
    _check_q(q)
    if len(forecast_days) != len(observed_days):
        raise ValueError("forecast_days and observed_days differ in length")
    n = len(observed_days)
    if n == 0:
        raise ValueError("empty input")
    if block_length < 1 or block_length > n:
        raise ValueError("block_length must be between 1 and the number of days")
    fc, ob = _Days(forecast_days, q), _Days(observed_days, q)
    if ob.full == 0:
        raise ValueError("the observed quantile is zero")
    starts = n - block_length + 1
    full, rest = divmod(n, block_length)
    rng = random.Random(seed)
    values = []
    for _ in range(n_resamples):
        picks = []
        for _ in range(full):
            s = rng.randrange(starts)
            picks.extend(range(s, s + block_length))
        if rest:
            s = rng.randrange(starts)
            picks.extend(range(s, s + rest))
        o = ob.quantile(picks, q)
        f = fc.quantile(picks, q)
        if o is None or f is None or o == 0:
            continue
        values.append((f - o) / o)
    if not values:
        raise ValueError("no resample had a non-zero observed quantile")
    low, high = _interval(values, alpha)
    return (fc.full - ob.full) / ob.full, low, high
