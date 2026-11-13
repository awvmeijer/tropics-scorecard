"""Two summary tables, added after the main scoring (protocol change log, 14 November 2026).

    skill.parquet     each model's change in mean absolute error against climatology, as a
                      percentage of climatology's error on the same cases, every lead day:
                      the layout of the scorecards in published weather-model studies
    extremes.parquet  the relative quantile error of 6-hour rain totals: do the model's
                      heaviest totals reach the gauges' heaviest? Against each gauge, and
                      against the gauges averaged over the model's own grid cell, so a cell
                      average is compared with a cell average

Both use the scorer's own cases, pairs and day blocks, and all their maths goes through
metrics/. Usage:
    python -m tropics_scorecard.scorer.summary
"""
from __future__ import annotations

import sys

import pandas as pd

from ..metrics import errors, extremes
from ..paths import load_config
from ..sources import get_source
from . import core

OUT = core.OUT


def _models(cfg: dict) -> list[str]:
    return [s for s in core.sources_for(cfg, "day") if s not in core.BASELINES]


def _pairs(cfg: dict, name: str, variable: str, cases: pd.DataFrame) -> pd.DataFrame:
    src = get_source(name, cfg)
    if hasattr(src, "drop_flagged"):
        src.drop_flagged = True
    p = core.make_pairs(src, "rain_hourly" if variable == core.SIX_HOUR else variable, cases, ())
    return core.six_hour_totals(p, cfg) if variable == core.SIX_HOUR else p


def skill(cfg: dict) -> pd.DataFrame:
    """Percent change in MAE against climatology, with the paired interval, every lead day."""
    rows = []
    fn = core.CONTINUOUS["mae"][0]
    for variable in cfg["summary_scores"]["skill_variables"]:
        base = "rain_hourly" if variable == core.SIX_HOUR else variable
        for lead in cfg["lead_times"]["days"]:
            cases = core.cases_for(cfg, base, "day", lead)
            clim = _pairs(cfg, "climatology", variable, cases)
            for name in _models(cfg):
                if core.excluded(cfg, name, base, "day", lead):
                    continue
                try:
                    p = _pairs(cfg, name, variable, cases)
                except LookupError:
                    continue
                keep = ["station_key", "valid_time"]
                common = p.merge(clim[keep], on=keep)
                ref = clim.merge(common[keep], on=keep)
                da = core.daily_values(common, [], fn, ("forecast", "observed")).get(())
                db = dict(zip(*core.daily_values(ref, [], fn, ("forecast", "observed")).get((), ([], []))))
                if not da:
                    continue
                pairs = [(x, db[d]) for d, x in zip(*da) if d in db]
                a, b = [x for x, _ in pairs], [y for _, y in pairs]
                ci = core.interval(a, b, cfg)
                if ci is None:
                    continue
                reference = sum(b) / len(b)  # climatology's day-weighted MAE on the same days
                pct = [errors.percent_change(v, reference) for v in ci]
                rows.append({"source": name, "variable": variable, "lead": int(lead), "difference": ci[0],
                             "difference_low": ci[1], "difference_high": ci[2], "reference_mae": reference,
                             "percent": pct[0], "low": pct[1], "high": pct[2], "n_pairs": len(common),
                             "n_days": len(a)})
                print(f"   skill {variable} day {lead} {name}: {pct[0]:+.1f}% ({pct[1]:+.1f} to {pct[2]:+.1f})",
                      flush=True)
    return pd.DataFrame(rows)


def _by_day(df: pd.DataFrame, cols: tuple[str, str]) -> tuple[list, list]:
    groups = df.groupby("day", sort=True)
    return [g[cols[0]].tolist() for _, g in groups], [g[cols[1]].tolist() for _, g in groups]


def extremes_table(cfg: dict) -> pd.DataFrame:
    """Relative quantile error of 6-hour rain totals, against gauges and against cell means."""
    s = cfg["summary_scores"]
    b = cfg["bootstrap"]
    rows = []
    for lead in cfg["lead_times"]["days"]:
        cases = core.cases_for(cfg, "rain_hourly", "day", lead)
        for name in _models(cfg):
            if core.excluded(cfg, name, "rain_hourly", "day", lead):
                continue
            try:
                p = _pairs(cfg, name, core.SIX_HOUR, cases)
            except LookupError:
                continue
            p = p.merge(get_source(name, cfg).cells, on="station_key")
            # One value per cell and time: the model's cell value, and the mean of the gauges
            # in that cell. The forecast is the same for every gauge in a cell, so its mean is it.
            cell = (p.groupby(["cell_lat", "cell_lon", "valid_time"])
                     .agg(forecast=("forecast", "mean"), observed=("observed", "mean"),
                          n=("observed", "size"), day=("day", "first")).reset_index())
            cell = cell[cell["n"] >= int(s["cell_mean_min_gauges"])]
            for reference, df in (("gauge", p), ("cell_mean", cell)):
                fd, od = _by_day(df, ("forecast", "observed"))
                for q in s["extremes_quantiles"]:
                    rqe, lo, hi = extremes.block_bootstrap_ci_relative_quantile_error(
                        fd, od, q, int(b["block_length_days"]), n_resamples=int(b["resamples"]),
                        alpha=float(b["alpha"]), seed=int(b["seed"]))
                    rows.append({"source": name, "lead": int(lead), "reference": reference, "q": q,
                                 "forecast_q": extremes.quantile(df["forecast"].tolist(), q),
                                 "observed_q": extremes.quantile(df["observed"].tolist(), q),
                                 "rqe": rqe, "low": lo, "high": hi, "n_values": len(df), "n_days": len(od)})
                    print(f"   extremes day {lead} {name} {reference} q={q}: {rows[-1]['forecast_q']:.1f} vs "
                          f"{rows[-1]['observed_q']:.1f} mm, {100 * rqe:+.0f}% ({100 * lo:+.0f} to {100 * hi:+.0f})",
                          flush=True)
    return pd.DataFrame(rows)


def main(cfg: dict | None = None) -> int:
    cfg = cfg or load_config()
    core.check_ready(cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    skill(cfg).to_parquet(OUT / "skill.parquet", index=False)
    extremes_table(cfg).to_parquet(OUT / "extremes.parquet", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
