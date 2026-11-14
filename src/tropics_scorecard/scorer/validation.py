"""Validation of the study itself: how much can a forecast be expected to match a station?

Added 14 November 2026 (protocol change log). Three tables, all for one day ahead:

    evaluation.parquet  the statistics used in regional model evaluation, for every source:
                        mean bias, normalised mean bias, mean absolute error, root mean
                        square error, correlation, index of agreement, and the correlation
                        of anomalies from climatology
    neighbours.parquet  how well two gauges agree, by the distance between them: the scale
                        over which rain at a point stops being predictable from nearby rain
    ceiling.parquet     a perfect forecast at ECMWF's grid size, scored at single gauges. The
                        "forecast" for a gauge is the mean of the other gauges in its cell, so
                        it knows the true cell rain and nothing below the cell. What it scores
                        is the best any 0.25 degree forecast could do at a point

Usage:
    python -m tropics_scorecard.scorer.validation
"""
from __future__ import annotations

import itertools
import math
import sys

import pandas as pd

from ..metrics import agreement, errors, geo
from ..paths import TABLES, load_config
from ..sources import ForecastSource, get_source
from . import core, summary

OUT = core.OUT
SOURCES = ["gfs_global", "ecmwf_ifs025", "ecmwf_aifs025_single", "ecmwf_ifs", "era5", "persistence", "climatology"]
VARIABLES = ["temperature_2m", "wind_speed_10m", "rain_hourly", core.SIX_HOUR]
DISTANCE_BINS_KM = [0, 2, 4, 8, 15, 30]
MIN_SHARED = 500  # 6-hour windows two gauges must share to count as a pair


def evaluation(cfg: dict) -> pd.DataFrame:
    rows = []
    for variable in VARIABLES:
        base = "rain_hourly" if variable == core.SIX_HOUR else variable
        cases = core.cases_for(cfg, base, "day", 1)
        clim = summary._pairs(cfg, "climatology", variable, cases)[["station_key", "valid_time", "forecast"]]
        clim = clim.rename(columns={"forecast": "climatology"})
        for name in SOURCES:
            try:
                p = summary._pairs(cfg, name, variable, cases).merge(clim, on=["station_key", "valid_time"])
            except LookupError:
                continue
            f, o, c = p["forecast"].tolist(), p["observed"].tolist(), p["climatology"].tolist()
            nmb = agreement.normalised_mean_bias(f, o)
            rows.append({"source": name, "variable": variable, "n_pairs": len(p),
                         "mean_bias": errors.bias(f, o), "normalised_mean_bias_pct": None if nmb is None else 100 * nmb,
                         "mae": errors.mae(f, o), "rmse": errors.rmse(f, o),
                         "correlation": agreement.correlation(f, o),
                         "index_of_agreement": agreement.index_of_agreement(f, o),
                         "anomaly_correlation": None if name == "climatology" else agreement.anomaly_correlation(f, o, c)})
            print(f"   evaluation {variable} {name}: r {rows[-1]['correlation']:.2f}", flush=True)
    return pd.DataFrame(rows)


def _six_hour_wide(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Observed 6-hour totals, one column per gauge, and the gauge positions."""
    cases = core.cases_for(cfg, "rain_hourly", "day", 1)
    totals = core.six_hour_totals(cases.assign(forecast=0.0), cfg)
    wide = totals.pivot(index="valid_time", columns="station_key", values="observed")
    grid = pd.read_parquet(TABLES / "openmeteo" / "grid.parquet").drop_duplicates("station_key")
    return wide, grid.set_index("station_key")[["station_lat", "station_lon"]]


def neighbours(cfg: dict) -> pd.DataFrame:
    wide, pos = _six_hour_wide(cfg)
    rows = []
    for a, b in itertools.combinations(wide.columns, 2):
        both = wide[[a, b]].dropna()
        if len(both) < MIN_SHARED:
            continue
        x, y = both[a].tolist(), both[b].tolist()
        r = agreement.correlation(x, y)
        if r is None:
            continue
        rows.append({"a": a, "b": b, "km": geo.haversine_km(*pos.loc[a], *pos.loc[b]), "n": len(both),
                     "correlation": r, "rmse": errors.rmse(x, y), "mae": errors.mae(x, y)})
    pairs = pd.DataFrame(rows)
    pairs["bin"] = pd.cut(pairs["km"], DISTANCE_BINS_KM + [math.inf], labels=[f"{lo} to {hi} km" for lo, hi in
                          zip(DISTANCE_BINS_KM, DISTANCE_BINS_KM[1:])] + [f"over {DISTANCE_BINS_KM[-1]} km"])
    out = pairs.groupby("bin", observed=True).agg(pairs=("km", "size"), km=("km", "mean"), correlation=("correlation", "mean"),
                                                 rmse=("rmse", "mean"), mae=("mae", "mean")).reset_index()
    print(out.round(3).to_string(index=False), flush=True)
    return out


class PerfectCell(ForecastSource):
    """For each gauge and 6-hour window, the mean of the other gauges in its grid cell."""
    name = "perfect_cell"

    def __init__(self, cfg: dict, model: str = "ecmwf_ifs025"):
        self.cfg, self.cells = cfg, get_source(model, cfg).cells

    def six_hour(self, pairs: pd.DataFrame) -> pd.DataFrame:
        p = pairs.merge(self.cells, on="station_key")
        g = p.groupby(["cell_lat", "cell_lon", "valid_time"])["observed"]
        n = g.transform("size")
        p = p.assign(forecast=(g.transform("sum") - p["observed"]) / (n - 1), n=n)
        p = p[p["n"] >= int(self.cfg["summary_scores"]["cell_mean_min_gauges"])]
        return p.drop(columns=["cell_lat", "cell_lon", "n"]).reset_index(drop=True)


def ceiling(cfg: dict) -> pd.DataFrame:
    """The perfect cell forecast and ECMWF's, on the same gauge-windows, against climatology."""
    cases = core.cases_for(cfg, "rain_hourly", "day", 1)
    keep = ["station_key", "valid_time"]
    perfect = PerfectCell(cfg).six_hour(core.six_hour_totals(cases.assign(forecast=0.0), cfg))
    clim = summary._pairs(cfg, "climatology", core.SIX_HOUR, cases).merge(perfect[keep], on=keep)
    rows = []
    for name, p in (("perfect_cell", perfect), ("ecmwf_ifs025", summary._pairs(cfg, "ecmwf_ifs025", core.SIX_HOUR, cases).merge(perfect[keep], on=keep)),
                    ("climatology", clim)):
        row = {"source": name, "n_pairs": len(p), "correlation": agreement.correlation(p["forecast"].tolist(), p["observed"].tolist()),
               "rmse": errors.rmse(p["forecast"].tolist(), p["observed"].tolist())}
        if name != "climatology":
            common = p.merge(clim[keep], on=keep)
            row["percent"], row["low"], row["high"] = summary.paired_change(common, clim.merge(common[keep], on=keep), cfg, "rmse")["percent"]
        rows.append(row)
        print(f"   ceiling {name}: r {row['correlation']:.2f}, RMSE {row['rmse']:.2f}", flush=True)
    return pd.DataFrame(rows)


def main(cfg: dict | None = None) -> int:
    cfg = cfg or load_config()
    core.check_ready(cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    evaluation(cfg).to_parquet(OUT / "evaluation.parquet", index=False)
    neighbours(cfg).to_parquet(OUT / "neighbours.parquet", index=False)
    ceiling(cfg).to_parquet(OUT / "ceiling.parquet", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
