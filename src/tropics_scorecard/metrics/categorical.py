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
    if len(forecast_yes) != len(observed_yes):
        raise ValueError("forecast and observed differ in length")
    hits = misses = false_alarms = correct_negatives = 0
    for f, o in zip(forecast_yes, observed_yes):
        if f and o:
            hits += 1
        elif o:
            misses += 1
        elif f:
            false_alarms += 1
        else:
            correct_negatives += 1
    return hits, misses, false_alarms, correct_negatives


def _ratio(top, bottom):
    return None if bottom == 0 else top / bottom


def pod(hits, misses, false_alarms, correct_negatives):
    """Probability of detection (hit rate): hits / (hits + misses).

    None when no event was observed.
    """
    return _ratio(hits, hits + misses)


def far(hits, misses, false_alarms, correct_negatives):
    """False alarm ratio: false_alarms / (hits + false_alarms).

    None when no event was forecast.
    """
    return _ratio(false_alarms, hits + false_alarms)


def csi(hits, misses, false_alarms, correct_negatives):
    """Critical success index: hits / (hits + misses + false_alarms).

    None when the denominator is zero.
    """
    return _ratio(hits, hits + misses + false_alarms)


def ets(hits, misses, false_alarms, correct_negatives):
    """Equitable threat score.

    hits_random = (hits + misses) * (hits + false_alarms) / n, with n the total.
    ets = (hits - hits_random) / (hits + misses + false_alarms - hits_random)
    None when the denominator is zero.
    """
    n = hits + misses + false_alarms + correct_negatives
    if n == 0:
        return None
    hits_random = (hits + misses) * (hits + false_alarms) / n
    return _ratio(hits - hits_random, hits + misses + false_alarms - hits_random)
