"""Singapore station network, data.gov.sg collection 1459.

Endpoint: https://api-open.data.gov.sg/v2/real-time/api/<variable>
- `date=YYYY-MM-DD` returns the whole day, newest first, 25 readings per page, with a
  `paginationToken` for the next page.
- `date=YYYY-MM-DDTHH:MM:SS` returns a single snapshot.
Without a key the API allows roughly one request every 7 to 10 seconds.

Usage (the v1 mode below is the one used for this study):
    python -m tropics_scorecard.ingest.datagovsg rainfall,air-temperature,wind-speed 2017-01-01 2026-10-31 --v1
    python -m tropics_scorecard.ingest.datagovsg air-temperature,wind-speed 2024-02-04 2026-10-31 --snapshots

A snapshot request for HH:MM:SS returns the reading stamped HH:MM:00 for every station
in one call (checked 2026-11-10). Snapshots are taken on the hour, Singapore time, which
is also on the hour in UTC.

Older v1 endpoint, https://api.data.gov.sg/v1/environment/<variable> (checked 2026-11-11):
- `date=YYYY-MM-DD` returns every reading of the day in one response, no pagination.
  The window leaves out the reading stamped 00:00 of that day, so `--v1` also fetches it
  with `date_time=YYYY-MM-DDT00:00:00`. Two requests per day per variable.
- Values are identical to v2: on 2024-03-01 all 18,069 shared rain readings and all 296
  shared temperature readings were equal.

    python -m tropics_scorecard.ingest.datagovsg air-temperature,wind-speed 2024-02-04 2026-10-31 --v1
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
V1_BASE = "https://api.data.gov.sg/v1/environment/"
VARIABLES = ("rainfall", "air-temperature", "relative-humidity", "wind-speed", "wind-direction")
CACHE = RAW / "datagovsg"
INTERVAL_SECONDS = 7.5
V1_INTERVAL_SECONDS = 2.0


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


def v1_day_dir(variable: str, day: dt.date) -> Path:
    return CACHE / f"{variable}-v1" / f"{day:%Y}" / f"{day:%Y-%m-%d}"


def fetch_day_v1(variable: str, day: dt.date, throttle: Throttle) -> list[Path]:
    """One day from the v1 endpoint: the day response plus the 00:00 reading. Resumable."""
    folder = v1_day_dir(variable, day)
    done = folder / "DONE"
    if done.exists():
        return sorted(folder.glob("*.json.gz"))
    out = []
    for name, query in (("day", f"date={day:%Y-%m-%d}"), ("midnight", f"date_time={day:%Y-%m-%d}T00:00:00")):
        path = folder / f"{name}.json.gz"
        try:
            body = cached_json(f"{V1_BASE}{variable}?{query}", path, throttle)
        except FetchError as err:
            if not str(err).startswith("404"):
                raise
            continue
        if not isinstance(body, dict) or "items" not in body:
            path.unlink(missing_ok=True)
            raise FetchError(f"unexpected v1 body for {variable} {day} {name}: {str(body)[:200]}")
        out.append(path)
    folder.mkdir(parents=True, exist_ok=True)
    done.write_text(f"{len(out)}\n")
    return out


def days(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("variable", help="one variable, or several separated by commas: " + ", ".join(VARIABLES))
    ap.add_argument("start", type=dt.date.fromisoformat)
    ap.add_argument("end", type=dt.date.fromisoformat)
    ap.add_argument("--snapshots", action="store_true", help="hourly snapshots instead of every reading")
    ap.add_argument("--v1", action="store_true", help="whole days from the older v1 endpoint, two requests a day")
    ap.add_argument("--newest-first", action="store_true")
    args = ap.parse_args(argv)
    if args.v1 and args.snapshots:
        ap.error("--v1 already returns every reading; drop --snapshots")
    variables = args.variable.split(",")
    for v in variables:
        if v not in VARIABLES:
            ap.error(f"unknown variable {v}")
    throttle = Throttle(V1_INTERVAL_SECONDS if args.v1 else INTERVAL_SECONDS)
    seq = list(days(args.start, args.end))
    if args.newest_first:
        seq.reverse()
    for i, day in enumerate(seq, 1):
        for v in variables:
            if args.v1:
                n, kind = fetch_day_v1(v, day, throttle), "v1files"
            elif args.snapshots:
                n, kind = fetch_snapshots(v, day, throttle), "snapshots"
            else:
                n, kind = fetch_day(v, day, throttle), "pages"
            print(f"{v} {day} {kind}={len(n)} ({i}/{len(seq)})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
