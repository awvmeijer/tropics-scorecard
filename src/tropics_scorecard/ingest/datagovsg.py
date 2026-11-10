"""Singapore station network, data.gov.sg collection 1459.

Endpoint: https://api-open.data.gov.sg/v2/real-time/api/<variable>
- `date=YYYY-MM-DD` returns the whole day, newest first, 25 readings per page, with a
  `paginationToken` for the next page.
- `date=YYYY-MM-DDTHH:MM:SS` returns a single snapshot.
Without a key the API allows roughly one request every 7 to 10 seconds.

Usage:
    python -m tropics_scorecard.ingest.datagovsg rainfall 2024-02-04 2026-10-31
    python -m tropics_scorecard.ingest.datagovsg air-temperature 2024-02-04 2026-10-31 --snapshots
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import urllib.parse
from pathlib import Path

from ..paths import RAW
from .http import FetchError, Throttle, cached_json

BASE = "https://api-open.data.gov.sg/v2/real-time/api/"
VARIABLES = ("rainfall", "air-temperature", "relative-humidity", "wind-speed", "wind-direction")
CACHE = RAW / "datagovsg"
INTERVAL_SECONDS = 7.5


def _day_dir(variable: str, day: dt.date) -> Path:
    return CACHE / variable / f"{day:%Y}" / f"{day:%Y-%m-%d}"


def fetch_day(variable: str, day: dt.date, throttle: Throttle) -> list[Path]:
    """Fetch every page of one day. Returns the cached page files. Resumable."""
    folder = _day_dir(variable, day)
    done = folder / "DONE"
    if done.exists():
        return sorted(folder.glob("p*.json.gz"))
    url = f"{BASE}{variable}?date={day:%Y-%m-%d}"
    pages: list[Path] = []
    page = 1
    while True:
        path = folder / f"p{page:03d}.json.gz"
        try:
            body = cached_json(url, path, throttle)
        except FetchError as err:
            if str(err).startswith("404"):
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "NO_DATA").write_text(url + "\n")
                done.write_text("0\n")
                return []
            raise
        pages.append(path)
        token = (body.get("data") or {}).get("paginationToken")
        if not token:
            break
        url = f"{BASE}{variable}?date={day:%Y-%m-%d}&paginationToken={urllib.parse.quote(token)}"
        page += 1
        if page > 400:
            raise FetchError(f"runaway pagination for {variable} {day}")
    done.write_text(f"{len(pages)}\n")
    return pages


def fetch_snapshots(variable: str, day: dt.date, throttle: Throttle, minute: int = 0) -> list[Path]:
    """One snapshot per hour, at HH:<minute> Singapore time."""
    folder = CACHE / f"{variable}-snapshots" / f"{day:%Y}" / f"{day:%Y-%m-%d}"
    out = []
    for hour in range(24):
        stamp = f"{day:%Y-%m-%d}T{hour:02d}:{minute:02d}:00"
        path = folder / f"{hour:02d}.json.gz"
        try:
            cached_json(f"{BASE}{variable}?date={stamp}", path, throttle)
            out.append(path)
        except FetchError as err:
            if not str(err).startswith("404"):
                raise
    return out


def days(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("variable", choices=VARIABLES)
    ap.add_argument("start", type=dt.date.fromisoformat)
    ap.add_argument("end", type=dt.date.fromisoformat)
    ap.add_argument("--snapshots", action="store_true", help="hourly snapshots instead of every reading")
    ap.add_argument("--newest-first", action="store_true")
    args = ap.parse_args(argv)
    throttle = Throttle(INTERVAL_SECONDS)
    seq = list(days(args.start, args.end))
    if args.newest_first:
        seq.reverse()
    for i, day in enumerate(seq, 1):
        n = fetch_snapshots(args.variable, day, throttle) if args.snapshots else fetch_day(args.variable, day, throttle)
        print(f"{args.variable} {day} pages={len(n)} ({i}/{len(seq)})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
