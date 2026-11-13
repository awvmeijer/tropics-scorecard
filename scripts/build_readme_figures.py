"""Draw the README figures as animated SVG: the pipeline schematic and the headline result.

GitHub shows SVG images with their CSS animations. Both figures are plain files with no
script. The result figure reads the scored results, so rerun this after scoring.
    uv run python scripts/build_readme_figures.py
"""
from __future__ import annotations

import pandas as pd

from tropics_scorecard.paths import ROOT, TABLES

OUT = ROOT / "docs" / "assets"
INK, INK2, RULE, PAPER = "#262626", "#555555", "#e4e4e4", "#ffffff"
GFS, IFS, PERS, CLIM = "#2a78d6", "#eb6834", "#1baf7a", "#b07a00"
FONT = "font-family=\"'JetBrains Mono', ui-monospace, Menlo, monospace\""
SANS = "font-family=\"'Inter Tight', system-ui, -apple-system, 'Segoe UI', sans-serif\""


def box(x, y, w, h, title, lines, delay):
    body = "".join(f'<text x="{x + 14}" y="{y + 46 + 17 * i}" {SANS} font-size="12.5" fill="{INK2}">{t}</text>' for i, t in enumerate(lines))
    return (f'<g class="node" style="animation-delay:{delay}s"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}" stroke="{INK}" stroke-width="1.2"/>'
            f'<text x="{x + 14}" y="{y + 24}" {FONT} font-size="11" letter-spacing="1.1" fill="{INK}">{title.upper()}</text>{body}</g>')


def flow(d, colour, delay, dots=3):
    out = f'<path d="{d}" fill="none" stroke="{RULE}" stroke-width="2"/><path class="wire" d="{d}" fill="none" stroke="{colour}" stroke-width="2" stroke-dasharray="6 8"/>'
    for i in range(dots):
        out += (f'<circle r="4" fill="{colour}"><animateMotion dur="3.2s" begin="{delay + i * 3.2 / dots:.2f}s" repeatCount="indefinite" path="{d}"/></circle>')
    return out


def pipeline() -> str:
    W, H = 980, 430
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="How Tropics Scorecard works: observations and forecasts are matched, scored against baselines, and published with intervals">',
         '<style>.node{opacity:0;animation:in .6s ease-out forwards}@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}'
         '.wire{animation:dash 1.2s linear infinite}@keyframes dash{to{stroke-dashoffset:-14}}'
         '@media (prefers-reduced-motion: reduce){.node{animation:none;opacity:1}.wire{animation:none}}</style>',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>']
    # wires first, so boxes sit on top
    s.append(flow("M250,95 C300,95 300,150 350,150", INK, 0.0))
    s.append(flow("M250,335 C300,335 300,280 350,280", IFS, 0.4))
    s.append(flow("M550,150 C600,150 600,215 650,215", INK, 0.8))
    s.append(flow("M550,280 C600,280 600,215 650,215", IFS, 1.2))
    s.append(flow("M450,190 L450,240", CLIM, 0.2, dots=1))
    s.append(flow("M850,215 L880,215", INK, 1.6, dots=1))
    s.append(box(30, 40, 220, 110, "Instruments", ["Rain gauges, 5 minutes", "Weather stations, 1 minute", "Airports and balloon soundings"], 0.0))
    s.append(box(30, 280, 220, 110, "Forecast archive", ["GFS and ECMWF", "1 to 7 days ahead", "One grid cell per station"], 0.15))
    s.append(box(350, 100, 200, 90, "Quality control", ["Every flag logged", "Hours kept only when complete"], 0.3))
    s.append(box(350, 240, 200, 90, "Baselines", ["Persistence, climatology", "Scored exactly like a model"], 0.45))
    s.append(box(650, 160, 200, 110, "Scorer", ["Same cases for everyone", "Paired differences", "Block bootstrap over days"], 0.6))
    s.append(f'<g class="node" style="animation-delay:.8s"><rect x="880" y="170" width="78" height="90" rx="6" fill="{INK}"/>'
             f'<text x="919" y="204" text-anchor="middle" {FONT} font-size="11" letter-spacing="1" fill="{PAPER}">SCORE</text>'
             f'<text x="919" y="226" text-anchor="middle" {FONT} font-size="11" fill="{PAPER}">with its</text>'
             f'<text x="919" y="243" text-anchor="middle" {FONT} font-size="11" fill="{PAPER}">interval</text></g>')
    s.append(f'<text x="30" y="24" {FONT} font-size="11" letter-spacing="1.1" fill="{INK2}">WHAT WAS MEASURED</text>')
    s.append(f'<text x="30" y="264" {FONT} font-size="11" letter-spacing="1.1" fill="{INK2}">WHAT WAS FORECAST</text>')
    s.append(f'<text x="350" y="372" {SANS} font-size="12.5" fill="{INK2}">The rules for matching and scoring were written down before any forecast was scored.</text>')
    s.append("</svg>")
    return "".join(s)


