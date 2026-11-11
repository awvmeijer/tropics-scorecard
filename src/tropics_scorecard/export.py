"""Write the dashboard's precomputed JSON to dashboard/data/.

Everything the static site shows comes from here. Observation views come from the
reference and quality-control tables; score views come from data/tables/results, and stay
empty until the scorer has run.

Usage:
    python -m tropics_scorecard.export
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import pandas as pd

from .match import observations
from .paths import RAW, ROOT, TABLES, load_config

OUT = ROOT / "dashboard" / "data"
MAP_PAD_DEG = 0.1


def bbox(cfg: dict) -> dict:
    """The study region from config, padded a little so coastlines are not cut at stations."""
    b = cfg["region"]["bounding_box"]
    return {"south": b["south"] - MAP_PAD_DEG, "north": b["north"] + MAP_PAD_DEG,
            "west": b["west"] - MAP_PAD_DEG, "east": b["east"] + MAP_PAD_DEG}


def _write(name: str, payload) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(payload, separators=(",", ":"), default=_default), encoding="utf-8")
    return path


def _default(o):
    if isinstance(o, (pd.Timestamp, dt.date, dt.datetime)):
        return o.isoformat()
    if isinstance(o, float) and math.isnan(o):
        return None
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(type(o))


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


# ---------------------------------------------------------------- basemap

def _clip(ring, box):
    """Sutherland-Hodgman clip of one ring to the box. Points are (lon, lat)."""
    def clip_edge(pts, inside, cross):
        out = []
        for i, cur in enumerate(pts):
            prev = pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
        return out

    def at_x(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))

    def at_y(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)

    pts = [tuple(p) for p in ring]
    for inside, cross in (
        (lambda p: p[0] >= box["west"], at_x(box["west"])),
        (lambda p: p[0] <= box["east"], at_x(box["east"])),
        (lambda p: p[1] >= box["south"], at_y(box["south"])),
        (lambda p: p[1] <= box["north"], at_y(box["north"])),
    ):
        if not pts:
            break
        pts = clip_edge(pts, inside, cross)
    return pts


def _simplify(pts, tol):
    """Douglas-Peucker on an open polyline."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    far, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norm
        if d > far:
            far, idx = d, i
    if far <= tol:
        return [pts[0], pts[-1]]
    return _simplify(pts[: idx + 1], tol)[:-1] + _simplify(pts[idx:], tol)


def basemap(cfg: dict, tol: float = 0.002) -> Path | None:
    src = RAW / "basemap" / "ne_10m_land.geojson"
    if not src.exists():
        return None
    box = bbox(cfg)
    rings = []
    for f in json.loads(src.read_text())["features"]:
        g = f["geometry"]
        for poly in g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]:
            for ring in poly[:1]:  # outer rings; lakes do not matter at this scale
                c = _clip(ring, box)
                if len(c) > 1 and c[0] == c[-1]:
                    c = c[:-1]
                if len(c) < 3:
                    continue
                # Douglas-Peucker needs two distinct ends: split the ring at its farthest point.
                k = max(range(len(c)), key=lambda i: (c[i][0] - c[0][0]) ** 2 + (c[i][1] - c[0][1]) ** 2)
                s = _simplify(c[: k + 1], tol)[:-1] + _simplify(c[k:] + [c[0]], tol)
                if len(s) >= 4:
                    rings.append([[round(x, 4), round(y, 4)] for x, y in s])
    return _write("basemap.json", {"bbox": box, "rings": rings,
                                   "source": "Natural Earth 1:10m land, public domain"})


# ---------------------------------------------------------------- stations and grid

