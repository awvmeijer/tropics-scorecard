"""Agreement statistics used in model evaluation against observations.

Conventions as in errors.py: error = forecast minus observed, a pair is skipped when either
value is None, ValueError when lengths differ or no valid pair remains.
"""
import math


def _pairs(forecast, observed):
    if len(forecast) != len(observed):
        raise ValueError("forecast and observed differ in length")
    out = [(f, o) for f, o in zip(forecast, observed) if f is not None and o is not None]
    if not out:
        raise ValueError("no valid pair")
    return out


def normalised_mean_bias(forecast, observed):
    """sum(forecast - observed) / sum(observed), as a fraction. None when sum(observed) is zero."""
    p = _pairs(forecast, observed)
    total = sum(o for _, o in p)
    return None if total == 0 else sum(f - o for f, o in p) / total


def correlation(forecast, observed):
    """Pearson correlation coefficient. None when either series is constant."""
    p = _pairs(forecast, observed)
    n = len(p)
    mf, mo = sum(f for f, _ in p) / n, sum(o for _, o in p) / n
    sff = sum((f - mf) ** 2 for f, _ in p)
    soo = sum((o - mo) ** 2 for _, o in p)
    if sff == 0 or soo == 0:
        return None
    return sum((f - mf) * (o - mo) for f, o in p) / math.sqrt(sff * soo)


def index_of_agreement(forecast, observed):
    """Willmott's index of agreement:
        1 - sum((f - o)^2) / sum((|f - mean(o)| + |o - mean(o)|)^2)
    1 is perfect, 0 no agreement. None when the denominator is zero."""
    p = _pairs(forecast, observed)
    mo = sum(o for _, o in p) / len(p)
    bottom = sum((abs(f - mo) + abs(o - mo)) ** 2 for f, o in p)
    return None if bottom == 0 else 1 - sum((f - o) ** 2 for f, o in p) / bottom


def anomaly_correlation(forecast, observed, climatology):
    """Correlation of (forecast - climatology) with (observed - climatology): how well the
    forecast follows departures from the usual, with the daily and seasonal cycle removed.
    None when either anomaly series is constant."""
    if not len(forecast) == len(observed) == len(climatology):
        raise ValueError("inputs differ in length")
    rows = [(f - c, o - c) for f, o, c in zip(forecast, observed, climatology)
            if f is not None and o is not None and c is not None]
    if not rows:
        raise ValueError("no valid triple")
    return correlation([a for a, _ in rows], [b for _, b in rows])
