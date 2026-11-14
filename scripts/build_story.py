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

    # The scorecard and the extremes test (scorer.summary).
    sk = pd.read_parquet(TABLES / "results" / "skill.parquet")
    def row(r):
        return {"s": r.source, "v": r.variable, "l": int(r.lead), "p": r4(r.percent), "lo": r4(r.low),
                "hi": r4(r.high), "d": int(r.n_days)}

    models = sk[sk.source != "always_dry"]
    skill = [row(r) for r in models[models.score == "rmse"].itertuples()]  # the scorecard: root mean square error
    # Rain one day ahead under both scores, with the always-dry forecast: what each score rewards.
    rain = sk[sk.variable.isin(["rain_hourly", "rain_6h"]) & (sk.lead == 1)]
    rain_scores = [{**row(r), "score": r.score} for r in rain.itertuples()]
    ex = pd.read_parquet(TABLES / "results" / "extremes.parquet")
    ext = [{"s": r.source, "ref": r.reference, "q": float(r.q), "f": r4(r.forecast_q), "o": r4(r.observed_q),
            "r": r4(r.rqe), "lo": r4(r.low), "hi": r4(r.high)} for r in ex[ex.lead == 1].itertuples()]
    pod = flat[(flat.metric == "pod") & (flat.threshold == 10.0) & (flat.lead == 1) & flat.against.isna()
               & (flat.source == "gfs_global")]
    heavy = {"gfs_pod10": r4(pod.value.iloc[0])}

    # Decision value (scorer.summary) and the ERA5 comparison (scorer.reanalysis), one day ahead
    # except the ERA5-judged scorecard, which has every lead day.
    de = pd.read_parquet(TABLES / "results" / "decision.parquet")
    dec = [{"s": r.source, "w": r.window, "a": float(r.cost_loss_ratio), "v": r4(r.value), "lo": r4(r.low),
            "hi": r4(r.high)} for r in de[de.lead == 1].itertuples()]
    re_ = pd.read_parquet(TABLES / "results" / "reanalysis.parquet")
    rea = [{"j": r.judge, "ref": r.reference, "s": r.source, "v": r.variable, "l": int(r.lead), "p": r4(r.percent),
            "lo": r4(r.low), "hi": r4(r.high), "d": int(r.n_days)} for r in re_.itertuples()]
    rb = pd.read_parquet(TABLES / "results" / "reanalysis_bias.parquet")
    reb = [{"v": r.variable, "y": r4(r.value), "lo": r4(r.low), "hi": r4(r.high)} for r in rb.itertuples()]
    rx = pd.read_parquet(TABLES / "results" / "reanalysis_extremes.parquet")
    rex = [{"ref": r.reference, "q": float(r.q), "f": r4(r.forecast_q), "o": r4(r.observed_q), "r": r4(r.rqe),
            "lo": r4(r.low), "hi": r4(r.high)} for r in rx.itertuples()]

    # Validation tables and the small trained model (scorer.validation, scorer.postprocess).
    def rec(df):
        return [{k: (r4(v) if isinstance(v, float) else v) for k, v in r.items()} for r in df.to_dict("records")]

    ev = pd.read_parquet(TABLES / "results" / "evaluation.parquet")
    nb = pd.read_parquet(TABLES / "results" / "neighbours.parquet").assign(bin=lambda d: d["bin"].astype(str))
    extra = {"rain_scores": rain_scores, "evaluation": rec(ev), "neighbours": rec(nb),
             "ceiling": rec(pd.read_parquet(TABLES / "results" / "ceiling.parquet")),
             "postprocess": rec(pd.read_parquet(TABLES / "results" / "postprocess.parquet"))}

    # Stations with at least one scored hour in the test period, one day ahead, any variable.
    from tropics_scorecard.paths import load_config
    from tropics_scorecard.scorer import core

    cfg = load_config()
    scored = set()
    for v in ("rain_hourly", "temperature_2m", "wind_speed_10m"):
        scored |= set(core.cases_for(cfg, v, "day", 1)["station_key"].unique())

    data = {"lead": lead, "versus": versus, "by_hour": by_hour, "cell_rule": cell_rule, "amount": amount,
            "map": {"view": VIEW, "rings": bm["rings"], "stations": stations, "cells": cells}, "cases": cases,
            "counts": counts, "skill": skill, "ext": ext, "heavy": heavy, "dec": dec, "rea": rea, "reb": reb,
            "rex": rex, "scored": len(scored), **extra}
    template = (ROOT / "scripts" / "story_template.html").read_text(encoding="utf-8")
    page = template.replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    (ROOT / "dashboard" / "story.html").write_text(page, encoding="utf-8")
    (ROOT / "docs" / "index.html").write_text(page, encoding="utf-8")  # served by GitHub Pages
    # The hosted copy of the full dashboard, served by GitHub Pages next to the summary.
    import shutil

    site = ROOT / "docs" / "dashboard"
    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(ROOT / "dashboard", site, ignore=shutil.ignore_patterns("story.html"))
    (ROOT / "docs" / ".nojekyll").write_text("")
    add_counter(site)
    print("wrote dashboard/story.html", len(page) // 1024, "kB", counts)


def add_counter(site: Path) -> None:
    """Put the GoatCounter tag on the hosted pages, if config names an account.

    It counts page views without cookies or personal data. A link such as
    ?ref=name shows as its own referrer, so one shared link can be told apart.
    """
    from tropics_scorecard.paths import load_config

    code = ((load_config().get("analytics") or {}).get("goatcounter_code") or "").strip()
    if not code:
        return
    tag = (f'<script data-goatcounter="https://{code}.goatcounter.com/count" '
           'async src="https://gc.zgo.at/count.js"></script>')
    for page in [ROOT / "docs" / "index.html", *site.glob("*.html")]:
        html = page.read_text(encoding="utf-8")
        if "data-goatcounter" in html:
            continue
        html = html.replace("</body>", tag + "\n</body>") if "</body>" in html else html + "\n" + tag + "\n"
        page.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
