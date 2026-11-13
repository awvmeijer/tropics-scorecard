"""Draw the README figures as animated SVG, in a dark and a light version.

GitHub shows SVG images with their CSS animations and picks the version by colour scheme.
Plain files, no script. The result figure reads the scored results, so rerun after scoring.
    uv run python scripts/build_readme_figures.py
"""
from __future__ import annotations

import pandas as pd

from tropics_scorecard.paths import ROOT, TABLES

OUT = ROOT / "docs" / "assets"
SANS = "font-family=\"'Inter Tight', Inter, system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif\""
THEMES = {
    "dark": dict(bg="#030303", card="#101010", edge="#2c2c2c", title="#ffffff", sub="#8f8f8f", label="#8f8f8f", wire="#3a3a3a",
                 accent="#1e9bff", glow=("rgba(0,105,190,.22)", "rgba(0,80,150,.07)"), gfs="#3987e5", ifs="#d95926", other="#9a9a9a", zero="#8f8f8f"),
    "light": dict(bg="#ffffff", card="#ffffff", edge="#d9d9d9", title="#0a0a0a", sub="#5e5e5e", label="#5e5e5e", wire="#cfcfcf",
                  accent="#0a78d6", glow=("rgba(0,120,215,.10)", "rgba(0,120,215,.03)"), gfs="#2a78d6", ifs="#eb6834", other="#5e5e5e", zero="#3d3d3d"),
}
STYLE = ("<style>.n{opacity:0;animation:in .7s ease-out forwards}@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}"
         ".halo{animation:halo 2.6s ease-in-out infinite}@keyframes halo{0%,100%{opacity:.35}50%{opacity:1}}"
         ".bar{transform-box:fill-box;transform-origin:center;animation:grow .9s ease-out both}@keyframes grow{from{transform:scaleX(0)}}"
         ".dot{animation:pop .5s ease-out both}@keyframes pop{from{opacity:0}}"
         "@media (prefers-reduced-motion: reduce){.n,.halo,.bar,.dot{animation:none;opacity:1}}</style>")


def frame(t, w, h, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{label}"><title>{label}</title>'
            f'<defs><radialGradient id="bg" cx="50%" cy="62%" r="55%"><stop offset="0%" stop-color="{t["glow"][0]}"/><stop offset="45%" stop-color="{t["glow"][1]}"/>'
            f'<stop offset="100%" stop-color="{t["bg"]}" stop-opacity="0"/></radialGradient></defs>{STYLE}'
            f'<rect width="{w}" height="{h}" rx="14" fill="{t["bg"]}"/><rect width="{w}" height="{h}" rx="14" fill="url(#bg)"/>')


def card(t, x, y, w, h, title, sub, delay, accent=False, sub2=None):
    edge, sw = (t["accent"], 1.4) if accent else (t["edge"], 1)
    out = f'<g class="n" style="animation-delay:{delay:.2f}s"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{t["card"]}" stroke="{edge}" stroke-width="{sw}"/>'
    out += f'<text x="{x + 16}" y="{y + 27}" {SANS} font-size="15" font-weight="500" fill="{t["title"]}">{title}</text>'
    out += f'<text x="{x + 16}" y="{y + 49}" {SANS} font-size="12.5" fill="{t["sub"]}">{sub}</text>'
    if sub2:
        out += f'<text x="{x + 16}" y="{y + 66}" {SANS} font-size="12.5" fill="{t["sub"]}">{sub2}</text>'
    return out + "</g>"


def stage(t, x, text):
    return f'<text x="{x}" y="48" {SANS} font-size="11" letter-spacing="2.2" fill="{t["label"]}">{text}</text>'


def wire(t, d, pulse=None, delay=0.0, dur=3.4):
    out = f'<path d="{d}" fill="none" stroke="{t["wire"]}" stroke-width="1.2"/>'
    if pulse:
        out += f'<circle r="3.2" fill="{pulse}"><animateMotion dur="{dur}s" begin="{delay}s" repeatCount="indefinite" path="{d}"/></circle>'
    return out


