"""Probability forecasts: Brier score, reliability table, ensemble CRPS."""


def brier_score(probabilities, outcomes):
    """Mean of (p - o) squared, with o equal to 1 when the event happened, else 0.

    ValueError when lengths differ, the input is empty, or a p is outside [0, 1].
    """
    raise NotImplementedError("write me by hand: metrics.probabilistic.brier_score")


def reliability_table(probabilities, outcomes, n_bins):
    """Bin forecasts by probability and compare with what happened.

    Bins are equal width over [0, 1]. A probability of exactly 1.0 goes in the
    last bin. Returns one tuple per non-empty bin, in ascending order:
    (bin_lower, bin_upper, count, mean_forecast_probability, observed_frequency)
    """
    raise NotImplementedError("write me by hand: metrics.probabilistic.reliability_table")


def crps_ensemble(members, observed):
    """Continuous ranked probability score of one ensemble against one value.

    crps = mean_i |x_i - y|  -  (1 / (2 * m * m)) * sum_i sum_j |x_i - x_j|
    with m members x and the observation y. Lower is better. With one member
    it equals the absolute error. ValueError when members is empty.
    """
    raise NotImplementedError("write me by hand: metrics.probabilistic.crps_ensemble")