def stations() -> Path:
    rows = {}
    for path in sorted((TABLES / "datagovsg").glob("stations_*.parquet")):
        st = pd.read_parquet(path)
        for r in st.itertuples():
            key = f"dgs:{r.station_id}"
            e = rows.setdefault(key, {"key": key, "id": r.station_id, "name": r.name, "network": "dgs",
                                      "lat": round(float(r.latitude), 5), "lon": round(float(r.longitude), 5),
                                      "variables": set(), "first": str(r.first_day), "last": str(r.last_day)})
            e["variables"].add({"rainfall": "rain_hourly", "air-temperature": "temperature_2m",
                                "wind-speed": "wind_speed_10m"}.get(r.variable, r.variable))
            e["first"], e["last"] = min(e["first"], str(r.first_day)), max(e["last"], str(r.last_day))
    names = {"48698099999": "Changi Airport", "48694099999": "Paya Lebar", "48699099999": "Seletar",
             "48679099999": "Senai, Johor", "48602199999": "Mersing", "96087099999": "Batam Hang Nadim",
             "96091099999": "Kijang, Bintan"}
    isd = sorted((TABLES / "isd").glob("obs_*.parquet"))
    if isd:
        d = pd.concat([pd.read_parquet(p, columns=["station_id", "time_utc", "latitude", "longitude"]) for p in isd])
        for sid, g in d.groupby("station_id"):
            key = f"isd:{sid}"
            rows[key] = {"key": key, "id": sid, "name": names.get(sid, sid), "network": "isd",
                         "lat": round(float(g["latitude"].median()), 5), "lon": round(float(g["longitude"].median()), 5),
                         "variables": {"temperature_2m", "wind_speed_10m"},
                         "first": str(g["time_utc"].min().date()), "last": str(g["time_utc"].max().date())}
    cells = {}
    grid = TABLES / "openmeteo" / "grid.parquet"
    if grid.exists():
        g = pd.read_parquet(grid)
        for r in g.itertuples():
            cells.setdefault(r.model, {}).setdefault(r.cell_rule, {})[r.station_key] = [round(r.cell_lat, 4), round(r.cell_lon, 4)]
    sizes = {}
    if grid.exists():
        for model, gm in g.groupby("model"):
            # Latitude rows are evenly spaced on all four grids; longitudes are not on the
            # reduced Gaussian grid of IFS 9 km, so the row spacing sets the drawn cell size.
            v = sorted(set(gm["cell_lat"].round(4)))
            steps = [round(b - a, 4) for a, b in zip(v, v[1:]) if b - a > 1e-3]
            sizes[model] = min(steps) if steps else None
    out = [{**r, "variables": sorted(r["variables"])} for r in sorted(rows.values(), key=lambda r: r["key"])]
    return _write("stations.json", {"stations": out, "cells": cells, "cell_size_deg": sizes})


# ---------------------------------------------------------------- coverage and quality control

def coverage(cfg: dict) -> Path:
    per = cfg["period"]
    out = {}
    for v in observations.VARIABLES:
        frames = []
        for path in sorted(observations.OUT.glob(f"{v}_*.parquet")):
            frames.append(pd.read_parquet(path, columns=["station_key", "time_utc", "complete", "flagged"]))
        if not frames:
            continue
        d = pd.concat(frames, ignore_index=True)
        d["usable"] = d["complete"] & ~d["flagged"]
        d["month"] = d["time_utc"].dt.strftime("%Y-%m")
        g = d.groupby(["station_key", "month"]).agg(usable=("usable", "sum"), present=("usable", "size")).reset_index()
        months = sorted(g["month"].unique())
        hours = {m: pd.Period(m).days_in_month * 24 for m in months}
        keys = sorted(g["station_key"].unique())
        mat = {k: [None] * len(months) for k in keys}
        idx = {m: i for i, m in enumerate(months)}
        for r in g.itertuples():
            mat[r.station_key][idx[r.month]] = round(r.usable / hours[r.month], 3)
        out[v] = {"months": months, "stations": keys, "share_usable": [mat[k] for k in keys],
                  "total_usable_hours": int(d["usable"].sum()), "total_hours_present": int(len(d))}
    return _write("coverage.json", {"variables": out, "test_period": per["day_level_lead_times"],
                                    "climatology_years": per["climatology_years"]})


def qc_summary() -> Path:
    rows = []
    for path in sorted((TABLES / "qc").glob("flags_*.parquet")):
        f = pd.read_parquet(path, columns=["check"])
        name = path.stem.removeprefix("flags_")
        source, rest = name.split("_", 1)
        parts = rest.rsplit("_", 1)
        variable, year = (parts[0], parts[1]) if len(parts) == 2 and parts[1].isdigit() else (rest, None)
        for check, n in f["check"].value_counts().items():
            rows.append({"source": source, "variable": variable, "year": year, "check": check, "flags": int(n)})
    return _write("qc.json", {"flags": rows})


def diurnal(cfg: dict, threshold: float | None = None) -> Path | None:
    """Observed rain frequency by local hour and monsoon phase, test period only."""
    from .scorer.core import regime

    threshold = threshold if threshold is not None else cfg["rain_thresholds_mm_per_hour"][0]
    per = cfg["period"]["day_level_lead_times"]
    d = observations.load("rain_hourly", per["start"], f"{per['end']} 23:00")
    if d.empty:
        return None
    local = d["time_utc"].dt.tz_convert(cfg["region"]["local_timezone"])
    d = d.assign(hour=local.dt.hour, regime=regime(local, cfg["regimes"]), wet=d["value"] >= threshold)
    out = {}
    for name, g in [("all", d)] + list(d.groupby("regime")):
        h = g.groupby("hour")["wet"].agg(["mean", "size"])
        out[name] = {"share_wet": [round(float(x), 4) for x in h["mean"]], "station_hours": [int(x) for x in h["size"]]}
    return _write("diurnal.json", {"threshold_mm": threshold, "by_regime": out,
                                   "period": {"start": str(d["time_utc"].min()), "end": str(d["time_utc"].max())}})


# ---------------------------------------------------------------- scores and status

