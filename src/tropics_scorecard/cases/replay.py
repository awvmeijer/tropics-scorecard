"""Replay one event from a single command, and write its data for the case page.

    python -m tropics_scorecard.cases.replay surge_2025_03
    python -m tropics_scorecard.cases.replay --all

Writes dashboard/data/cases/<id>.json and, the first time only, a page skeleton in
docs/cases/<id>.md. The skeleton has the facts and tables; the diagnosis is left for the
author to write, and a later run never overwrites the page.

What goes in:
- observations: hourly network mean, gauges with rain, and the wettest gauge, for rain;
  network mean temperature and wind; every gauge's event total for the map
- the Changi soundings in the event window and the last one before it
- forecasts at lead days 1, 3 and 5, averaged over the same stations as the observations.
  Forecasts are left out until the verification protocol is signed off
  (config proposals_accepted), so no forecast is looked at before then.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from ..match import observations
from ..paths import ROOT, TABLES, load_config

CASES = ROOT / "config" / "cases.yaml"
OUT = ROOT / "dashboard" / "data" / "cases"
PAGES = ROOT / "docs" / "cases"
LEADS = (1, 3, 5)
TOP_HPA = 100.0


def load_cases() -> dict:
    return yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]


def _window(case: dict, tz: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    a = pd.Timestamp(str(case["start"])).tz_localize(tz).tz_convert("UTC")
    b = pd.Timestamp(str(case["end"])).tz_localize(tz).tz_convert("UTC")
    return a, b


def _round(v, d=2):
    return None if pd.isna(v) else round(float(v), d)


def observed(variable: str, a, b) -> pd.DataFrame:
    return observations.load(variable, a, b)


def network_series(obs: pd.DataFrame, tz: str, wet_mm: float | None = None) -> list[dict]:
    if obs.empty:
        return []
    g = obs.groupby("time_utc")["value"]
    df = pd.DataFrame({"mean": g.mean(), "max": g.max(), "n": g.size()})
    if wet_mm is not None:
        df["wet"] = g.apply(lambda v: int((v >= wet_mm).sum()))
    out = []
    for t, r in df.iterrows():
        row = {"t": t.tz_convert(tz).strftime("%Y-%m-%d %H:%M"), "mean": _round(r["mean"]), "max": _round(r["max"]), "n": int(r["n"])}
        if wet_mm is not None:
            row["wet"] = int(r["wet"])
        out.append(row)
    return out


def soundings(a, b) -> list[dict]:
    s = pd.read_parquet(TABLES / "igra" / "soundings.parquet")
    lv = pd.read_parquet(TABLES / "igra" / "levels.parquet")
    before = s[s["nominal_time_utc"] < a].tail(1)
    inside = s[(s["nominal_time_utc"] >= a) & (s["nominal_time_utc"] <= b)]
    out = []
    for r in pd.concat([before, inside]).itertuples():
        L = lv[(lv["sounding_id"] == r.sounding_id) & (lv["pressure_hpa"] >= TOP_HPA)].dropna(subset=["pressure_hpa"])
        L = L.sort_values("pressure_hpa", ascending=False)
        levels = []
        for x in L.itertuples():
            t = x.temperature_c
            dpd = x.dewpoint_depression_c
            levels.append({"p": _round(x.pressure_hpa, 1), "z": _round(x.height_m, 0), "t": _round(t, 1),
                           "td": _round(t - dpd, 1) if pd.notna(t) and pd.notna(dpd) else None,
                           "wd": _round(x.wind_dir_deg, 0), "ws": _round(x.wind_speed_ms, 1)})
        out.append({"id": r.sounding_id, "time_utc": r.nominal_time_utc.isoformat(), "release_hhmm": r.release_hhmm,
                    "before_event": bool(r.nominal_time_utc < a), "levels": levels})
    return out


def forecasts(cfg: dict, variable: str, obs: pd.DataFrame, tz: str) -> dict:
    """Network-mean forecast per model and lead day, on the stations and hours observed."""
    from ..sources import get_source

    out = {}
    if obs.empty:
        return out
    models = [m for m in cfg["forecast_sources"] if m not in ("persistence", "climatology")]
    for name in models + ["persistence", "climatology"]:
        src = get_source(name, cfg)
        for lead in LEADS:
            cases = obs[["station_key", "time_utc"]].rename(columns={"time_utc": "valid_time"}).assign(lead_kind="day", lead=lead)
            try:
                f = src.predict(variable, cases)
            except LookupError:
                continue
            s = pd.DataFrame({"t": cases["valid_time"], "f": f.to_numpy()}).dropna().groupby("t")["f"].mean()
            out.setdefault(name, {})[str(lead)] = [{"t": t.tz_convert(tz).strftime("%Y-%m-%d %H:%M"), "mean": _round(v)} for t, v in s.items()]
    return out


def replay(case_id: str, cfg: dict | None = None) -> Path:
    cfg = cfg or load_config()
    case = load_cases()[case_id]
    tz = cfg["region"]["local_timezone"]
    a, b = _window(case, tz)
    rain = observed("rain_hourly", a, b)
    temp = observed("temperature_2m", a, b)
    wind = observed("wind_speed_10m", a, b)
    totals = rain.groupby("station_key")["value"].agg(["sum", "size"]).reset_index()
    signed_off = cfg.get("proposals_accepted") is True
    payload = {
        "id": case_id, "title": case["title"], "kind": case.get("kind"), "sources": case.get("sources", []),
        "window_local": [str(case["start"]), str(case["end"])],
        "observed": {
            "rain_hourly": network_series(rain, tz, wet_mm=cfg["rain_thresholds_mm_per_hour"][0]),
            "temperature_2m": network_series(temp, tz),
            "wind_speed_10m": network_series(wind, tz),
            "rain_totals": [{"station": r.station_key, "mm": _round(r.sum, 1), "hours": int(r.size)} for r in totals.itertuples()],
        },
        "soundings": soundings(a, b),
        "forecasts_included": signed_off,
        "forecasts": {v: forecasts(cfg, v, o, tz) for v, o in (("rain_hourly", rain), ("temperature_2m", temp))} if signed_off else {},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{case_id}.json"
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    _skeleton(case_id, case, payload)
    return path


def _skeleton(case_id: str, case: dict, payload: dict) -> None:
    page = PAGES / f"{case_id}.md"
    if page.exists():
        return
    rain = payload["observed"]["rain_hourly"]
    peak = max(rain, key=lambda r: r["mean"] or 0) if rain else None
    total = sum((r["mean"] or 0) for r in rain)
    src = "\n".join(f"- {u}" for u in payload["sources"])
    text = f"""# {case['title']}

