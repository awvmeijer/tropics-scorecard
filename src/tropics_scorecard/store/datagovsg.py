"""Turn cached data.gov.sg pages into tidy tables.

readings: station_id, time_utc, time_local, variable, value, unit, reading_type
stations: station_id, name, latitude, longitude, variable, first_day, last_day
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd

from ..ingest.datagovsg import CACHE
from ..paths import TABLES

OUT = TABLES / "datagovsg"


def _pages(variable: str, year: int | None = None):
    root = CACHE / variable
    pattern = f"{year}/*/p*.json.gz" if year else "*/*/p*.json.gz"
    for path in sorted(root.glob(pattern)):
        if (path.parent / "DONE").exists():
            yield path


def parse_page(body: dict, variable: str) -> tuple[list[dict], list[dict]]:
    data = body.get("data") or {}
    unit = data.get("readingUnit")
    rtype = data.get("readingType")
    rows = []
    for reading in data.get("readings") or []:
        stamp = reading["timestamp"]
        for item in reading.get("data") or []:
            rows.append(
                {"station_id": item["stationId"], "time": stamp, "variable": variable,
                 "value": item.get("value"), "unit": unit, "reading_type": rtype}
            )
    stations = [
        {"station_id": s["id"], "name": s.get("name"), "latitude": s["location"]["latitude"],
         "longitude": s["location"]["longitude"]}
        for s in data.get("stations") or []
    ]
    return rows, stations


def build(variable: str, year: int) -> Path | None:
    rows, stations = [], []
    for path in _pages(variable, year):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            r, s = parse_page(json.load(fh), variable)
        day = path.parent.name
        rows += r
        stations += [{**x, "day": day} for x in s]
    if not rows:
        return None
    df = pd.DataFrame(rows)
    t = pd.to_datetime(df.pop("time"), format="ISO8601")
    df["time_utc"] = t.dt.tz_convert("UTC")
    df["time_local"] = t.dt.tz_convert("Asia/Singapore").dt.tz_localize(None)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[["station_id", "time_utc", "time_local", "variable", "value", "unit", "reading_type"]]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"readings_{variable}_{year}.parquet"
    df.to_parquet(path, index=False)
    st = pd.DataFrame(stations)
    st = (st.groupby(["station_id", "name", "latitude", "longitude"], as_index=False)
            .agg(first_day=("day", "min"), last_day=("day", "max")))
    st["variable"] = variable
    st.to_parquet(OUT / f"stations_{variable}_{year}.parquet", index=False)
    return path


def build_snapshots(variable: str, year: int) -> Path | None:
    """Hourly snapshot files to the same tidy layout, written as snapshots_<variable>_<year>."""
    rows, stations = [], []
    for path in sorted((CACHE / f"{variable}-snapshots" / str(year)).glob("*/*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            r, s = parse_page(json.load(fh), variable)
        rows += r
        stations += [{**x, "day": path.parent.name} for x in s]
    if not rows:
        return None
    df = pd.DataFrame(rows)
    t = pd.to_datetime(df.pop("time"), format="ISO8601")
    df["time_utc"] = t.dt.tz_convert("UTC")
    df["time_local"] = t.dt.tz_convert("Asia/Singapore").dt.tz_localize(None)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[["station_id", "time_utc", "time_local", "variable", "value", "unit", "reading_type"]]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"snapshots_{variable}_{year}.parquet"
    df.to_parquet(path, index=False)
    st = (pd.DataFrame(stations).groupby(["station_id", "name", "latitude", "longitude"], as_index=False)
            .agg(first_day=("day", "min"), last_day=("day", "max")))
    st["variable"] = variable
    st.to_parquet(OUT / f"stations_{variable}_{year}.parquet", index=False)
    return path


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("variable")
    ap.add_argument("years", type=int, nargs="+")
    ap.add_argument("--snapshots", action="store_true")
    args = ap.parse_args(argv)
    for y in args.years:
        p = build_snapshots(args.variable, y) if args.snapshots else build(args.variable, y)
        print(args.variable, y, p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
