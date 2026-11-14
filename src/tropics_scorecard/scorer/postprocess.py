"""A small trained model: does station data unlock the information in the raw forecasts?

Added 14 November 2026 (protocol change log). The raw forecasts lose to climatology at the
stations. This asks whether that is because they carry no information, or because nobody
has fitted them to the instruments.

The model is deliberately plain: ordinary least squares on
    the station climatology for that hour, the ECMWF and GFS forecasts one day ahead,
    hour of day and day of year (as sine and cosine), and the station's latitude and longitude.
It is fitted on the first part of the test period and scored only on the later part
(config `postprocess.train_until`), so no scored hour was seen in training. Stations that
joined the network after the split are scored apart: the model never saw them at all.

A gradient-boosted model on the same inputs is fitted too when scikit-learn is installed
(`uv sync --extra ml`), as a check that the plain model is not leaving much behind.

Writes data/tables/results/postprocess.parquet. Usage:
    python -m tropics_scorecard.scorer.postprocess
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from ..paths import TABLES, load_config
from . import core, summary

OUT = core.OUT
VARIABLES = ["temperature_2m", "wind_speed_10m", core.SIX_HOUR]
INPUTS = ["climatology", "ecmwf_ifs025", "gfs_global", "hour_sin", "hour_cos", "year_sin", "year_cos", "lat", "lon"]
KEYS = ["station_key", "valid_time"]


def table(cfg: dict, variable: str) -> pd.DataFrame:
    """One row per case that climatology, ECMWF and GFS all forecast, with the model inputs."""
    base = "rain_hourly" if variable == core.SIX_HOUR else variable
    cases = core.cases_for(cfg, base, "day", 1)
    t = summary._pairs(cfg, "climatology", variable, cases).rename(columns={"forecast": "climatology"})
    for name in ("ecmwf_ifs025", "gfs_global"):
        f = summary._pairs(cfg, name, variable, cases)[KEYS + ["forecast"]].rename(columns={"forecast": name})
        t = t.merge(f, on=KEYS)
    local = t["valid_time"].dt.tz_convert(cfg["region"]["local_timezone"])
    hour, day = 2 * np.pi * local.dt.hour / 24, 2 * np.pi * local.dt.day_of_year / 365.25
    pos = pd.read_parquet(TABLES / "openmeteo" / "grid.parquet").drop_duplicates("station_key").set_index("station_key")
    return t.assign(hour_sin=np.sin(hour), hour_cos=np.cos(hour), year_sin=np.sin(day), year_cos=np.cos(day),
                    lat=t["station_key"].map(pos["station_lat"]), lon=t["station_key"].map(pos["station_lon"]))


def fit_linear(train: pd.DataFrame):
    """Least squares with an intercept. Returns a function from a table to predictions."""
    x = np.column_stack([np.ones(len(train))] + [train[c].to_numpy(float) for c in INPUTS])
    coef, *_ = np.linalg.lstsq(x, train["observed"].to_numpy(float), rcond=None)
    return lambda d: np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in INPUTS]) @ coef, coef


def fit_boosted(train: pd.DataFrame):
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
    except ImportError:
        return None
    model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, random_state=0)
    model.fit(train[INPUTS].to_numpy(float), train["observed"].to_numpy(float))
    return lambda d: model.predict(d[INPUTS].to_numpy(float))


def run(cfg: dict) -> pd.DataFrame:
    split = pd.Timestamp(str(cfg["postprocess"]["train_until"]), tz="UTC") + pd.Timedelta(days=1)
    rows = []
    for variable in VARIABLES:
        t = table(cfg, variable)
        train, test = t[t["valid_time"] < split], t[t["valid_time"] >= split]
        seen = set(train["station_key"])
        linear, coef = fit_linear(train)
        models = {"linear": linear, "boosted": fit_boosted(train)}
        groups = {"stations in training": test[test["station_key"].isin(seen)],
                  "stations never seen": test[~test["station_key"].isin(seen)]}
        for group, d in groups.items():
            if d.empty:
                continue
            ref = d.assign(forecast=d["climatology"])
            candidates = {"ecmwf_ifs025": d["ecmwf_ifs025"].to_numpy(float), "gfs_global": d["gfs_global"].to_numpy(float)}
            candidates.update({name: fn(d) for name, fn in models.items() if fn is not None})
            for name, values in candidates.items():
                if variable == core.SIX_HOUR:
                    values = np.clip(values, 0, None)  # a rain total cannot be negative
                p = d.assign(forecast=values)
                for score in ("rmse", "mae"):
                    got = summary.paired_change(p, ref, cfg, score)
                    if got is None:
                        continue
                    rows.append({"variable": variable, "group": group, "model": name, "score": score,
                                 "percent": got["percent"][0], "low": got["percent"][1], "high": got["percent"][2],
                                 "n_pairs": len(d), "n_stations": d["station_key"].nunique(), "n_days": got["n_days"],
                                 "n_train": len(train)})
                    print(f"   postprocess {variable} {group} {name} {score}: {got['percent'][0]:+.1f}% "
                          f"({got['percent'][1]:+.1f} to {got['percent'][2]:+.1f})", flush=True)
        print(f"   {variable} linear coefficients: " + ", ".join(f"{n} {c:+.3f}" for n, c in zip(["intercept"] + INPUTS, coef)), flush=True)
    return pd.DataFrame(rows)


def main(cfg: dict | None = None) -> int:
    cfg = cfg or load_config()
    core.check_ready(cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    run(cfg).to_parquet(OUT / "postprocess.parquet", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
