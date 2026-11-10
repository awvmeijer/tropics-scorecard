"""Continuous errors: bias, mean absolute error, root mean square error.

Conventions for every function here:
- error = forecast minus observed
- a pair is skipped when either value is None
- ValueError when the inputs differ in length, or no valid pair remains
"""


def bias(forecast, observed):
    """Mean of (forecast - observed) over valid pairs."""
    raise NotImplementedError("write me by hand: metrics.errors.bias")


def mae(forecast, observed):
    """Mean of |forecast - observed| over valid pairs."""
    raise NotImplementedError("write me by hand: metrics.errors.mae")


def rmse(forecast, observed):
    """Square root of the mean of (forecast - observed) squared over valid pairs."""
    raise NotImplementedError("write me by hand: metrics.errors.rmse")


def rmse_by_lead_time(records):
    """Group records by lead time and return {lead_time: rmse}.

    records is an iterable of (lead_time, forecast, observed) tuples.
    Pairs with a None are skipped. A lead time with no valid pair is left out.
    The result is ordered by lead time, ascending.
    """
    raise NotImplementedError("write me by hand: metrics.errors.rmse_by_lead_time")