def pipeline(theme: str) -> str:
    t = THEMES[theme]
    W, H = 1040, 560
    s = [frame(t, W, H, "Tropics Scorecard pipeline: station observations and archived forecasts are matched on the same cases, scored against two baselines through one scorer, and reported with intervals.")]
    s += [stage(t, 44, "01 · MEASURE"), stage(t, 336, "02 · MATCH"), stage(t, 676, "03 · SCORE")]
    # connectors: sources into quality control and the reference
    for i, y in enumerate((102, 176, 250)):
        s.append(wire(t, f"M260,{y} H298 V118 H336", t["title"], delay=i * 0.9))
    s.append(wire(t, "M260,324 H298 V246 H336", t["accent"], delay=0.5))
    s.append(wire(t, "M468,150 V196"))
    s.append(wire(t, "M600,262 H638 V128 H676", t["accent"], delay=1.2))
    s.append(wire(t, "M638,210 H676"))
    s.append(wire(t, "M638,262 V292 H676"))
    s.append(f'<path d="M468,424 V352" fill="none" stroke="{t["sub"]}" stroke-width="1.2" stroke-dasharray="3 4"/><path d="M463,359 L468,351 L473,359" fill="none" stroke="{t["sub"]}" stroke-width="1.2"/>'
             f'<text x="480" y="386" {SANS} font-size="11" letter-spacing="2" fill="{t["label"]}">REPLAY</text>')
    s.append(card(t, 44, 72, 216, 60, "Rain gauges", "5-minute totals, 2017 to 2026", 0.0))
    s.append(card(t, 44, 146, 216, 60, "Weather stations", "temperature and wind, 1 minute", 0.1))
    s.append(card(t, 44, 220, 216, 60, "Airports and soundings", "hourly reports, balloon profiles", 0.2))
    s.append(card(t, 44, 294, 216, 60, "Forecast archive", "GFS and ECMWF, 1 to 7 days ahead", 0.3))
    s.append(card(t, 336, 72, 264, 78, "Quality control", "every flag logged; an hour counts only", 0.4, sub2="when complete"))
    s.append(f'<g class="n" style="animation-delay:.5s"><rect x="336" y="196" width="264" height="156" rx="14" fill="{t["card"]}" stroke="{t["edge"]}"/>'
             f'<text x="352" y="223" {SANS} font-size="15" font-weight="500" fill="{t["title"]}">One scorer</text>'
             f'<text x="352" y="245" {SANS} font-size="12.5" fill="{t["sub"]}">the same cases for every source</text>'
             f'<rect x="352" y="256" width="232" height="38" rx="9" fill="{t["card"]}" stroke="{t["edge"]}"/>'
             f'<text x="364" y="272" {SANS} font-size="12.5" font-weight="500" fill="{t["title"]}">Persistence and climatology</text>'
             f'<text x="364" y="287" {SANS} font-size="11" fill="{t["sub"]}">baselines, scored exactly like a model</text>'
             f'<rect x="352" y="302" width="232" height="38" rx="9" fill="{t["card"]}" stroke="{t["edge"]}"/>'
             f'<text x="364" y="318" {SANS} font-size="12.5" font-weight="500" fill="{t["title"]}">One grid cell per station</text>'
             f'<text x="364" y="333" {SANS} font-size="11" fill="{t["sub"]}">the cell the station sits in, raw values</text></g>')
    s.append(f'<circle class="halo" cx="600" cy="262" r="7" fill="{t["accent"]}" opacity=".35"/><circle cx="600" cy="262" r="3.5" fill="{t["accent"]}"/>')
    s.append(card(t, 676, 96, 320, 64, "Paired differences, with intervals", "block bootstrap over days, 95 percent", 0.6, accent=True))
    s.append(card(t, 676, 178, 320, 64, "By lead time, hour and season", "where and when a forecast goes wrong", 0.7))
    s.append(card(t, 676, 260, 320, 64, "Dashboard and summary page", "every number with its sample size", 0.8))
    s.append(f'<g class="n" style="animation-delay:.9s"><rect x="44" y="424" width="952" height="62" rx="14" fill="{t["card"]}" stroke="{t["edge"]}"/>'
             f'<text x="60" y="451" {SANS} font-size="15" font-weight="500" fill="{t["title"]}">Case replays</text>'
             f'<text x="60" y="473" {SANS} font-size="12.5" fill="{t["sub"]}">one command replays an event through the same scorer: a record monsoon surge, a squall line, an 18-day dry spell</text></g>')
    s.append("</svg>")
    return "".join(s)