def scores() -> Path:
    path = TABLES / "results" / "results.parquet"
    if not path.exists():
        return _write("scores.json", {"rows": [], "columns": []})
    df = pd.read_parquet(path)
    cols = list(df.columns)
    rows = [[_clean(v) for v in r] for r in df.itertuples(index=False, name=None)]
    return _write("scores.json", {"columns": cols, "rows": rows})


def metric_status() -> dict:
    """Which hand-written metric functions exist yet. A stub raises NotImplementedError."""
    from .metrics import bootstrap, categorical, episodes, errors, geo, probabilistic, timeseries

    probes = {
        errors: {"bias": ([1.0], [1.0]), "mae": ([1.0], [1.0]), "rmse": ([1.0], [1.0]),
                 "rmse_by_lead_time": ([(1, 1.0, 1.0)],)},
        categorical: {"contingency": ([True], [True]), "pod": (1, 0, 0, 0), "far": (1, 0, 0, 0),
                      "csi": (1, 0, 0, 0), "ets": (1, 0, 0, 1)},
        probabilistic: {"brier_score": ([0.5], [1]), "reliability_table": ([0.5], [1], 2), "crps_ensemble": ([1.0], 1.0)},
        bootstrap: {"bootstrap_ci_mean_diff": ([1.0, 2.0], [1.0, 1.0], 10), "block_bootstrap_ci_mean_diff": ([1.0, 2.0], [1.0, 1.0], 1, 10)},
        geo: {"haversine_km": (1.0, 103.0, 1.0, 104.0), "nearest_station": (1.0, 103.0, {"a": (1.0, 103.0)})},
        timeseries: {"rolling_mean": ([1.0, 2.0], 1), "resample_mean": ([0, 1], [1.0, 2.0], 1, 0)},
        episodes: {"merge_intervals": ([(0, 1)],)},
    }
    status = {}
    for mod, fns in probes.items():
        for name, args in fns.items():
            try:
                getattr(mod, name)(*args)
                state = "written"
            except NotImplementedError:
                state = "stub"
            except Exception:  # written, but our probe input upset it: still not a stub
                state = "written"
            status[f"{mod.__name__.rsplit('.', 1)[-1]}.{name}"] = state
    return status


def downloads(cfg: dict) -> dict:
    """Days on disk against days wanted, per download stream."""
    from .ingest.datagovsg import CACHE

    per = cfg["period"]
    # Observations start early enough for persistence at the longest lead day.
    first = dt.date.fromisoformat(str(per["day_level_lead_times"]["start"])) - dt.timedelta(days=max(cfg["lead_times"]["days"]))
    test = (first, dt.date.fromisoformat(str(per["day_level_lead_times"]["end"])))
    clim = (dt.date.fromisoformat(str(per["climatology_years"]["start"])), dt.date.fromisoformat(str(per["climatology_years"]["end"])))

    def done(folder: Path, span) -> int:
        n = 0
        for y in range(span[0].year, span[1].year + 1):
            for d in (folder / str(y)).glob("*/DONE") if (folder / str(y)).exists() else []:
                day = dt.date.fromisoformat(d.parent.name)
                n += span[0] <= day <= span[1]
        return n

    want = lambda s: (s[1] - s[0]).days + 1  # noqa: E731
    out = {}
    for label, folder, span in [
        ("Rain, test period", CACHE / "rainfall", test),
        ("Temperature, test period", CACHE / "air-temperature-v1", test),
        ("Wind, test period", CACHE / "wind-speed-v1", test),
        ("Rain, climatology years", CACHE / "rainfall-v1", clim),
        ("Temperature, climatology years", CACHE / "air-temperature-v1", clim),
        ("Wind, climatology years", CACHE / "wind-speed-v1", clim),
    ]:
        out[label] = {"days_done": done(folder, span), "days_wanted": want(span)}
    return out


def meta(cfg: dict) -> Path:
    results = TABLES / "results" / "results.parquet"
    return _write("meta.json", {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
        "protocol_signed_off": cfg.get("proposals_accepted") is True,
        "scored": results.exists(),
        "metrics": metric_status(),
        "downloads": downloads(cfg),
        "period": {k: {kk: str(vv) for kk, vv in v.items()} for k, v in cfg["period"].items()},
        "variables": cfg["variables"],
        "sources": cfg["forecast_sources"],
        "secondary_sources": cfg.get("secondary_forecast_sources") or [],
        "rain_thresholds_mm_per_hour": cfg["rain_thresholds_mm_per_hour"],
        "lead_days": cfg["lead_times"]["days"],
        "cell_rule": cfg["matching"]["cell_rule"],
    })


def main(argv=None) -> int:
    cfg = load_config()
    for fn in (lambda: basemap(cfg), stations, lambda: coverage(cfg), qc_summary, lambda: diurnal(cfg), scores, lambda: meta(cfg)):
        p = fn()
        print(p if p is None else f"{p.relative_to(ROOT)} {p.stat().st_size // 1024} kB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
