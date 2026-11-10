"""Parse ISD global-hourly CSVs into one tidy table.

Field codes follow the ISD format document: missing values are 9999 or 99999,
scaled by 10. Quality codes are kept so QC can use them.
"""
from __future__ import annotations

import pandas as pd

from ..ingest.isd import CACHE, STATIONS
from ..paths import TABLES

OUT = TABLES / "isd"


def _split(series: pd.Series, n: int) -> pd.DataFrame:
    return series.fillna("").str.split(",", expand=True).reindex(columns=range(n))


def parse(path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, usecols=lambda c: c in {
        "STATION", "DATE", "LATITUDE", "LONGITUDE", "ELEVATION", "REPORT_TYPE", "WND", "TMP", "DEW", "AA1"})
    out = pd.DataFrame({
        "station_id": raw["STATION"],
        "time_utc": pd.to_datetime(raw["DATE"], format="ISO8601").dt.tz_localize("UTC"),
        "report_type": raw["REPORT_TYPE"].str.strip(),
        "latitude": pd.to_numeric(raw["LATITUDE"]),
        "longitude": pd.to_numeric(raw["LONGITUDE"]),
        "elevation_m": pd.to_numeric(raw["ELEVATION"]),
    })
    tmp = _split(raw["TMP"], 2)
    out["temperature_c"] = pd.to_numeric(tmp[0], errors="coerce").where(lambda v: v.abs() < 9999) / 10
    out["temperature_qc"] = tmp[1]
    dew = _split(raw["DEW"], 2)
    out["dewpoint_c"] = pd.to_numeric(dew[0], errors="coerce").where(lambda v: v.abs() < 9999) / 10
    wnd = _split(raw["WND"], 5)
    out["wind_dir_deg"] = pd.to_numeric(wnd[0], errors="coerce").where(lambda v: v != 999)
    out["wind_dir_qc"] = wnd[1]
    out["wind_type"] = wnd[2]
    out["wind_speed_ms"] = pd.to_numeric(wnd[3], errors="coerce").where(lambda v: v != 9999) / 10
    out["wind_speed_qc"] = wnd[4]
    aa = _split(raw["AA1"] if "AA1" in raw else pd.Series([""] * len(raw)), 4)
    out["precip_period_h"] = pd.to_numeric(aa[0], errors="coerce").where(lambda v: v != 99)
    out["precip_mm"] = pd.to_numeric(aa[1], errors="coerce").where(lambda v: v != 9999) / 10
    out["precip_qc"] = aa[3]
    out["preferred"] = preferred(out)
    return out


def preferred(df: pd.DataFrame) -> pd.Series:
    """One report per station and hour for matching.

    On the hour a station often sends both a SYNOP (FM-12, temperature in tenths) and a
    METAR (FM-15, whole degrees, wind in whole knots). Prefer the SYNOP, then the METAR,
    then a special report (FM-16). Half-hour METARs are never preferred.
    """
    rank = df["report_type"].map({"FM-12": 0, "FM-15": 1, "FM-16": 2}).fillna(3)
    on_hour = df["time_utc"].dt.minute == 0
    order = pd.DataFrame({"station_id": df["station_id"], "time_utc": df["time_utc"], "rank": rank}).sort_values("rank", kind="stable")
    first = ~order.duplicated(["station_id", "time_utc"], keep="first")
    return (first.reindex(df.index) & on_hour).astype(bool)


def build(years) -> list:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for year in years:
        frames = [parse(CACHE / str(year) / f"{s}.csv") for s in STATIONS if (CACHE / str(year) / f"{s}.csv").exists()]
        if frames:
            path = OUT / f"obs_{year}.parquet"
            pd.concat(frames, ignore_index=True).to_parquet(path, index=False)
            written.append(path)
    return written


if __name__ == "__main__":
    for p in build(range(2017, 2026)):
        print(p)
