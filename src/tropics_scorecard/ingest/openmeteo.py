"""Archived operational forecasts from Open-Meteo, cached to data/raw/openmeteo/.

Services (checked 2026-11-10, see docs/source_check.md):
- Previous Runs, https://previous-runs-api.open-meteo.com/v1/forecast. `<var>_previous_dayN`
  is the value for a valid hour from the run that was current N days earlier.
- Single Runs, https://single-runs-api.open-meteo.com/v1/forecast with `run=YYYY-MM-DDTHH:MM`.
  The whole output of one run, so lead time is known to the hour.

Grid cells. Every forecast request asks for a grid-cell centre with `cell_selection=nearest`
and `elevation=nan`, so each response is one cell's raw model value: no land preference and
no elevation downscaling by Open-Meteo. Which cell a station is paired with is a matching
rule in config/study.yaml. The `grid` step records, for every station and model, the cell
Open-Meteo picks under `nearest` and under `land`, and both sets of cells are fetched, so
the rule can change without new downloads. The `land` rule needs a target elevation (with
`elevation=nan` it falls back to the nearest cell, checked 2026-11-11), so its discovery
request uses Open-Meteo's default 90 m elevation model for the station point.

Free tier: fewer than 10,000 calls a day, 5,000 an hour and 600 a minute. A request with more
than 10 variables or more than 14 days counts pro rata, and each location counts. A ledger
in data/raw/openmeteo/ledger.jsonl keeps this client below 80 percent of each limit, across
restarts.

Usage:
    python -m tropics_scorecard.ingest.openmeteo grid
    python -m tropics_scorecard.ingest.openmeteo previous
    python -m tropics_scorecard.ingest.openmeteo single
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import sys
import time
import urllib.parse
from pathlib import Path

from ..paths import RAW, TABLES, load_config
from .http import FetchError, cached_json

CACHE = RAW / "openmeteo"
LEDGER = CACHE / "ledger.jsonl"
PREVIOUS = "https://previous-runs-api.open-meteo.com/v1/forecast"
SINGLE = "https://single-runs-api.open-meteo.com/v1/forecast"

# Our variable name -> Open-Meteo hourly variable.
VARIABLES = {
    "rain_hourly": "precipitation",
    "temperature_2m": "temperature_2m",
    "wind_speed_10m": "wind_speed_10m",
}
CELL_RULES = ("nearest", "land")
LIMITS = {60: 600, 3600: 5000, 86400: 10000}  # window in seconds -> calls
SHARE = 0.8
CHUNK_DAYS = 91
CELL_DECIMALS = 4  # cell coordinates are rounded once, here and in store.openmeteo, and joined exactly
GRID_PROBE_DAY = dt.date(2026, 10, 1)


# ---------------------------------------------------------------- pacing

def weight(n_locations: int, n_variables: int, n_days: float) -> float:
    """Calls charged for one request, by the pro-rata rule on the pricing page."""
    return n_locations * max(1.0, n_variables / 10) * max(1.0, n_days / 14)


class Ledger:
    """Calls spent, by time, persisted so pacing survives a restart."""

    def __init__(self, path: Path = LEDGER):
        self.path = path
        self.entries: list[tuple[float, float]] = []
        if path.exists():
            for line in path.read_text().splitlines():
                t, w = json.loads(line)
                self.entries.append((t, w))
        self._trim(time.time())

    def _trim(self, now: float) -> None:
        self.entries = [(t, w) for t, w in self.entries if now - t < 86400]

    def spent(self, window: int, now: float) -> float:
        return sum(w for t, w in self.entries if now - t < window)

    def wait_for(self, w: float) -> None:
        while True:
            now = time.time()
            self._trim(now)
            waits = []
            for window, limit in LIMITS.items():
                cap = SHARE * limit
                if w > cap:
                    raise ValueError(f"request weight {w:.1f} exceeds the {window}s budget {cap:.0f}")
                if self.spent(window, now) + w > cap:
                    # wait until enough of the window has rolled off
                    acc, need = 0.0, self.spent(window, now) + w - cap
                    for t, x in sorted(e for e in self.entries if now - e[0] < window):
                        acc += x
                        if acc >= need:
                            waits.append(t + window - now + 1)
                            break
            if not waits:
                return
            pause = max(waits)
            print(f"pacing: sleeping {pause:.0f}s to stay inside the free-tier limits", flush=True)
            time.sleep(min(pause, 900))

    def record(self, w: float) -> None:
        t = time.time()
        self.entries.append((t, w))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as fh:
            fh.write(json.dumps([t, w]) + "\n")


class Polite:
    """Throttle-compatible object for cached_json: a short gap between requests."""

    def __init__(self, interval: float = 1.0):
        self.interval, self._last = interval, 0.0

    def wait(self) -> None:
        delay = self._last + self.interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()


def fetch(base: str, params: dict, path: Path, w: float, ledger: Ledger, polite: Polite) -> dict | list:
    """Cached GET. Spends ledger budget only when the response is not on disk."""
    url = base + "?" + urllib.parse.urlencode(params, safe=",:")
    if path.exists():
        return cached_json(url, path)
    for attempt in range(5):
        ledger.wait_for(w)
        try:
            return cached_json(url, path, polite)
        except FetchError as err:
            if not str(err).startswith("not JSON") or attempt == 4:
                raise
            print(f"retry in {30 * (attempt + 1)}s: {err}", file=sys.stderr, flush=True)
            time.sleep(30 * (attempt + 1))
        finally:
            ledger.record(w)
    raise AssertionError("unreachable")


# ---------------------------------------------------------------- stations and cells

def stations() -> list[dict]:
    """Every station that can be scored: data.gov.sg rain, temperature and wind, and ISD airports."""
    import pandas as pd

    out: dict[str, dict] = {}
    for path in sorted((TABLES / "datagovsg").glob("stations_*.parquet")):
        st = pd.read_parquet(path)
        for r in st.itertuples():
            out.setdefault(f"dgs:{r.station_id}", {"key": f"dgs:{r.station_id}", "latitude": float(r.latitude),
                                                   "longitude": float(r.longitude)})
    isd = TABLES / "isd"
    if isd.exists():
        frames = [pd.read_parquet(p, columns=["station_id", "latitude", "longitude"]) for p in sorted(isd.glob("obs_*.parquet"))]
        d = pd.concat(frames).groupby("station_id")[["latitude", "longitude"]].median()
        for sid, r in d.iterrows():
            out[f"isd:{sid}"] = {"key": f"isd:{sid}", "latitude": float(r.latitude), "longitude": float(r.longitude)}
    return sorted(out.values(), key=lambda s: s["key"])


def models(cfg: dict) -> list[dict]:
    """Operational models from config, each with the first valid day it is scored from."""
    start = dt.date.fromisoformat(str(cfg["period"]["day_level_lead_times"]["start"]))
    out = [{"id": m, "from": start} for m in cfg["forecast_sources"] if m not in ("persistence", "climatology")]
    for m in cfg.get("secondary_forecast_sources") or []:
        out.append({"id": m["id"], "from": dt.date.fromisoformat(str(m["from"]))})
    return out


def _key(coords: list[tuple[float, float]]) -> str:
    return hashlib.sha1(json.dumps(coords).encode()).hexdigest()[:12]


def grid(cfg: dict, ledger: Ledger, polite: Polite, batch: int = 50) -> Path:
    """Ask Open-Meteo which cell it uses for each station, per model and cell rule."""
    import pandas as pd

    sts = stations()
    rows = []
    for m in models(cfg):
        for rule in CELL_RULES:
            for i in range(0, len(sts), batch):
                part = sts[i:i + batch]
                coords = [(s["latitude"], s["longitude"]) for s in part]
                params = {
                    "latitude": ",".join(f"{la:.5f}" for la, _ in coords),
                    "longitude": ",".join(f"{lo:.5f}" for _, lo in coords),
                    "hourly": "temperature_2m_previous_day1", "models": m["id"], "cell_selection": rule,
                    "timezone": "GMT",
                    "start_date": GRID_PROBE_DAY.isoformat(), "end_date": GRID_PROBE_DAY.isoformat(),
                }
                if rule == "nearest":
                    params["elevation"] = ",".join(["nan"] * len(coords))
                folder = rule if rule == "nearest" else f"{rule}-dem"
                path = CACHE / "grid" / m["id"] / folder / f"{_key(coords)}.json.gz"
                body = fetch(PREVIOUS, params, path, weight(len(coords), 1, 1), ledger, polite)
                body = body if isinstance(body, list) else [body]
                if len(body) != len(part):
                    raise FetchError(f"grid: {len(part)} locations asked, {len(body)} returned ({m['id']} {rule})")
                for s, b in zip(part, body):
                    # With elevation=nan the reported elevation is the cell's own mean height.
                    # Otherwise it is the elevation model's value at the station point.
                    rows.append({"station_key": s["key"], "station_lat": s["latitude"], "station_lon": s["longitude"],
                                 "model": m["id"], "cell_rule": rule, "cell_lat": round(b["latitude"], CELL_DECIMALS),
                                 "cell_lon": round(b["longitude"], CELL_DECIMALS),
                                 "cell_elevation_m": b.get("elevation") if rule == "nearest" else None,
                                 "point_elevation_m": b.get("elevation") if rule != "nearest" else None})
    out = TABLES / "openmeteo"
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_parquet(out / "grid.parquet", index=False)
    print(df.groupby(["model", "cell_rule"]).agg(stations=("station_key", "size"),
                                                 cells=("cell_lat", lambda s: len(set(zip(s, df.loc[s.index, "cell_lon"])))))
          .to_string())
    return out / "grid.parquet"


def cells(model: str, station_prefix: str | None = None) -> list[tuple[float, float]]:
    import pandas as pd

    g = pd.read_parquet(TABLES / "openmeteo" / "grid.parquet")
    g = g[g["model"] == model]
    if station_prefix:
        g = g[g["station_key"].str.startswith(station_prefix)]
    return sorted(set(zip(g["cell_lat"], g["cell_lon"])))


def _cell_dir(kind: str, model: str, cell: tuple[float, float]) -> Path:
    return CACHE / kind / model / f"{cell[0]:.4f}_{cell[1]:.4f}"


# ---------------------------------------------------------------- Previous Runs

def previous_variables(cfg: dict) -> list[str]:
    return [f"{VARIABLES[v]}_previous_day{d}" for v in cfg["variables"] for d in cfg["lead_times"]["days"]]


def chunks(start: dt.date, end: dt.date, days: int = CHUNK_DAYS):
    a = start
    while a <= end:
        b = min(end, a + dt.timedelta(days=days - 1))
        yield a, b
        a = b + dt.timedelta(days=1)


def previous(cfg: dict, ledger: Ledger, polite: Polite) -> int:
    end = dt.date.fromisoformat(str(cfg["period"]["day_level_lead_times"]["end"]))
    hourly = previous_variables(cfg)
    n = 0
    for m in models(cfg):
        cs = cells(m["id"])
        for a, b in chunks(m["from"], end):
            for cell in cs:
                path = _cell_dir("previous", m["id"], cell) / f"{a}_{b}.json.gz"
                params = {
                    "latitude": f"{cell[0]:.4f}", "longitude": f"{cell[1]:.4f}", "hourly": ",".join(hourly),
                    "models": m["id"], "cell_selection": "nearest", "elevation": "nan", "timezone": "GMT",
                    "wind_speed_unit": "ms", "start_date": a.isoformat(), "end_date": b.isoformat(),
                }
                body = fetch(PREVIOUS, params, path, weight(1, len(hourly), (b - a).days + 1), ledger, polite)
                got = (round(body["latitude"], 4), round(body["longitude"], 4))
                if math.dist(got, (round(cell[0], 4), round(cell[1], 4))) > 1e-3:
                    raise FetchError(f"asked for cell {cell}, got {got} ({m['id']})")
                n += 1
            print(f"previous {m['id']} {a}..{b} cells={len(cs)}", flush=True)
    return n


# ---------------------------------------------------------------- Single Runs

def single(cfg: dict, ledger: Ledger, polite: Polite, run_hours=None) -> int:
    """Whole runs for the hour-level period, for the cells that hold data.gov.sg stations.
    Run hours come from config lead_times.single_run_hours_utc, the same list the scorer uses."""
    run_hours = tuple(run_hours or cfg["lead_times"]["single_run_hours_utc"])
    per = cfg["period"]["hour_level_lead_times"]
    start = dt.date.fromisoformat(str(per["start"]))
    end = dt.date.fromisoformat(str(per["end"]))
    hourly = ",".join(VARIABLES[v] for v in cfg["variables"])
    n = 0
    for m in [x for x in models(cfg) if x["id"] in cfg["forecast_sources"]]:
        cs = cells(m["id"], "dgs:")
        day = start
        while day <= end:
            for h in run_hours:
                run = dt.datetime(day.year, day.month, day.day, h)
                folder = CACHE / "single" / m["id"] / f"{day:%Y}" / f"{run:%Y-%m-%dT%H}"
                path = folder / f"{_key(cs)}.json.gz"
                if (folder / "NOT_AVAILABLE").exists():
                    continue
                params = {
                    "latitude": ",".join(f"{c[0]:.4f}" for c in cs),
                    "longitude": ",".join(f"{c[1]:.4f}" for c in cs),
                    "hourly": hourly, "models": m["id"], "run": f"{run:%Y-%m-%dT%H:%M}",
                    "cell_selection": "nearest", "elevation": ",".join(["nan"] * len(cs)),
                    "timezone": "GMT", "wind_speed_unit": "ms",
                }
                try:
                    fetch(SINGLE, params, path, weight(len(cs), 3, 7), ledger, polite)
                    n += 1
                except FetchError as err:
                    if "not available" in str(err):
                        folder.mkdir(parents=True, exist_ok=True)
                        (folder / "NOT_AVAILABLE").write_text(str(err)[:500] + "\n")
                    else:
                        raise
            if day.day == 1:
                print(f"single {m['id']} {day:%Y-%m} cells={len(cs)}", flush=True)
            day += dt.timedelta(days=1)
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=["grid", "previous", "single", "all"])
    args = ap.parse_args(argv)
    cfg = load_config()
    ledger, polite = Ledger(), Polite()
    if args.step in ("grid", "all"):
        grid(cfg, ledger, polite)
    if args.step in ("previous", "all"):
        print(f"previous: {previous(cfg, ledger, polite)} cell chunks on disk", flush=True)
    if args.step in ("single", "all"):
        print(f"single: {single(cfg, ledger, polite)} runs on disk", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
