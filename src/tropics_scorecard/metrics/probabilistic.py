"""Probability forecasts: Brier score, reliability table, ensemble CRPS."""


def _check(probabilities, outcomes):
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes differ in length")
    if len(probabilities) == 0:
        raise ValueError("empty input")
    for p in probabilities:
        if not 0 <= p <= 1:
            raise ValueError(f"probability {p} is outside [0, 1]")


def brier_score(probabilities, outcomes):
    """Mean of (p - o) squared, with o equal to 1 when the event happened, else 0.

    ValueError when lengths differ, the input is empty, or a p is outside [0, 1].
    """
    _check(probabilities, outcomes)
    return sum((p - (1 if o else 0)) ** 2 for p, o in zip(probabilities, outcomes)) / len(probabilities)


def reliability_table(probabilities, outcomes, n_bins):
    """Bin forecasts by probability and compare with what happened.

    Bins are equal width over [0, 1]. A probability of exactly 1.0 goes in the
    last bin. Returns one tuple per non-empty bin, in ascending order:
    (bin_lower, bin_upper, count, mean_forecast_probability, observed_frequency)
    """
    _check(probabilities, outcomes)
    if n_bins < 1:
        raise ValueError("n_bins must be at least 1")
    sums = [[0, 0.0, 0] for _ in range(n_bins)]  # count, sum of p, events
    for p, o in zip(probabilities, outcomes):
        k = min(int(p * n_bins), n_bins - 1)
        sums[k][0] += 1
        sums[k][1] += p
        sums[k][2] += 1 if o else 0
    return [(k / n_bins, (k + 1) / n_bins, c, sp / c, ev / c) for k, (c, sp, ev) in enumerate(sums) if c]


def crps_ensemble(members, observed):
    """Continuous ranked probability score of one ensemble against one value.

    crps = mean_i |x_i - y|  -  (1 / (2 * m * m)) * sum_i sum_j |x_i - x_j|
    with m members x and the observation y. Lower is better. With one member
    it equals the absolute error. ValueError when members is empty.
    """
    m = len(members)
    if m == 0:
        raise ValueError("no members")
    accuracy = sum(abs(x - observed) for x in members) / m
    # Sum over ordered pairs from the sorted members: x_(i) appears with weight 2i - m + 1.
    spread = 2 * sum((2 * i - m + 1) * x for i, x in enumerate(sorted(members)))
    return accuracy - spread / (2 * m * m)
