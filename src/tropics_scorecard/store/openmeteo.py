"""Turn cached Open-Meteo responses into tidy forecast tables.

previous_<model>.parquet: model, cell_lat, cell_lon, cell_elevation_m, valid_time, variable,
    lead_day, value
single_<model>.parquet: model, run_time, cell_lat, cell_lon, cell_elevation_m, valid_time,
    variable, lead_hours, value

Times are UTC. Variables use this project's names (rain_hourly, temperature_2m,
wind_speed_10m). Rain is the total of the hour ending at valid_time; temperature and wind
are values at valid_time, wind in metres per second.

Usage:
    python -m tropics_scorecard.store.openmeteo
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import re
from pathlib import Path

import pandas as pd

from ..ingest.openmeteo import CACHE, VARIABLES
from ..paths import TABLES

OUT = TABLES / "openmeteo"
OURS = {v: k for k, v in VARIABLES.items()}
PREVIOUS_KEY = re.compile(r"^(?P<var>.+)_previous_day(?P<day>\d+)$")


def _read(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def parse_previous(body: dict, model: str) -> pd.DataFrame:
    hourly = body.get("hourly") or {}
    times = pd.to_datetime(hourly.get("time") or [], utc=True)
    frames = []
    for key, values in hourly.items():
        m = PREVIOUS_KEY.match(key)
        if not m or m["var"] not in OURS:
            continue
        frames.append(pd.DataFrame({"valid_time": times, "variable": OURS[m["var"]],
                                    "lead_day": int(m["day"]), "value": pd.to_numeric(pd.Series(values), errors="coerce")}))
    if not frames:
        return pd.DataFrame(columns=["model", "cell_lat", "cell_lon", "cell_elevation_m", "valid_time", "variable", "lead_day", "value"])
    df = pd.concat(frames, ignore_index=True)
    df.insert(0, "cell_elevation_m", body.get("elevation"))
    df.insert(0, "cell_lon", round(float(body["longitude"]), 4))
    df.insert(0, "cell_lat", round(float(body["latitude"]), 4))
    df.insert(0, "model", model)
    return df


def parse_single(body: dict | list, model: str, run_time: dt.datetime) -> pd.DataFrame:
    run = pd.Timestamp(run_time, tz="UTC")
    frames = []
    for loc in body if isinstance(body, list) else [body]:
        hourly = loc.get("hourly") or {}
        times = pd.to_datetime(hourly.get("time") or [], utc=True)
        lead = ((times - run) / pd.Timedelta(hours=1)).astype(int)
        for key, values in hourly.items():
            if key not in OURS:
                continue
            frames.append(pd.DataFrame({
                "model": model, "run_time": run, "cell_lat": round(float(loc["latitude"]), 4),
                "cell_lon": round(float(loc["longitude"]), 4), "cell_elevation_m": loc.get("elevation"),
                "valid_time": times, "variable": OURS[key], "lead_hours": lead,
                "value": pd.to_numeric(pd.Series(values), errors="coerce")}))
    if not frames:
        return pd.DataFrame(columns=["model", "run_time", "cell_lat", "cell_lon", "cell_elevation_m",
                                     "valid_time", "variable", "lead_hours", "value"])
    return pd.concat(frames, ignore_index=True)


def build_previous(model: str) -> Path | None:
    files = sorted((CACHE / "previous" / model).glob("*/*.json.gz"))
    if not files:
        return None
    df = pd.concat([parse_previous(_read(p), model) for p in files], ignore_index=True)
    df = df.drop_duplicates(["cell_lat", "cell_lon", "valid_time", "variable", "lead_day"], keep="last")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"previous_{model}.parquet"
    df.to_parquet(path, index=False)
    return path


def build_single(model: str) -> Path | None:
    files = sorted((CACHE / "single" / model).glob("*/*/*.json.gz"))
    if not files:
        return None
    frames = []
    for p in files:
        run = dt.datetime.strptime(p.parent.name, "%Y-%m-%dT%H")
        frames.append(parse_single(_read(p), model, run))
    df = pd.concat(frames, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"single_{model}.parquet"
    df.to_parquet(path, index=False)
    return path


def main(argv=None) -> int:
    for kind, build in (("previous", build_previous), ("single", build_single)):
        root = CACHE / kind
        for model_dir in sorted(root.glob("*")) if root.exists() else []:
            print(kind, model_dir.name, build(model_dir.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
