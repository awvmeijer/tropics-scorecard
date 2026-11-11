"""The reference: hourly observations in the form the forecasts are scored against.

reference/<variable>_<year>.parquet:
    station_key, network, time_utc, value, complete, flagged

- rain_hourly: data.gov.sg gauges, the total of the 5-minute readings in the hour ending at
  time_utc. `complete` when the hour holds config matching.rain_readings_per_hour readings.
- temperature_2m, wind_speed_10m: data.gov.sg readings stamped on the hour, and ISD airport
  reports chosen by store.isd.preferred. Wind in metres per second.
- `flagged` when any reading that went into the value carries a quality-control flag.

The rules come from config/study.yaml (section `matching`) and are explained in
docs/verification_protocol.md, section 3.

Usage:
    python -m tropics_scorecard.match.observations 2024 2025 2026
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ..paths import TABLES, load_config

OUT = TABLES / "reference"
VARIABLES = ("rain_hourly", "temperature_2m", "wind_speed_10m")
DGS_NAME = {"rain_hourly": "rainfall", "temperature_2m": "air-temperature", "wind_speed_10m": "wind-speed"}
ISD = {"temperature_2m": ("temperature_c", "temperature"), "wind_speed_10m": ("wind_speed_ms", "wind_speed")}
COLUMNS = ["station_key", "network", "time_utc", "value", "complete", "flagged"]


def _flags(name: str) -> pd.DataFrame:
    paths = sorted((TABLES / "qc").glob(name))
    if not paths:
        return pd.DataFrame(columns=["station_id", "time_utc", "check"])
    f = pd.concat([pd.read_parquet(p, columns=["station_id", "time_utc", "check"]) for p in paths], ignore_index=True)
    f["time_utc"] = pd.to_datetime(f["time_utc"], utc=True)
    return f


def hour_end(times: pd.Series, stamp: str) -> pd.Series:
    """The hour a 5-minute reading belongs to, labelled by the hour's end.

    stamp="end": a stamp marks the end of its interval, so 10:05 to 11:00 make the hour ending 11:00.
    stamp="start": a stamp marks the start, so 10:00 to 10:55 make the hour ending 11:00.
    """
    if stamp == "end":
        return times.dt.ceil("h")
    if stamp == "start":
        return times.dt.floor("h") + pd.Timedelta(hours=1)
    raise ValueError(f"unknown gauge_stamp {stamp!r}")


def rain_hours(readings: pd.DataFrame, flags: pd.DataFrame, stamp: str, per_hour: int) -> pd.DataFrame:
    """readings: station_id, time_utc, value. flags: station_id, time_utc, check."""
    d = readings.dropna(subset=["value"])[["station_id", "time_utc", "value"]].copy()
    d = d.drop_duplicates(["station_id", "time_utc"])
    bad = flags[flags["check"] != "stuck_dry"][["station_id", "time_utc"]].drop_duplicates()
    d = d.merge(bad.assign(bad=True), on=["station_id", "time_utc"], how="left")
    d["bad"] = d["bad"].fillna(False).astype(bool)
    d["hour"] = hour_end(d["time_utc"], stamp)
    h = d.groupby(["station_id", "hour"]).agg(value=("value", "sum"), n=("value", "size"), flagged=("bad", "any")).reset_index()
    stuck = flags[flags["check"] == "stuck_dry"][["station_id", "time_utc"]].drop_duplicates()
    stuck = stuck.rename(columns={"time_utc": "hour"}).assign(stuck=True)
    h = h.merge(stuck, on=["station_id", "hour"], how="left")
    h["flagged"] = h["flagged"] | h["stuck"].fillna(False).astype(bool)
    h["complete"] = h["n"] == per_hour
    out = pd.DataFrame({"station_key": "dgs:" + h["station_id"], "network": "dgs", "time_utc": h["hour"],
                        "value": h["value"].round(3), "complete": h["complete"], "flagged": h["flagged"]})
    return out[COLUMNS]


def instant_hours(readings: pd.DataFrame, flags: pd.DataFrame, window_minutes: int, scale: float = 1.0) -> pd.DataFrame:
    """The reading stamped on the hour; with a window, the mean of readings within it."""
    d = readings.dropna(subset=["value"])[["station_id", "time_utc", "value"]].drop_duplicates(["station_id", "time_utc"])
    bad = flags[["station_id", "time_utc"]].drop_duplicates().assign(bad=True)
    d = d.merge(bad, on=["station_id", "time_utc"], how="left")
    d["bad"] = d["bad"].fillna(False).astype(bool)
    if window_minutes == 0:
        d = d[(d["time_utc"].dt.minute == 0) & (d["time_utc"].dt.second == 0)]
        h = d.rename(columns={"time_utc": "hour", "bad": "flagged"})
    else:
        d["hour"] = d["time_utc"].dt.round("h")
        d = d[(d["time_utc"] - d["hour"]).abs() <= pd.Timedelta(minutes=window_minutes)]
        h = d.groupby(["station_id", "hour"]).agg(value=("value", "mean"), flagged=("bad", "any")).reset_index()
    out = pd.DataFrame({"station_key": "dgs:" + h["station_id"], "network": "dgs", "time_utc": h["hour"],
                        "value": (h["value"] * scale).round(3), "complete": True, "flagged": h["flagged"]})
    return out[COLUMNS]


def isd_hours(obs: pd.DataFrame, flags: pd.DataFrame, column: str) -> pd.DataFrame:
    d = obs[obs["preferred"]][["station_id", "time_utc", column]].rename(columns={column: "value"}).dropna(subset=["value"])
    bad = flags[["station_id", "time_utc"]].drop_duplicates().assign(bad=True)
    d = d.merge(bad, on=["station_id", "time_utc"], how="left")
    out = pd.DataFrame({"station_key": "isd:" + d["station_id"], "network": "isd", "time_utc": d["time_utc"],
                        "value": d["value"].round(3), "complete": True,
                        "flagged": d["bad"].fillna(False).astype(bool)})
    return out[COLUMNS]


def build(variable: str, year: int, cfg: dict | None = None) -> Path | None:
    cfg = cfg or load_config()
    m = cfg["matching"]
    parts = []
    dgs = TABLES / "datagovsg" / f"readings_{DGS_NAME[variable]}_{year}.parquet"
    if dgs.exists():
        # Yearly reading files follow Singapore dates, eight hours ahead of UTC, so the last
        # UTC hours of a year sit in the next year's file. Read up to 00:00 UTC on 1 January.
        r = [pd.read_parquet(dgs, columns=["station_id", "time_utc", "value"])]
        f = [_flags(f"flags_datagovsg_{DGS_NAME[variable]}_{year}.parquet")]
        nxt = TABLES / "datagovsg" / f"readings_{DGS_NAME[variable]}_{year + 1}.parquet"
        if nxt.exists():
            r.append(pd.read_parquet(nxt, columns=["station_id", "time_utc", "value"],
                                     filters=[("time_utc", "<=", pd.Timestamp(f"{year + 1}-01-01T00:00", tz="UTC"))]))
            f.append(_flags(f"flags_datagovsg_{DGS_NAME[variable]}_{year + 1}.parquet"))
        r, f = pd.concat(r, ignore_index=True), pd.concat(f, ignore_index=True)
        if variable == "rain_hourly":
            h = rain_hours(r, f, m["gauge_stamp"], m["rain_readings_per_hour"])
        else:
            scale = m["knots_to_ms"] if variable == "wind_speed_10m" else 1.0
            h = instant_hours(r, f, m["instant_window_minutes"], scale)
        parts.append(h)
    isd = TABLES / "isd" / f"obs_{year}.parquet"
    if variable in ISD and isd.exists():
        col, qcvar = ISD[variable]
        parts.append(isd_hours(pd.read_parquet(isd), _flags(f"flags_isd_{qcvar}.parquet"), col))
    if not parts:
        return None
    df = pd.concat(parts, ignore_index=True)
    df = df[df["time_utc"].dt.year == year]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{variable}_{year}.parquet"
    df.sort_values(["station_key", "time_utc"]).to_parquet(path, index=False)
    return path


def utc(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def load(variable: str, start, end, *, complete_only: bool = True, drop_flagged: bool = True) -> pd.DataFrame:
    """Reference values with start <= time_utc <= end (UTC, inclusive)."""
    start, end = utc(start), utc(end)
    paths = [OUT / f"{variable}_{y}.parquet" for y in range(start.year, end.year + 1)]
    paths = [p for p in paths if p.exists()]
    if not paths:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    df = df[(df["time_utc"] >= start) & (df["time_utc"] <= end)]
    if complete_only:
        df = df[df["complete"]]
    if drop_flagged:
        df = df[~df["flagged"]]
    return df.reset_index(drop=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("years", type=int, nargs="+")
    ap.add_argument("--variables", default=",".join(VARIABLES))
    args = ap.parse_args(argv)
    cfg = load_config()
    for v in args.variables.split(","):
        for y in args.years:
            print(v, y, build(v, y, cfg), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
