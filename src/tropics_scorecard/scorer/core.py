"""Scorer internals. See the package docstring for the rules."""
from __future__ import annotations

import math
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from ..match import observations
from ..metrics import bootstrap, categorical, errors, probabilistic
from ..paths import TABLES
from ..sources import ForecastSource, get_source

OUT = TABLES / "results"
VARIABLES = ("rain_hourly", "temperature_2m", "wind_speed_10m")
RESULT_COLUMNS = ["source", "against", "variable", "lead_kind", "lead", "station", "hour_local", "regime",
                  "qc", "metric", "threshold", "value", "low", "high", "n_pairs", "n_days"]
GROUPS = {"all": [], "hour_local": ["hour_local"], "regime": ["regime"], "station": ["station_key"]}
BASELINES = ("persistence", "climatology")


class NotReady(RuntimeError):
    """The protocol has not been signed off, so nothing may be scored."""


def _mse(forecast, observed):
    return errors.rmse(forecast, observed) ** 2


def _brier(probabilities, outcomes):
    return probabilistic.brier_score(probabilities, outcomes)


# metric name -> (daily function, columns it takes, transform of the bootstrap output)
CONTINUOUS = {
    "bias": (lambda f, o: errors.bias(f, o), ("forecast", "observed"), None),
    "mae": (lambda f, o: errors.mae(f, o), ("forecast", "observed"), None),
    "rmse": (_mse, ("forecast", "observed"), lambda x: math.sqrt(max(x, 0.0))),
}
CONTINGENCY = ("pod", "far", "csi", "ets")


# ---------------------------------------------------------------- cases and pairs

def regime(local: pd.Series, regimes: dict) -> pd.Series:
    md = local.dt.strftime("%m-%d")
    out = pd.Series("none", index=local.index, dtype=object)
    for name, r in regimes.items():
        s, e = r["start"], r["end"]
        inside = (md >= s) & (md <= e) if s <= e else (md >= s) | (md <= e)
        out[inside] = name
    return out


