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


def relative_economic_value(hits, misses, false_alarms, correct_negatives, cost_loss_ratio):
    """How much of a perfect forecast's value a yes or no forecast keeps, for one user.

    The user can pay a cost C to protect against a loss L that the event would cause, and
    cost_loss_ratio is a = C / L, between 0 and 1 exclusive. With base rate s, hit rate H
    and false alarm rate F = false_alarms / (false_alarms + correct_negatives), the mean
    expense per case, in units of L, is
        acting on the forecast   F a (1 - s) - H s (1 - a) + s
        a perfect forecast       s a
        the best fixed choice    min(a, s)   (always protect, or never)
    and the value is (best fixed - forecast) / (best fixed - perfect): 1 for a perfect
    forecast, 0 for no better than knowing only how often the event happens, negative when
    acting on the forecast costs more than the best fixed choice.
    None when the event never or always happened.
    ValueError when cost_loss_ratio is not strictly between 0 and 1.
    """
    a = cost_loss_ratio
    if not 0 < a < 1:
        raise ValueError(f"cost_loss_ratio {a} is not strictly between 0 and 1")
    n = hits + misses + false_alarms + correct_negatives
    events = hits + misses
    if n == 0 or events == 0 or events == n:
        return None
    s = events / n
    h = hits / events
    f = false_alarms / (false_alarms + correct_negatives)
    fixed = min(a, s)
    forecast = f * a * (1 - s) - h * s * (1 - a) + s
    return (fixed - forecast) / (fixed - s * a)