def result(theme: str) -> str:
    t = THEMES[theme]
    res = pd.read_parquet(TABLES / "results" / "results.parquet")
    d = res[(res.qc == "flags_removed") & (res.station == "all") & (res.hour_local == "all") & (res.regime == "all")
            & (res.lead_kind == "day") & (res.lead == 1) & (res.metric == "mae") & (res.against == "climatology")]
    names = {"gfs_global": ("GFS", t["gfs"]), "ecmwf_ifs025": ("ECMWF IFS 0.25°", t["ifs"]),
             "ecmwf_aifs025_single": ("ECMWF AIFS 0.25°", t["other"]), "ecmwf_ifs": ("ECMWF IFS 9 km", t["other"])}
    groups = [("rain_hourly", "Hourly rain, mm"), ("temperature_2m", "Temperature, °C"), ("wind_speed_10m", "Wind speed, m/s")]
    rows = [(title, names[r.source], r.value, r.low, r.high) for v, title in groups for r in d[d.variable == v].itertuples() if r.source in names]
    W, left, right, rh, top = 1040, 250, 60, 27, 96
    H = top + len(rows) * rh + len(groups) * 30 + 56
    lo = min(min(r[3] for r in rows), 0) - 0.05
    hi = max(r[4] for r in rows) + 0.05
    X = lambda v: left + (v - lo) / (hi - lo) * (W - left - right)  # noqa: E731
    s = [frame(t, W, H, "Difference in mean absolute error against climatology, one day ahead, with 95 percent intervals. Rain forecasts are slightly better than climatology; temperature and wind forecasts are worse."),
         stage(t, 44, "ERROR AGAINST CLIMATOLOGY · ONE DAY AHEAD · 95 PERCENT INTERVALS"),
         f'<text x="{X(0) - 12}" y="78" text-anchor="end" {SANS} font-size="12.5" fill="{t["sub"]}">← better than climatology</text>',
         f'<text x="{X(0) + 12}" y="78" {SANS} font-size="12.5" fill="{t["sub"]}">worse than climatology →</text>']
    v = -0.2
    while v <= hi:
        if v >= lo:
            s.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{top - 6}" y2="{H - 46}" stroke="{t["wire"]}" stroke-width="1"/>'
                     f'<text x="{X(v):.1f}" y="{H - 26}" text-anchor="middle" {SANS} font-size="11.5" fill="{t["sub"]}">{v:+.1f}</text>')
        v = round(v + 0.2, 1)
    s.append(f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="{top - 6}" y2="{H - 46}" stroke="{t["zero"]}" stroke-width="1.2"/>')
    y, last = top - 6, None
    for i, (title, (name, colour), val, a, b) in enumerate(rows):
        if title != last:
            y += 30
            s.append(f'<text x="44" y="{y - 8}" {SANS} font-size="14" font-weight="500" fill="{t["title"]}">{title}</text>')
            last = title
        cy = y + rh / 2
        s.append(f'<text x="{left - 14}" y="{cy + 4}" text-anchor="end" {SANS} font-size="12.5" fill="{t["sub"]}">{name}</text>'
                 f'<line class="bar" style="animation-delay:{0.08 * i:.2f}s" x1="{X(a):.1f}" x2="{X(b):.1f}" y1="{cy}" y2="{cy}" stroke="{colour}" stroke-width="4" stroke-linecap="round"/>'
                 f'<circle class="dot" style="animation-delay:{0.08 * i + 0.5:.2f}s" cx="{X(val):.1f}" cy="{cy}" r="5.5" fill="{colour}" stroke="{t["bg"]}" stroke-width="2"/>')
        y += rh
    s.append("</svg>")
    return "".join(s)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for theme in THEMES:
        (OUT / f"pipeline-{theme}.svg").write_text(pipeline(theme), encoding="utf-8")
        (OUT / f"result-{theme}.svg").write_text(result(theme), encoding="utf-8")
    print("wrote", sorted(p.name for p in OUT.glob("*.svg")))


if __name__ == "__main__":
    main()