def _period(cfg: dict, lead_kind: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    per = cfg["period"]["day_level_lead_times" if lead_kind == "day" else "hour_level_lead_times"]
    return pd.Timestamp(str(per["start"]), tz="UTC"), pd.Timestamp(f"{per['end']} 23:00", tz="UTC")


def annotate(cases: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    local = cases["valid_time"].dt.tz_convert(cfg["region"]["local_timezone"])
    return cases.assign(day=local.dt.strftime("%Y-%m-%d"), hour_local=local.dt.hour.astype(str),
                        regime=regime(local, cfg["regimes"]))


def cases_for(cfg: dict, variable: str, lead_kind: str, lead: int, drop_flagged: bool = True,
              reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """Every reference value in the period, as a case for this lead time."""
    start, end = _period(cfg, lead_kind)
    obs = reference if reference is not None else observations.load(variable, start, end, drop_flagged=drop_flagged)
    obs = obs[(obs["time_utc"] >= start) & (obs["time_utc"] <= end)]
    c = obs.rename(columns={"time_utc": "valid_time", "value": "observed"})[["station_key", "valid_time", "observed"]]
    if lead_kind == "hour":
        run = c["valid_time"] - pd.Timedelta(hours=int(lead))
        c = c[run.dt.hour.isin(cfg["lead_times"]["single_run_hours_utc"]) & (run >= start)]
    c = c.assign(lead_kind=lead_kind, lead=int(lead)).reset_index(drop=True)
    return annotate(c, cfg)


def make_pairs(source: ForecastSource, variable: str, cases: pd.DataFrame, thresholds) -> pd.DataFrame:
    p = cases.copy()
    p["forecast"] = source.predict(variable, cases).to_numpy()
    p = p.dropna(subset=["forecast"]).reset_index(drop=True)
    if variable == "rain_hourly":
        deterministic = getattr(source, "deterministic", True)
        for t in thresholds:
            p[f"obs_{t}"] = (p["observed"] >= t).astype(int)
            if deterministic:
                p[f"prob_{t}"] = (p["forecast"] >= t).astype(float)
                p[f"yes_{t}"] = p["forecast"] >= t
            else:
                p[f"prob_{t}"] = source.probability(variable, p, t).to_numpy()
                p[f"yes_{t}"] = source.says_yes(variable, p, t).fillna(False).to_numpy().astype(bool)
    return p


# ---------------------------------------------------------------- scores

def daily_values(p: pd.DataFrame, keys: list[str], fn, cols) -> dict[tuple, tuple[list, list]]:
    """For each group, the days in order and the metric's value on each day."""
    arrays = [p[c].to_numpy() for c in cols]
    out: dict[tuple, tuple[list, list]] = {}
    if p.empty:
        return out
    for k, idx in p.groupby(keys + ["day"], sort=True, observed=True).indices.items():
        k = k if isinstance(k, tuple) else (k,)
        v = fn(*[a[idx].tolist() for a in arrays])
        if v is None:
            continue
        days, vals = out.setdefault(k[:-1], ([], []))
        days.append(k[-1])
        vals.append(float(v))
    return out


def interval(values_a: list, values_b: list | None, cfg: dict):
    """(mean difference, low, high) from the block bootstrap, or None when too few days."""
    b = cfg["bootstrap"]
    block = int(b["block_length_days"])
    if len(values_a) < 2 * block:
        return None
    other = values_b if values_b is not None else [0.0] * len(values_a)
    return bootstrap.block_bootstrap_ci_mean_diff(values_a, other, block, n_resamples=int(b["resamples"]),
                                                  alpha=float(b["alpha"]), seed=int(b["seed"]))


def _row(meta: dict, group: str, gk: tuple, **kw) -> dict:
    labels = {"station": "all", "hour_local": "all", "regime": "all"}
    if group != "all":
        labels["station" if group == "station" else group] = gk[0]
    return {**meta, **labels, **kw}


def _size(p: pd.DataFrame, keys: list[str]) -> dict[tuple, int]:
    if not keys:
        return {(): len(p)}
    return {(k if isinstance(k, tuple) else (k,)): int(n) for k, n in p.groupby(keys, observed=True).size().items()}


def score_pairs(p: pd.DataFrame, meta: dict, cfg: dict, groups=("all",), metrics=None, thresholds=()) -> list[dict]:
    """Single-source scores for one set of pairs. meta holds source, variable, lead, qc."""
    rows = []
    metrics = metrics or tuple(CONTINUOUS)
    for group in groups:
        keys = GROUPS[group]
        sizes = _size(p, keys)
        for name in metrics:
            fn, cols, post = CONTINUOUS[name]
            for gk, (days, vals) in daily_values(p, keys, fn, cols).items():
                ci = interval(vals, None, cfg)
                if ci is None:
                    continue
                m, lo, hi = (post(x) for x in ci) if post else ci
                rows.append(_row(meta, group, gk, against=None, metric=name, threshold=None, value=m, low=lo,
                                 high=hi, n_pairs=sizes[gk], n_days=len(days)))
        for t in thresholds:
            for gk, (days, vals) in daily_values(p, keys, _brier, (f"prob_{t}", f"obs_{t}")).items():
                ci = interval(vals, None, cfg)
                if ci is None:
                    continue
                rows.append(_row(meta, group, gk, against=None, metric="brier", threshold=t, value=ci[0], low=ci[1],
                                 high=ci[2], n_pairs=sizes[gk], n_days=len(days)))
            if group == "station":
                continue
            parts = p.groupby(keys, observed=True) if keys else [((), p)]
            for gk, sub in parts:
                gk = gk if isinstance(gk, tuple) else (gk,)
                table = categorical.contingency(sub[f"yes_{t}"].tolist(), (sub[f"obs_{t}"] == 1).tolist())
                n_days = sub["day"].nunique()
                for name in CONTINGENCY:
                    v = getattr(categorical, name)(*table)
                    rows.append(_row(meta, group, gk, against=None, metric=name, threshold=t, value=v, low=None,
                                     high=None, n_pairs=len(sub), n_days=n_days))
                h, mi, fa, _ = table
                for name, v in (("observed_events", h + mi), ("forecast_events", h + fa)):
                    rows.append(_row(meta, group, gk, against=None, metric=name, threshold=t, value=v, low=None,
                                     high=None, n_pairs=len(sub), n_days=n_days))
    return rows


def compare_pairs(pa: pd.DataFrame, pb: pd.DataFrame, meta: dict, against: str, cfg: dict, groups=("all",),
                  thresholds=()) -> list[dict]:
    """A minus B on the cases both forecast: MAE, and the Brier score for each threshold."""
    keep = ["station_key", "valid_time"]
    common = pa.merge(pb[keep], on=keep)
    pb = pb.merge(common[keep], on=keep)
    rows = []
    specs = [("mae", None, CONTINUOUS["mae"][0], ("forecast", "observed"))]
    specs += [("brier", t, _brier, (f"prob_{t}", f"obs_{t}")) for t in thresholds]
    for group in groups:
        keys = GROUPS[group]
        sizes = _size(common, keys)
        for name, t, fn, cols in specs:
            da, db = daily_values(common, keys, fn, cols), daily_values(pb, keys, fn, cols)
            for gk, (days, va) in da.items():
                if gk not in db:
                    continue
                lookup = dict(zip(*db[gk]))
                pairs = [(x, lookup[d]) for d, x in zip(days, va) if d in lookup]
                if not pairs:
                    continue
                a, b = [x for x, _ in pairs], [y for _, y in pairs]
                ci = interval(a, b, cfg)
                if ci is None:
                    continue
                rows.append(_row(meta, group, gk, against=against, metric=name, threshold=t, value=ci[0],
                                 low=ci[1], high=ci[2], n_pairs=sizes[gk], n_days=len(a)))
    return rows


# ---------------------------------------------------------------- jobs

def check_ready(cfg: dict) -> None:
    if cfg.get("proposals_accepted") is not True:
        raise NotReady("config proposals_accepted is not true: the verification protocol is not signed off, "
                       "so nothing is scored")
    if str(cfg["bootstrap"].get("block_length_days", "TODO")).upper() == "TODO":
        raise NotReady("bootstrap.block_length_days is not fixed yet (protocol section 7)")


def sources_for(cfg: dict, lead_kind: str) -> list[str]:
    models = [m for m in cfg["forecast_sources"] if m not in BASELINES]
    if lead_kind == "hour":
        return ["persistence_issue", "persistence", "climatology"] + models
    return ["persistence", "climatology"] + models + [m["id"] for m in cfg.get("secondary_forecast_sources") or []]


def comparisons_for(cfg: dict, lead_kind: str) -> list[tuple[str, str]]:
    models = [m for m in cfg["forecast_sources"] if m not in BASELINES]
    extra = [] if lead_kind == "hour" else [m["id"] for m in cfg.get("secondary_forecast_sources") or []]
    base = ["persistence_issue", "persistence", "climatology"] if lead_kind == "hour" else list(BASELINES)
    out = [(m, b) for m in models + extra for b in base]
    out += [(a, b) for i, a in enumerate(models) for b in models[i + 1:]]
    return out


def excluded(cfg: dict, source: str, variable: str, lead_kind: str, lead: int) -> bool:
    """True when config lists this source, variable and lead as a known archive fault."""
    for e in cfg.get("exclusions") or []:
        if (e["source"] == source and e["variable"] == variable and e["lead_kind"] == lead_kind
                and int(lead) in [int(x) for x in e["leads"]]):
            return True
    return False


SIX_HOUR = "rain_6h"


def six_hour_totals(p: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Hourly rain pairs summed to 6-hour totals ending 00, 06, 12 and 18 UTC.

    A window counts only when all six hours have both a forecast and an observation.
    Sums of forecast and observed are plain additions of matched values, not a metric.
    """
    if p.empty:
        return p
    end = p["valid_time"].dt.ceil("6h")
    g = p.assign(valid_time=end).groupby(["station_key", "valid_time"], sort=False)
    out = g.agg(forecast=("forecast", "sum"), observed=("observed", "sum"), n=("observed", "size")).reset_index()
    out = out[out["n"] == 6].drop(columns="n")
    out = out.assign(lead_kind=p["lead_kind"].iloc[0], lead=int(p["lead"].iloc[0]))
    return annotate(out, cfg).reset_index(drop=True)


def job(cfg: dict, variable: str, lead_kind: str, lead: int, qc: str) -> list[dict]:
    """Everything for one variable, lead time and quality-control variant."""
    drop = qc == "flags_removed"
    six = variable == SIX_HOUR
    label, variable = variable, ("rain_hourly" if six else variable)
    thresholds = tuple(cfg["rain_thresholds_mm_per_hour"]) if variable == "rain_hourly" and not six else ()
    full = drop and lead_kind == "day"
    groups = ("all", "hour_local", "regime", "station") if full else ("all",)
    cmp_groups = ("all", "hour_local", "regime") if full else ("all",)
    cases = cases_for(cfg, variable, lead_kind, lead, drop_flagged=drop)
    meta = {"variable": label, "lead_kind": lead_kind, "lead": int(lead), "qc": qc}
    pairs, rows = {}, []
    for name in sources_for(cfg, lead_kind):
        if excluded(cfg, name, variable, lead_kind, lead):
            continue
        src = get_source(name, cfg)
        if hasattr(src, "drop_flagged"):
            src.drop_flagged = drop
        try:
            pairs[name] = make_pairs(src, variable, cases, thresholds)
            if six:
                pairs[name] = six_hour_totals(pairs[name], cfg)
        except LookupError as err:  # a forecast table that is not built yet
            print(f"skip {name}: {err}", flush=True)
            continue
        if pairs[name].empty:
            continue
        # Single scores: station breakdown only for bias and MAE, to keep the run short.
        rows += score_pairs(pairs[name], {**meta, "source": name}, cfg, tuple(g for g in groups if g != "station"),
                            thresholds=thresholds)
        if "station" in groups:
            rows += score_pairs(pairs[name], {**meta, "source": name}, cfg, ("station",), metrics=("bias", "mae"))
    for a, b in comparisons_for(cfg, lead_kind):
        if a in pairs and b in pairs and not pairs[a].empty and not pairs[b].empty:
            rows += compare_pairs(pairs[a], pairs[b], {**meta, "source": a}, b, cfg, cmp_groups, thresholds)
    if full:  # grid-cell sensitivity check, protocol 3.1
        rule = cfg["matching"]["cell_rule_sensitivity"]
        for m in [m for m in cfg["forecast_sources"] if m not in BASELINES]:
            if m not in pairs:
                continue
            alt = get_source(m, cfg, cell_rule=rule)
            try:
                pa = make_pairs(alt, variable, cases, thresholds)
                if six:
                    pa = six_hour_totals(pa, cfg)
            except LookupError:
                continue
            rows += score_pairs(pa, {**meta, "source": alt.name}, cfg, ("all",), metrics=("bias", "mae"),
                                thresholds=thresholds[:1])
            rows += compare_pairs(pa, pairs[m], {**meta, "source": alt.name}, m, cfg, ("all",), thresholds[:1])
    return rows


def _job(args):
    return job(*args)


def jobs(cfg: dict, variables=VARIABLES) -> list[tuple]:
    out = []
    for v in variables:
        for d in cfg["lead_times"]["days"]:
            out += [(cfg, v, "day", int(d), "flags_removed"), (cfg, v, "day", int(d), "flags_kept")]
        for h in range(1, int(cfg["lead_times"]["hours"]["max"]) + 1):
            out.append((cfg, v, "hour", h, "flags_removed"))
    if "rain_hourly" in variables:  # 6-hour totals, protocol section 4 (added 2026-11-13)
        out += [(cfg, SIX_HOUR, "day", int(d), "flags_removed") for d in cfg["lead_times"]["days"]]
    return out


def to_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    return df.astype({"station": str, "hour_local": str, "regime": str})


def run(source: ForecastSource | str, cfg: dict, variables=VARIABLES, lead_kinds=("day",)) -> pd.DataFrame:
    """Tidy results for one forecast source, main table only (quality-control flags removed)."""
    check_ready(cfg)
    rows = []
    for v in variables:
        thresholds = tuple(cfg["rain_thresholds_mm_per_hour"]) if v == "rain_hourly" else ()
        for kind in lead_kinds:
            leads = cfg["lead_times"]["days"] if kind == "day" else range(1, int(cfg["lead_times"]["hours"]["max"]) + 1)
            src = get_source(source, cfg) if isinstance(source, str) else source  # caches live in the source
            for lead in leads:
                p = make_pairs(src, v, cases_for(cfg, v, kind, int(lead)), thresholds)
                meta = {"source": src.name, "variable": v, "lead_kind": kind, "lead": int(lead), "qc": "flags_removed"}
                rows += score_pairs(p, meta, cfg, ("all", "hour_local", "regime"), thresholds=thresholds)
    return to_frame(rows)


def run_all(cfg: dict, variables=VARIABLES, workers: int | None = None) -> pd.DataFrame:
    """Every source, every comparison, every lead time. Writes data/tables/results/results.parquet."""
    check_ready(cfg)
    work = jobs(cfg, variables)
    workers = workers or max(1, (os.cpu_count() or 2) - 2)
    rows: list[dict] = []
    if workers == 1:
        for t in work:
            rows += job(*t)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for i, r in enumerate(ex.map(_job, work, chunksize=1), 1):
                rows += r
                if i % 10 == 0 or i == len(work):
                    print(f"scored {i}/{len(work)} jobs", flush=True)
    df = to_frame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / "results.parquet", index=False)
    return df


def summary_numbers(df: pd.DataFrame) -> dict:
    """A few counts for the run log."""
    return {"rows": len(df), "sources": sorted(df["source"].unique().tolist()) if len(df) else [],
            "with_interval": int(df["low"].notna().sum()) if len(df) else 0,
            "lead_days": sorted(np.unique(df.loc[df["lead_kind"] == "day", "lead"]).tolist()) if len(df) else []}
