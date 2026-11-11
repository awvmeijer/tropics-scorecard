"""Turn cached data.gov.sg responses into tidy tables.

readings: station_id, time_utc, time_local, variable, value, unit, reading_type
stations: station_id, name, latitude, longitude, variable, first_day, last_day

Two raw layouts feed the same table: v2 pages (`<variable>/<year>/<day>/p*.json.gz`) and
v1 whole days (`<variable>-v1/<year>/<day>/day.json.gz` plus `midnight.json.gz`). Their
values are identical where both exist (checked 2026-11-11).
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
    """v2 pages of complete days. A day that also has a complete v1 download is read from
    v1 only, so no reading is counted twice."""
    root = CACHE / variable
    pattern = f"{year}/*/p*.json.gz" if year else "*/*/p*.json.gz"
    for path in sorted(root.glob(pattern)):
        day = path.parent
        if (day / "DONE").exists() and not (CACHE / f"{variable}-v1" / day.parent.name / day.name / "DONE").exists():
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


def parse_v1(body: dict, variable: str, day: str | None = None) -> tuple[list[dict], list[dict]]:
    """Rows and stations from a v1 response. With `day` (YYYY-MM-DD), keep only readings
    stamped on that local date: a midnight request can return the previous day's last
    reading, which the previous day's own file already holds."""
    meta = body.get("metadata") or {}
    unit = meta.get("reading_unit")
    rtype = meta.get("reading_type")
    rows = []
    for item in body.get("items") or []:
        stamp = item["timestamp"]
        if day and not stamp.startswith(day):
            continue
        for r in item.get("readings") or []:
            rows.append({"station_id": r["station_id"], "time": stamp, "variable": variable,
                         "value": r.get("value"), "unit": unit, "reading_type": rtype})
    stations = [
        {"station_id": s["id"], "name": s.get("name"), "latitude": s["location"]["latitude"],
         "longitude": s["location"]["longitude"]}
        for s in meta.get("stations") or []
    ]
    return rows, stations


def _v1_files(variable: str, year: int):
    root = CACHE / f"{variable}-v1" / str(year)
    for folder in sorted(root.glob("*")):
        if (folder / "DONE").exists():
            for name in ("day", "midnight"):
                path = folder / f"{name}.json.gz"
                if path.exists():
                    yield path


def _read(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def build(variable: str, year: int) -> Path | None:
    frames, stations = [], []
    for path in _pages(variable, year):
        r, s = parse_page(_read(path), variable)
        if r:
            frames.append(pd.DataFrame.from_records(r))
        stations += [{**x, "day": path.parent.name} for x in s]
    for path in _v1_files(variable, year):
        day = path.parent.name
        r, s = parse_v1(_read(path), variable, day if path.name.startswith("midnight") else None)
        if r:
            frames.append(pd.DataFrame.from_records(r))
        stations += [{**x, "day": day} for x in s]
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
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
