"""Continuous errors: bias, mean absolute error, root mean square error.

Conventions for every function here:
- error = forecast minus observed
- a pair is skipped when either value is None
- ValueError when the inputs differ in length, or no valid pair remains
"""
import math


def _errors(forecast, observed):
    if len(forecast) != len(observed):
        raise ValueError("forecast and observed differ in length")
    out = [f - o for f, o in zip(forecast, observed) if f is not None and o is not None]
    if not out:
        raise ValueError("no valid pair")
    return out


def bias(forecast, observed):
    """Mean of (forecast - observed) over valid pairs."""
    e = _errors(forecast, observed)
    return sum(e) / len(e)


def mae(forecast, observed):
    """Mean of |forecast - observed| over valid pairs."""
    e = _errors(forecast, observed)
    return sum(abs(x) for x in e) / len(e)


def rmse(forecast, observed):
    """Square root of the mean of (forecast - observed) squared over valid pairs."""
    e = _errors(forecast, observed)
    return math.sqrt(sum(x * x for x in e) / len(e))


def rmse_by_lead_time(records):
    """Group records by lead time and return {lead_time: rmse}.

    records is an iterable of (lead_time, forecast, observed) tuples.
    Pairs with a None are skipped. A lead time with no valid pair is left out.
    The result is ordered by lead time, ascending.
    """
    groups = {}
    for lead, f, o in records:
        if f is None or o is None:
            continue
        groups.setdefault(lead, ([], []))
        groups[lead][0].append(f)
        groups[lead][1].append(o)
    return {lead: rmse(*groups[lead]) for lead in sorted(groups)}
