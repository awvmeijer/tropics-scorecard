"""Parse IGRA v2 fixed-width sounding files into header and level tables.

Columns follow the IGRA v2 data format description. Pressure in Pa, height in m,
temperature and dewpoint depression in tenths of a degree, relative humidity in
tenths of a percent, wind speed in tenths of m/s. -9999 is missing, -8888 removed.
"""
from __future__ import annotations

import pandas as pd

from ..ingest.igra import CACHE, STATION
from ..paths import TABLES

OUT = TABLES / "igra"


def _num(s: str) -> float | None:
    s = s.strip()
    if not s:
        return None
    v = int(s)
    return None if v in (-9999, -8888) else v


def parse(path, first_year: int = 2017):
    headers, levels = [], []
    keep = False
    with open(path, encoding="ascii") as fh:
        for line in fh:
            if line.startswith("#"):
                year = int(line[13:17])
                keep = year >= first_year
                if not keep:
                    continue
                reltime = line[27:31]
                sid = f"{line[13:17]}{line[18:20]}{line[21:23]}{line[24:26]}"
                headers.append({
                    "sounding_id": sid,
                    "nominal_time_utc": f"{line[13:17]}-{line[18:20]}-{line[21:23]}T{line[24:26]}:00",
                    "release_hhmm": None if reltime.strip() in ("9999", "") else reltime.strip(),
                    "n_levels": int(line[32:36]),
                    "source": line[37:45].strip(),
                    "latitude": int(line[55:62]) / 10000,
                    "longitude": int(line[63:71]) / 10000,
                })
            elif keep:
                p, z, t = _num(line[9:15]), _num(line[16:21]), _num(line[22:27])
                rh, dpd, wd, ws = _num(line[28:33]), _num(line[34:39]), _num(line[40:45]), _num(line[46:51])
                levels.append({
                    "sounding_id": sid,
                    "level_type": line[0:2],
                    "elapsed": line[3:8].strip(),
                    "pressure_hpa": None if p is None else p / 100,
                    "pressure_flag": line[15].strip(),
                    "height_m": z,
                    "height_flag": line[21].strip(),
                    "temperature_c": None if t is None else t / 10,
                    "temperature_flag": line[27].strip(),
                    "rh_pct": None if rh is None else rh / 10,
                    "dewpoint_depression_c": None if dpd is None else dpd / 10,
                    "wind_dir_deg": wd,
                    "wind_speed_ms": None if ws is None else ws / 10,
                })
    h = pd.DataFrame(headers)
    h["nominal_time_utc"] = pd.to_datetime(h["nominal_time_utc"]).dt.tz_localize("UTC")
    return h, pd.DataFrame(levels)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    h, lv = parse(CACHE / f"{STATION}-por.txt")
    h = h.drop_duplicates("sounding_id")
    h.to_parquet(OUT / "soundings.parquet", index=False)
    lv.to_parquet(OUT / "levels.parquet", index=False)
    return h, lv


if __name__ == "__main__":
    h, lv = build()
    print(len(h), "soundings", h["nominal_time_utc"].min(), h["nominal_time_utc"].max(), len(lv), "levels")
