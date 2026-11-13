"""Run quality control over the stored tables and log every flag.

Writes data/tables/qc/flags_<source>_<variable>.parquet and prints a summary.

Usage:
    python -m tropics_scorecard.qc.run isd
    python -m tropics_scorecard.qc.run datagovsg rainfall 2024
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from ..paths import TABLES, load_config
from . import checks

OUT = TABLES / "qc"


def _save(flags: pd.DataFrame, source: str, variable: str, suffix: str = "") -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    flags = flags.copy()
    flags["source"], flags["variable"] = source, variable
    flags.to_parquet(OUT / f"flags_{source}_{variable}{suffix}.parquet", index=False)
    return flags


def summarise(flags: pd.DataFrame, n_readings: int) -> pd.DataFrame:
    if flags.empty:
        return pd.DataFrame(columns=["check", "flags", "share_pct"])
    s = flags.groupby("check").size().rename("flags").reset_index()
    s["share_pct"] = (100 * s["flags"] / max(n_readings, 1)).round(3)
    return s


def run_isd(cfg: dict) -> dict:
    qc = cfg["quality_control"]
    df = pd.concat([pd.read_parquet(p) for p in sorted((TABLES / "isd").glob("obs_*.parquet"))], ignore_index=True)
    bad_codes = set(qc["isd_bad_quality_codes"])
    out = {}
    for var, col, qcol, rng, spike in [
        ("temperature", "temperature_c", "temperature_qc", qc["range"]["isd_temperature_c"], qc["spike"]["isd_temperature_c"]),
        ("wind_speed", "wind_speed_ms", "wind_speed_qc", qc["range"]["isd_wind_speed_ms"], None),
    ]:
        d = df[["station_id", "time_utc", "report_type", "preferred", col, qcol]].rename(columns={col: "value"})
        parts = [
            checks._flags(d[d[qcol].isin(bad_codes)], "isd_quality_code", d.loc[d[qcol].isin(bad_codes), qcol].map(lambda c: f"ISD code {c}")),
            checks.out_of_range(d.dropna(subset=["value"]), rng["min"], rng["max"]),
        ]
        # Duplicates are checked within a report type: a SYNOP and a METAR at the same hour are two reports.
        for rt, sub in d.dropna(subset=["value"]).groupby("report_type"):
            f = checks.duplicates(sub)
            parts.append(f.assign(detail=f["detail"] + f" ({rt})"))
        pref = d[d["preferred"]]
        if spike:
            parts.append(checks.spikes(pref, spike["jump"], spike["max_gap_minutes"]))
        if var == "temperature":
            tz = qc["timezone"]["expected_local_hour_of_max"]
            parts.append(checks.timezone_check(pref, cfg["region"]["local_timezone"], tz["min"], tz["max"]))
        flags = _save(pd.concat(parts, ignore_index=True), "isd", var)
        out[var] = summarise(flags, int(d["value"].notna().sum()))
    return out


DGS = {
    "rainfall": "rainfall_mm_per_5min",
    "air-temperature": "air_temperature_c",
    "relative-humidity": "relative_humidity_pct",
    "wind-speed": "wind_speed_knots",
}


def hourly_rain(d: pd.DataFrame) -> pd.DataFrame:
    """Hourly totals of 5-minute gauge readings, hour labelled by its end, with a count of
    readings. A reading stamped HH:MM covers the five minutes ending at HH:MM (to be
    confirmed in the observation note), so 10:05 to 11:00 make the hour ending 11:00."""
    d = d.dropna(subset=["value"]).copy()
    d["hour_end"] = d["time_utc"].dt.ceil("h")
    h = d.groupby(["station_id", "hour_end"])["value"].agg(["sum", "count"]).reset_index()
    return h.rename(columns={"hour_end": "time_utc", "sum": "value", "count": "n_readings"})


def run_datagovsg(cfg: dict, variable: str, year: int) -> dict:
    qc = cfg["quality_control"]
    key = DGS[variable]
    path = TABLES / "datagovsg" / f"readings_{variable}_{year}.parquet"
    d = pd.read_parquet(path)[["station_id", "time_utc", "value"]]
    parts = [checks.duplicates(d.dropna(subset=["value"])),
             checks.out_of_range(d.dropna(subset=["value"]), qc["range"][key]["min"], qc["range"][key]["max"])]
    if key in qc["spike"]:
        parts.append(checks.spikes(d, qc["spike"][key]["jump"], qc["spike"][key]["max_gap_minutes"]))
    if key in qc["flatline"]:
        f = qc["flatline"][key]
        parts.append(checks.flatlines(d, f["minutes"], f.get("ignore_value")))
    if variable == "air-temperature":
        tz = qc["timezone"]["expected_local_hour_of_max"]
        parts.append(checks.timezone_check(d, cfg["region"]["local_timezone"], tz["min"], tz["max"]))
    blocked = None
    if variable == "rainfall":
        st = pd.read_parquet(TABLES / "datagovsg" / f"stations_{variable}_{year}.parquet")
        sd = qc["stuck_dry"]
        h = hourly_rain(d)
        h = h[h["n_readings"] == 12]
        try:
            parts.append(checks.stuck_dry(h, st, sd["radius_km"], sd["min_neighbours"], sd["neighbour_median_mm"]))
        except checks.BlockedByStub as err:
            blocked = str(err)
    flags = _save(pd.concat(parts, ignore_index=True), "datagovsg", variable, f"_{year}")
    return {"summary": summarise(flags, int(d["value"].notna().sum())), "blocked": blocked}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=["isd", "datagovsg"])
    ap.add_argument("variable", nargs="?")
    ap.add_argument("year", nargs="?", type=int)
    args = ap.parse_args(argv)
    cfg = load_config()
    if args.source == "isd":
        for var, s in run_isd(cfg).items():
            print(f"== isd {var}\n{s.to_string(index=False)}")
    else:
        r = run_datagovsg(cfg, args.variable, args.year)
        print(r["summary"].to_string(index=False))
        if r["blocked"]:
            print(f"BLOCKED: stuck_dry check skipped, needs a metric function: {r['blocked']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
