"""Yes or no events: contingency table and the scores built on it.

hit: forecast yes, observed yes
miss: forecast no, observed yes
false alarm: forecast yes, observed no
correct negative: forecast no, observed no
"""


def contingency(forecast_yes, observed_yes):
    """Return (hits, misses, false_alarms, correct_negatives) as integers.

    Inputs are equal-length sequences of booleans. ValueError otherwise.
    """
    raise NotImplementedError("write me by hand: metrics.categorical.contingency")


def pod(hits, misses, false_alarms, correct_negatives):
    """Probability of detection (hit rate): hits / (hits + misses).

    None when no event was observed.
    """
    raise NotImplementedError("write me by hand: metrics.categorical.pod")


def far(hits, misses, false_alarms, correct_negatives):
    """False alarm ratio: false_alarms / (hits + false_alarms).

    None when no event was forecast.
    """
    raise NotImplementedError("write me by hand: metrics.categorical.far")


def csi(hits, misses, false_alarms, correct_negatives):
    """Critical success index: hits / (hits + misses + false_alarms).

    None when the denominator is zero.
    """
    raise NotImplementedError("write me by hand: metrics.categorical.csi")


def ets(hits, misses, false_alarms, correct_negatives):
    """Equitable threat score.

    hits_random = (hits + misses) * (hits + false_alarms) / n, with n the total.
    ets = (hits - hits_random) / (hits + misses + false_alarms - hits_random)
    None when the denominator is zero.
    """
    raise NotImplementedError("write me by hand: metrics.categorical.ets")
