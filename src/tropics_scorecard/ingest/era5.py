"""ERA5 reanalysis from Open-Meteo's historical archive, cached to data/raw/openmeteo/era5/.

ERA5 is the reanalysis that learned weather models such as GraphCast and GenCast are
trained on and verified against. Here it is used two ways: scored against the stations like
any forecast, and used as the judge in place of the stations, so the same forecasts can be
scored both ways.

Service (checked 2026-11-14): https://archive-api.open-meteo.com/v1/archive with
`models=era5`, no key. The grid is 0.25 degrees. Every request asks for a cell centre with
`cell_selection=nearest` and `elevation=nan`, so each response is one cell's raw ERA5 value,
as for the forecasts (see ingest.openmeteo). Precipitation is the sum over the preceding
hour, the same convention as the forecasts.

Pacing shares the Open-Meteo ledger, so the free-tier limits hold across both clients.

Usage:
    python -m tropics_scorecard.ingest.era5 grid
    python -m tropics_scorecard.ingest.era5 fetch
    python -m tropics_scorecard.ingest.era5 all
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import sys

from ..paths import TABLES, load_config
from .http import FetchError
from .openmeteo import CACHE, CELL_DECIMALS, GRID_PROBE_DAY, VARIABLES, Ledger, Polite, _key, chunks, fetch, stations, weight

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
MODEL = "era5"
FOLDER = CACHE / "era5"
GRID = TABLES / "openmeteo" / "grid_era5.parquet"
CHUNK_DAYS = 366


def span(cfg: dict) -> tuple[dt.date, dt.date]:
    """From the first climatology year to the end of the test period."""
    start = dt.date.fromisoformat(str(cfg["period"]["climatology_years"]["start"]))
    end = dt.date.fromisoformat(str(cfg["period"]["day_level_lead_times"]["end"]))
    return start, end


def grid(ledger: Ledger, polite: Polite, batch: int = 50):
    """The ERA5 cell Open-Meteo uses for each station (nearest cell, no elevation adjustment)."""
    import pandas as pd

    sts = stations()
    rows = []
    for i in range(0, len(sts), batch):
        part = sts[i:i + batch]
        coords = [(s["latitude"], s["longitude"]) for s in part]
        params = {
            "latitude": ",".join(f"{la:.5f}" for la, _ in coords),
            "longitude": ",".join(f"{lo:.5f}" for _, lo in coords),
            "hourly": "temperature_2m", "models": MODEL, "cell_selection": "nearest",
            "elevation": ",".join(["nan"] * len(coords)), "timezone": "GMT",
            "start_date": GRID_PROBE_DAY.isoformat(), "end_date": GRID_PROBE_DAY.isoformat(),
        }
        body = fetch(ARCHIVE, params, FOLDER / "grid" / f"{_key(coords)}.json.gz", weight(len(coords), 1, 1),
                     ledger, polite)
        body = body if isinstance(body, list) else [body]
        if len(body) != len(part):
            raise FetchError(f"era5 grid: {len(part)} locations asked, {len(body)} returned")
        for s, b in zip(part, body):
            rows.append({"station_key": s["key"], "station_lat": s["latitude"], "station_lon": s["longitude"],
                         "cell_lat": round(b["latitude"], CELL_DECIMALS), "cell_lon": round(b["longitude"], CELL_DECIMALS),
                         "cell_elevation_m": b.get("elevation")})
    df = pd.DataFrame(rows)
    GRID.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(GRID, index=False)
    print(f"era5 grid: {len(df)} stations in {df.groupby(['cell_lat', 'cell_lon']).ngroups} cells", flush=True)
    return GRID


def cells() -> list[tuple[float, float]]:
    import pandas as pd

    g = pd.read_parquet(GRID)
    return sorted(set(zip(g["cell_lat"], g["cell_lon"])))


def cell_dir(cell: tuple[float, float]):
    return FOLDER / "cells" / f"{cell[0]:.4f}_{cell[1]:.4f}"


def fetch_all(cfg: dict, ledger: Ledger, polite: Polite) -> int:
    start, end = span(cfg)
    hourly = [VARIABLES[v] for v in ("rain_hourly", "temperature_2m", "wind_speed_10m")]
    n = 0
    for cell in cells():
        for a, b in chunks(start, end, CHUNK_DAYS):
            params = {
                "latitude": f"{cell[0]:.4f}", "longitude": f"{cell[1]:.4f}", "hourly": ",".join(hourly),
                "models": MODEL, "cell_selection": "nearest", "elevation": "nan", "timezone": "GMT",
                "wind_speed_unit": "ms", "start_date": a.isoformat(), "end_date": b.isoformat(),
            }
            body = fetch(ARCHIVE, params, cell_dir(cell) / f"{a}_{b}.json.gz",
                         weight(1, len(hourly), (b - a).days + 1), ledger, polite)
            got = (round(body["latitude"], 4), round(body["longitude"], 4))
            if math.dist(got, cell) > 1e-3:
                raise FetchError(f"era5: asked for cell {cell}, got {got}")
            n += 1
        print(f"era5 {cell} {start}..{end}", flush=True)
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=["grid", "fetch", "all"])
    args = ap.parse_args(argv)
    cfg = load_config()
    ledger, polite = Ledger(), Polite()
    if args.step in ("grid", "all"):
        grid(ledger, polite)
    if args.step in ("fetch", "all"):
        print(f"era5: {fetch_all(cfg, ledger, polite)} chunks on disk", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
