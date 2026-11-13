"""The scorer: one entry point for any forecast source.

    from tropics_scorecard.scorer import run
    results = run(source, cfg)          # tidy results for one source
    results = run_all(cfg)              # every source, every comparison, written to disk

All the maths goes through src/tropics_scorecard/metrics/. Nothing here computes an error,
a score or an interval by itself.

Rules (docs/verification_protocol.md, sections 4 and 7):
- A score with an interval is the mean over days of the daily score. Each day counts once,
  however many stations reported. The interval comes from a moving-block bootstrap over
  days (metrics.bootstrap.block_bootstrap_ci_mean_diff), run against zero for a single
  score and against the other source for a comparison.
- RMSE is the square root of the day-weighted mean squared error; its interval is the
  interval on the mean squared error, square-rooted.
- Contingency scores (probability of detection, false alarm ratio, critical success index,
  equitable threat score) come from one table over all pairs in the group, with no interval.
- Comparisons use only cases both sources forecast.
"""
from .core import RESULT_COLUMNS, run, run_all, score_pairs

__all__ = ["RESULT_COLUMNS", "run", "run_all", "score_pairs"]
