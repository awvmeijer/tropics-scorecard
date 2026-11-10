"""Integrated Global Radiosonde Archive version 2, Changi (SNM00048698).

Two files: the period of record and the current year to date.

Usage:
    python -m tropics_scorecard.ingest.igra
"""
from __future__ import annotations

import sys
import zipfile

from ..paths import RAW
from .http import Throttle, cached_file

BASE = "https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/access"
STATION = "SNM00048698"
CACHE = RAW / "igra"
FILES = {
    "por": f"{BASE}/data-por/{STATION}-data.txt.zip",
    "y2d": f"{BASE}/data-y2d/{STATION}-data-beg2026.txt.zip",
}


def fetch_all():
    throttle = Throttle(1.0)
    out = {}
    for kind, url in FILES.items():
        path = cached_file(url, CACHE / f"{STATION}-{kind}.txt.zip", throttle)
        with zipfile.ZipFile(path) as zf:
            name = zf.namelist()[0]
            target = CACHE / f"{STATION}-{kind}.txt"
            if not target.exists():
                target.write_bytes(zf.read(name))
        out[kind] = target
    return out


def main() -> int:
    for kind, path in fetch_all().items():
        print(kind, path, path.stat().st_size, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
