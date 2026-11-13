"""Choose the bootstrap block length from baseline errors only (protocol section 7).

For each variable, at lead day 1: the daily series of persistence MAE minus climatology MAE
on common cases, then its autocorrelation. The block length is the first lag in days below
0.1, at least 2 days; the largest over the variables is used for all. No model is read.
    uv run python scripts/fix_block_length.py
"""
import pandas as pd

from tropics_scorecard.paths import load_config
from tropics_scorecard.scorer import core
from tropics_scorecard.sources import get_source

cfg = load_config()
best = 2
for v in core.VARIABLES:
    cases = core.cases_for(cfg, v, "day", 1)
    pa = core.make_pairs(get_source("persistence", cfg), v, cases, ())
    pb = core.make_pairs(get_source("climatology", cfg), v, cases, ())
    keep = ["station_key", "valid_time"]
    common = pa.merge(pb[keep], on=keep)
    pb = pb.merge(common[keep], on=keep)
    fn, cols, _ = core.CONTINUOUS["mae"]
    (days, a), = core.daily_values(common, [], fn, cols).values()
    (days_b, b), = core.daily_values(pb, [], fn, cols).values()
    d = pd.Series(a, index=pd.to_datetime(days)) - pd.Series(b, index=pd.to_datetime(days_b))
    d = d.asfreq("D")
    acf = [d.autocorr(k) for k in range(1, 31)]
    lag = next((k for k, r in enumerate(acf, 1) if r < 0.1), 30)
    print(v, "days", int(d.notna().sum()), "acf lags 1 to 7:", [round(r, 2) for r in acf[:7]], "first lag below 0.1:", lag)
    best = max(best, lag)
print("block_length_days:", best)
