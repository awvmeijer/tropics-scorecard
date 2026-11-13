"""Two summary tables, added after the main scoring (protocol change log, 14 November 2026).

    skill.parquet     each model's change in mean absolute error against climatology, as a
                      percentage of climatology's error on the same cases, every lead day:
                      the layout of the scorecards in published weather-model studies
    extremes.parquet  the relative quantile error of 6-hour rain totals: do the model's
                      heaviest totals reach the gauges' heaviest? Against each gauge, and
                      against the gauges averaged over the model's own grid cell, so a cell
                      average is compared with a cell average
    decision.parquet  relative economic value for heavy rain: protect when the forecast says
                      10 mm or more, and see how much of a perfect forecast's saving over the
                      best fixed choice that keeps, for each ratio of cost to avoided loss

Both use the scorer's own cases, pairs and day blocks, and all their maths goes through
metrics/. Usage:
    python -m tropics_scorecard.scorer.summary
"""
from __future__ import annotations

import sys

import pandas as pd

from ..metrics import bootstrap, categorical, errors, extremes
from ..paths import load_config
from ..sources import get_source
from . import core

OUT = core.OUT


def _models(cfg: dict) -> list[str]:
    return [s for s in core.sources_for(cfg, "day") if s not in core.BASELINES]


def _pairs(cfg: dict, name, variable: str, cases: pd.DataFrame) -> pd.DataFrame:
    """Pairs for a source given by name, or a source object (such as a climatology built from
    another history), with 6-hour totals summed from the hourly pairs."""
    src = get_source(name, cfg) if isinstance(name, str) else name
    if hasattr(src, "drop_flagged"):
        src.drop_flagged = True
    p = core.make_pairs(src, "rain_hourly" if variable == core.SIX_HOUR else variable, cases, ())
    return core.six_hour_totals(p, cfg) if variable == core.SIX_HOUR else p


def skill_rows(cfg: dict, variable: str, lead: int, cases: pd.DataFrame, clim, names, tag: str = "") -> list[dict]:
    """Percent change in MAE against a climatology, with the paired interval, for each source.

    cases carry the truth in "observed"; clim is the climatology source scored on the same
    cases. Only cases both sides forecast count, and days are paired before the interval."""
    fn = core.CONTINUOUS["mae"][0]
    base = "rain_hourly" if variable == core.SIX_HOUR else variable
    ref_pairs = _pairs(cfg, clim, variable, cases)
    rows = []
    for name in names:
        if core.excluded(cfg, name, base, "day", lead):
            continue
        try:
            p = _pairs(cfg, name, variable, cases)
        except LookupError:
            continue
        keep = ["station_key", "valid_time"]
        common = p.merge(ref_pairs[keep], on=keep)
        ref = ref_pairs.merge(common[keep], on=keep)
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
                     "percent": pct[0], "low": pct[1], "high": pct[2], "n_pairs": len(common), "n_days": len(a)})
        print(f"   skill{tag} {variable} day {lead} {name}: {pct[0]:+.1f}% ({pct[1]:+.1f} to {pct[2]:+.1f})", flush=True)
    return rows


def skill(cfg: dict) -> pd.DataFrame:
    """Percent change in MAE against climatology, judged by the stations, every lead day."""
    rows = []
    for variable in cfg["summary_scores"]["skill_variables"]:
        base = "rain_hourly" if variable == core.SIX_HOUR else variable
        for lead in cfg["lead_times"]["days"]:
            cases = core.cases_for(cfg, base, "day", lead)
            rows += skill_rows(cfg, variable, lead, cases, "climatology", _models(cfg))
    return pd.DataFrame(rows)


def _by_day(df: pd.DataFrame, cols: tuple[str, str]) -> tuple[list, list]:
    groups = df.groupby("day", sort=True)
    return [g[cols[0]].tolist() for _, g in groups], [g[cols[1]].tolist() for _, g in groups]


def extremes_table(cfg: dict, sources=None, leads=None) -> pd.DataFrame:
    """Relative quantile error of 6-hour rain totals, against gauges and against cell means."""
    s = cfg["summary_scores"]
    b = cfg["bootstrap"]
    rows = []
    for lead in leads or cfg["lead_times"]["days"]:
        cases = core.cases_for(cfg, "rain_hourly", "day", lead)
        for name in sources or _models(cfg):
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


def decision_table(cfg: dict, sources=None) -> pd.DataFrame:
    """Relative economic value of acting on each forecast's heavy-rain yes or no."""
    s = cfg["summary_scores"]
    b = cfg["bootstrap"]
    t = float(s["decision_threshold_mm"])
    rows = []
    names = sources or ["persistence"] + _models(cfg)
    for lead in cfg["lead_times"]["days"]:
        cases = core.cases_for(cfg, "rain_hourly", "day", lead)
        for window in s["decision_windows"]:
            for name in names:
                if core.excluded(cfg, name, "rain_hourly", "day", lead):
                    continue
                try:
                    p = _pairs(cfg, name, window, cases)
                except LookupError:
                    continue
                if p.empty:
                    continue
                yes, obs = p["forecast"] >= t, p["observed"] >= t
                counts = (pd.DataFrame({"day": p["day"], "h": yes & obs, "m": ~yes & obs, "fa": yes & ~obs,
                                        "cn": ~yes & ~obs}).groupby("day", sort=True)[["h", "m", "fa", "cn"]].sum())
                daily = [tuple(int(x) for x in r) for r in counts.itertuples(index=False)]
                total = tuple(int(x) for x in counts.sum())
                for a in s["cost_loss_ratios"]:
                    def value(counts, a=a):
                        return categorical.relative_economic_value(*counts, a)

                    try:
                        v, lo, hi = bootstrap.block_bootstrap_ci_statistic(
                            daily, value, int(b["block_length_days"]), n_resamples=int(b["resamples"]),
                            alpha=float(b["alpha"]), seed=int(b["seed"]))
                    except ValueError:
                        continue
                    rows.append({"source": name, "window": window, "lead": int(lead), "threshold": t,
                                 "cost_loss_ratio": float(a), "value": v, "low": lo, "high": hi,
                                 "hits": total[0], "misses": total[1], "false_alarms": total[2],
                                 "correct_negatives": total[3], "n_days": len(daily)})
                best = max((r for r in rows if r["source"] == name and r["window"] == window and r["lead"] == lead),
                           key=lambda r: r["value"], default=None)
                if best:
                    print(f"   decision day {lead} {window} {name}: best value {best['value']:+.3f} at "
                          f"C/L {best['cost_loss_ratio']} ({best['low']:+.3f} to {best['high']:+.3f}), "
                          f"hits {total[0]} of {total[0] + total[1]}", flush=True)
    return pd.DataFrame(rows)


def main(cfg: dict | None = None) -> int:
    cfg = cfg or load_config()
    core.check_ready(cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    skill(cfg).to_parquet(OUT / "skill.parquet", index=False)
    extremes_table(cfg).to_parquet(OUT / "extremes.parquet", index=False)
    decision_table(cfg).to_parquet(OUT / "decision.parquet", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