Window: {case['start']} to {case['end']}, Singapore time. Replay: `python -m tropics_scorecard.cases.replay {case_id}`.

## What happened

Public reports:
{src}

From the gauges: network-mean rain over the window {total:.1f} mm.{f" The wettest hour for the network ended {peak['t']}, with a network mean of {peak['mean']} mm and {peak.get('wet')} gauges wet." if peak else ""}

## What each forecast said

Filled in by the replay tool once the protocol is signed off: network-mean forecast at lead days 1, 3 and 5, against the gauges.

## The sounding

Changi soundings in the window and the last one before it are in the case data and on the dashboard.

## Diagnosis

To write: what physically happened, and why each forecast went the way it did.

## Failure mode

To write: one entry for docs/failure_modes.md.
"""
    PAGES.mkdir(parents=True, exist_ok=True)
    page.write_text(text, encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", nargs="?")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config()
    ids = list(load_cases()) if args.all else [args.case]
    for cid in ids:
        print(replay(cid, cfg).relative_to(ROOT), flush=True)
    chosen = yaml.safe_load(CASES.read_text(encoding="utf-8")).get("chosen") or list(load_cases())
    index = [{"id": k, "title": v["title"], "kind": v.get("kind")} for k, v in load_cases().items() if k in chosen]
    (OUT / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
