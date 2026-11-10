"""NOAA Integrated Surface Database, global hourly, from the AWS open data bucket.

NCEI's global-hourly access path now redirects to
https://noaa-global-hourly-pds.s3.amazonaws.com/<year>/<USAF><WBAN>.csv
The regional archive ends on 2025-08-24 (checked 2026-11-10).

Usage:
    python -m tropics_scorecard.ingest.isd 2017 2025
"""
from __future__ import annotations

import argparse
import sys

from ..paths import RAW
from .http import FetchError, Throttle, cached_file

BASE = "https://noaa-global-hourly-pds.s3.amazonaws.com"
CACHE = RAW / "isd"

# Airports inside the bounding box with reports in 2024 (from isd-history.csv).
STATIONS = {
    "48698099999": "Singapore Changi",
    "48694099999": "Paya Lebar",
    "48699099999": "Seletar",
    "48679099999": "Senai",
    "48602199999": "Mersing",
    "96087099999": "Batam Hang Nadim",
    "96091099999": "Kijang",
}


def fetch(year: int, station: str, throttle: Throttle):
    try:
        return cached_file(f"{BASE}/{year}/{station}.csv", CACHE / str(year) / f"{station}.csv", throttle)
    except FetchError as err:
        if str(err).startswith("404"):
            return None
        raise


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("first_year", type=int)
    ap.add_argument("last_year", type=int)
    args = ap.parse_args(argv)
    throttle = Throttle(0.5)
    for year in range(args.first_year, args.last_year + 1):
        for station, name in STATIONS.items():
            path = fetch(year, station, throttle)
            print(year, station, name, "missing" if path is None else f"{path.stat().st_size} bytes", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
