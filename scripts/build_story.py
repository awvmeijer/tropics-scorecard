"""Build the one-page summary, dashboard/story.html, from the results and dashboard data.

A single self-contained file: the numbers are embedded, nothing is fetched. Rerun after
scoring. Usage:
    uv run python scripts/build_story.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tropics_scorecard.paths import ROOT, TABLES

DATA = ROOT / "dashboard" / "data"
MAIN = ["gfs_global", "ecmwf_ifs025", "persistence", "climatology"]
VIEW = {"south": 1.13, "north": 1.54, "west": 103.55, "east": 104.15}


def r4(v):
    return None if pd.isna(v) else round(float(v), 4)


def main() -> None:
    res = pd.read_parquet(TABLES / "results" / "results.parquet")
    base = res[(res.qc == "flags_removed") & (res.station == "all") & (res.lead_kind == "day")]
    flat = base[(base.hour_local == "all") & (base.regime == "all")]

    lead = {}
    for v in ("rain_hourly", "rain_6h", "temperature_2m", "wind_speed_10m"):
        d = flat[(flat.variable == v) & (flat.metric == "mae") & flat.against.isna() & flat.source.isin(MAIN)]
        lead[v] = {s: [{"x": int(r.lead), "y": r4(r.value), "lo": r4(r.low), "hi": r4(r.high)}
                       for r in g.sort_values("lead").itertuples()] for s, g in d.groupby("source")}

    cmp_rows = flat[(flat.metric == "mae") & (flat.lead == 1) & (flat.against == "climatology")]
    versus = {v: [{"s": r.source, "y": r4(r.value), "lo": r4(r.low), "hi": r4(r.high)} for r in g.itertuples()]
              for v, g in cmp_rows.groupby("variable")}

    hours = base[(base.regime == "all") & (base.hour_local != "all") & (base.lead == 1) & base.against.isna()]
    by_hour = {}
    for v, metric in (("temperature_2m", "bias"), ("rain_hourly", "mae")):
        d = hours[(hours.variable == v) & (hours.metric == metric) & hours.source.isin(MAIN)]
        by_hour[f"{v}_{metric}"] = {s: [{"x": int(r.hour_local), "y": r4(r.value), "lo": r4(r.low), "hi": r4(r.high)}
                                        for r in g.assign(h=g.hour_local.astype(int)).sort_values("h").itertuples()]
                                    for s, g in d.groupby("source")}

    cell = flat[(flat.metric == "mae") & (flat.lead == 1) & (flat.source == "ecmwf_ifs025@land") & (flat.against == "ecmwf_ifs025")]
    cell_rule = {r.variable: {"y": r4(r.value), "lo": r4(r.low), "hi": r4(r.high)} for r in cell.itertuples()}

    # Mean forecast rain by lead for the cells over Singapore: shows the archive fault.
    amount = {}
    for m in ("gfs_global", "ecmwf_ifs025"):
        t = pd.read_parquet(TABLES / "openmeteo" / f"previous_{m}.parquet", filters=[("variable", "==", "rain_hourly")])
        t = t[t.cell_lat.between(1.2, 1.4)]
        amount[m] = [{"x": int(k), "y": r4(v)} for k, v in t.groupby("lead_day").value.mean().items()]

    st = json.loads((DATA / "stations.json").read_text())
    bm = json.loads((DATA / "basemap.json").read_text())
    stations = [{"k": s["key"], "lat": s["lat"], "lon": s["lon"], "isd": s["network"] == "isd"} for s in st["stations"]
                if VIEW["south"] <= s["lat"] <= VIEW["north"] and VIEW["west"] <= s["lon"] <= VIEW["east"]]
    cells = {rule: {k: v for k, v in st["cells"]["ecmwf_ifs025"][rule].items()} for rule in ("nearest", "land")}

    cases = {}
    for cid in ("surge_2025_03", "squall_2024_09_17", "dry_2024_07"):
        c = json.loads((DATA / "cases" / f"{cid}.json").read_text())
        obs = c["observed"]["rain_hourly"]
        f = c["forecasts"]["rain_hourly"]
        look = {m: {p["t"]: p["mean"] for p in f[m]["1"]} for m in ("gfs_global", "ecmwf_ifs025")}
        cases[cid] = {"title": c["title"], "t": [o["t"] for o in obs], "obs": [o["mean"] for o in obs],
                      "gfs_global": [look["gfs_global"].get(o["t"]) for o in obs],
                      "ecmwf_ifs025": [look["ecmwf_ifs025"].get(o["t"]) for o in obs]}

    n = flat[(flat.metric == "mae") & (flat.lead == 1) & flat.against.isna() & (flat.source == "ecmwf_ifs025")]
    counts = {r.variable: int(r.n_pairs) for r in n.itertuples()}
    data = {"lead": lead, "versus": versus, "by_hour": by_hour, "cell_rule": cell_rule, "amount": amount,
            "map": {"view": VIEW, "rings": bm["rings"], "stations": stations, "cells": cells}, "cases": cases,
            "counts": counts}
    template = (ROOT / "scripts" / "story_template.html").read_text(encoding="utf-8")
    out = template.replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    (ROOT / "dashboard" / "story.html").write_text(out, encoding="utf-8")
    (ROOT / "docs" / "index.html").write_text(out, encoding="utf-8")  # served by GitHub Pages
    print("wrote dashboard/story.html", len(out) // 1024, "kB", counts)


if __name__ == "__main__":
    main()