def result() -> str:
    res = pd.read_parquet(TABLES / "results" / "results.parquet")
    d = res[(res.qc == "flags_removed") & (res.station == "all") & (res.hour_local == "all") & (res.regime == "all")
            & (res.lead_kind == "day") & (res.lead == 1) & (res.metric == "mae") & (res.against == "climatology")]
    names = {"gfs_global": ("GFS", GFS), "ecmwf_ifs025": ("ECMWF IFS 0.25°", IFS), "ecmwf_aifs025_single": ("ECMWF AIFS 0.25°", INK2), "ecmwf_ifs": ("ECMWF IFS 9 km", INK2)}
    groups = [("rain_hourly", "Hourly rain, mm"), ("temperature_2m", "Temperature, °C"), ("wind_speed_10m", "Wind speed, m/s")]
    rows = [(title, names[r.source], r.value, r.low, r.high) for v, title in groups for r in d[d.variable == v].itertuples() if r.source in names]
    W, left, right, rh = 980, 200, 30, 26
    H = 70 + len(rows) * rh + len(groups) * 26 + 40
    lo = min(min(r[3] for r in rows), 0) - 0.05
    hi = max(r[4] for r in rows) + 0.05
    X = lambda v: left + (v - lo) / (hi - lo) * (W - left - right)  # noqa: E731
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Difference in mean absolute error against climatology, one day ahead, with 95 percent intervals">',
         '<style>.bar{transform-box:fill-box;transform-origin:center;animation:grow .9s ease-out both}@keyframes grow{from{transform:scaleX(0)}}'
         '.dot{animation:pop .4s ease-out both}@keyframes pop{from{opacity:0}}@media (prefers-reduced-motion: reduce){.bar,.dot{animation:none}}</style>',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<text x="0" y="18" {FONT} font-size="11" letter-spacing="1.1" fill="{INK2}">ERROR AGAINST CLIMATOLOGY, ONE DAY AHEAD · 95 PERCENT INTERVALS</text>',
         f'<text x="{X(0) - 10}" y="44" text-anchor="end" {SANS} font-size="12.5" fill="{INK2}">← better than climatology</text>',
         f'<text x="{X(0) + 10}" y="44" {SANS} font-size="12.5" fill="{INK2}">worse than climatology →</text>']
    t = -0.2
    while t <= hi:
        if t >= lo:
            s.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="54" y2="{H - 30}" stroke="{RULE}"/><text x="{X(t):.1f}" y="{H - 12}" text-anchor="middle" {FONT} font-size="11" fill="{INK2}">{t:+.1f}</text>')
        t = round(t + 0.2, 1)
    s.append(f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="54" y2="{H - 30}" stroke="{INK}"/>')
    y, last = 54, None
    for i, (title, (name, colour), v, a, b) in enumerate(rows):
        if title != last:
            y += 26
            s.append(f'<text x="0" y="{y - 7}" {SANS} font-size="13" font-weight="600" fill="{INK}">{title}</text>')
            last = title
        cy = y + rh / 2
        s.append(f'<text x="{left - 12}" y="{cy + 4}" text-anchor="end" {SANS} font-size="12.5" fill="{INK}">{name}</text>'
                 f'<line class="bar" style="animation-delay:{0.08 * i:.2f}s" x1="{X(a):.1f}" x2="{X(b):.1f}" y1="{cy}" y2="{cy}" stroke="{colour}" stroke-width="4" stroke-linecap="round"/>'
                 f'<circle class="dot" style="animation-delay:{0.08 * i + 0.5:.2f}s" cx="{X(v):.1f}" cy="{cy}" r="5.5" fill="{colour}" stroke="{PAPER}" stroke-width="2"/>')
        y += rh
    s.append("</svg>")
    return "".join(s)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pipeline.svg").write_text(pipeline(), encoding="utf-8")
    (OUT / "result.svg").write_text(result(), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
