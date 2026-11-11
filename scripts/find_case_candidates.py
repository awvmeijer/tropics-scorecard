"""List candidate case-study events from the gauge network, before any forecast is looked at.

Three kinds, from the reference table (complete, unflagged hours) in the test period:
- wet days: the highest network-mean daily rain (Singapore dates)
- intense hours: the most gauges at or above 20 mm in one hour
- dry spells: the longest runs of days with network-mean rain under 1 mm

The output is a shortlist for choosing cases together with public reports that fix their
dates. Writes exports/case_candidates.md. Usage:
    uv run python scripts/find_case_candidates.py
"""
from __future__ import annotations

from tropics_scorecard.match import observations
from tropics_scorecard.paths import ROOT, load_config

INTENSE_MM = 20.0
DRY_MM = 1.0


def main() -> None:
    cfg = load_config()
    per = cfg["period"]["day_level_lead_times"]
    d = observations.load("rain_hourly", per["start"], f"{per['end']} 23:00")
    tz = cfg["region"]["local_timezone"]
    d["date"] = d["time_utc"].dt.tz_convert(tz).dt.date
    d["local_hour"] = d["time_utc"].dt.tz_convert(tz).dt.hour
    station_day = d.groupby(["station_key", "date"]).agg(mm=("value", "sum"), hours=("value", "size")).reset_index()
    station_day = station_day[station_day["hours"] >= 22]  # nearly complete days only
    day = station_day.groupby("date").agg(network_mean_mm=("mm", "mean"), gauges=("mm", "size"),
                                          wettest_gauge_mm=("mm", "max")).reset_index()
    wet = day.sort_values("network_mean_mm", ascending=False).head(12)

    hours = d.groupby("time_utc").agg(gauges_20mm=("value", lambda v: int((v >= INTENSE_MM).sum())),
                                      max_mm=("value", "max"), gauges=("value", "size")).reset_index()
    hours["local"] = hours["time_utc"].dt.tz_convert(tz).dt.strftime("%Y-%m-%d %H:00")
    intense = hours.sort_values(["gauges_20mm", "max_mm"], ascending=False).head(12)

    day = day.sort_values("date").reset_index(drop=True)
    day["dry"] = day["network_mean_mm"] < DRY_MM
    runs, start = [], None
    for i, r in day.iterrows():
        if r["dry"] and start is None:
            start = i
        if (not r["dry"] or i == len(day) - 1) and start is not None:
            end = i if r["dry"] else i - 1
            runs.append((day.loc[start, "date"], day.loc[end, "date"], end - start + 1,
                         round(float(day.loc[start:end, "network_mean_mm"].sum()), 1)))
            start = None
    dry = sorted(runs, key=lambda x: -x[2])[:8]

    lines = ["# Case-study candidates", "",
             f"From the gauge reference, {d['time_utc'].min():%Y-%m-%d} to {d['time_utc'].max():%Y-%m-%d} (UTC), "
             "complete and unflagged hours only. No forecast was looked at. Dates are Singapore dates.", "",
             "## Wettest days (network mean)", "", "| Date | Network mean mm | Wettest gauge mm | Gauges |", "|---|---|---|---|"]
    lines += [f"| {r.date} | {r.network_mean_mm:.1f} | {r.wettest_gauge_mm:.1f} | {r.gauges} |" for r in wet.itertuples()]
    lines += ["", f"## Most widespread intense hours (gauges with {INTENSE_MM:.0f} mm or more)", "",
              "| Local hour | Gauges at 20 mm+ | Highest mm | Gauges reporting |", "|---|---|---|---|"]
    lines += [f"| {r.local} | {r.gauges_20mm} | {r.max_mm:.1f} | {r.gauges} |" for r in intense.itertuples()]
    lines += ["", f"## Longest dry spells (network mean under {DRY_MM:.0f} mm a day)", "",
              "| From | To | Days | Total network-mean mm |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {n} | {mm} |" for a, b, n, mm in dry]
    out = ROOT / "exports" / "case_candidates.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
