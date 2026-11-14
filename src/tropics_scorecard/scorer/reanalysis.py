"""The same forecasts, two judges: the stations, and the ERA5 reanalysis.

Added 14 November 2026 (protocol change log). Learned weather models such as GraphCast and
GenCast are trained on ERA5 and scored against it. This module asks two questions:

1. How close is ERA5 itself to the instruments? ERA5 is scored against the stations like any
   forecast, on the one-day-ahead cases, against station climatology, and its 6-hour rain
   extremes are tested like the models'.
2. Does the verdict on a forecast change with the judge? Each model's change in RMSE against
   climatology, at every lead day, is computed twice on the same station-hours: once with the
   station readings as the truth and station climatology as the reference, once with ERA5 at
   the station's cell as the truth and ERA5 climatology (same years, same station, month and
   local hour) as the reference.

Writes data/tables/results/reanalysis.parquet and reanalysis_extremes.parquet. Usage:
    python -m tropics_scorecard.scorer.reanalysis
"""
from __future__ import annotations

import sys

import pandas as pd

from ..baselines.climatology import Climatology
from ..paths import load_config
from ..sources.era5 import Era5
from . import core, summary

OUT = core.OUT


def era5_judged(cfg: dict, era5: Era5, base: str, lead: int) -> pd.DataFrame:
    """The station-truth cases for this lead, with ERA5 at each station's cell as the truth."""
    cases = core.cases_for(cfg, base, "day", lead)
    truth = era5.at_stations(base, cases, "valid_time")
    return cases.assign(observed=truth).dropna(subset=["observed"]).reset_index(drop=True)


def era5_climatology(cfg: dict, era5: Era5, base: str) -> Climatology:
    years = cfg["period"]["climatology_years"]
    return Climatology(cfg, reference=era5.history(base, str(years["start"]), f"{years['end']} 23:00"))


def table(cfg: dict) -> pd.DataFrame:
    era5 = Era5(cfg)
    names = summary._models(cfg)
    rows = []
    for variable in cfg["summary_scores"]["skill_variables"]:
        base = "rain_hourly" if variable == core.SIX_HOUR else variable
        clim_era5 = era5_climatology(cfg, era5, base)
        for lead in cfg["lead_times"]["days"]:
            stations = core.cases_for(cfg, base, "day", lead)
            got = summary.skill_rows(cfg, variable, lead, stations, "climatology",
                                     names + (["era5"] if lead == 1 else []), " [stations]", score="rmse")
            rows += [{**r, "judge": "stations"} for r in got]
            judged = era5_judged(cfg, era5, base, lead)
            got = summary.skill_rows(cfg, variable, lead, judged, clim_era5, names, " [era5]", score="rmse")
            rows += [{**r, "judge": "era5"} for r in got]
            # GFS against ECMWF IFS 0.25 directly, under each judge: does the order change?
            ifs = core.get_source("ecmwf_ifs025", cfg)
            for judge, c in (("stations", stations), ("era5", judged)):
                got = summary.skill_rows(cfg, variable, lead, c, ifs, ["gfs_global"], f" [{judge}, against IFS]", score="rmse")
                rows += [{**r, "judge": judge, "reference": "ecmwf_ifs025"} for r in got]
    t = pd.DataFrame(rows)
    t["reference"] = t["reference"].fillna("climatology") if "reference" in t else "climatology"
    return t


def bias(cfg: dict) -> pd.DataFrame:
    """ERA5's mean error against the stations, one-day-ahead cases, with the day-block interval."""
    era5 = Era5(cfg)
    fn = core.CONTINUOUS["bias"][0]
    rows = []
    for variable in cfg["summary_scores"]["skill_variables"]:
        base = "rain_hourly" if variable == core.SIX_HOUR else variable
        p = summary._pairs(cfg, era5, variable, core.cases_for(cfg, base, "day", 1))
        days, vals = core.daily_values(p, [], fn, ("forecast", "observed"))[()]
        ci = core.interval(vals, None, cfg)
        rows.append({"source": "era5", "variable": variable, "metric": "bias", "value": ci[0], "low": ci[1],
                     "high": ci[2], "n_pairs": len(p), "n_days": len(days)})
    return pd.DataFrame(rows)


def main(cfg: dict | None = None) -> int:
    cfg = cfg or load_config()
    core.check_ready(cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    t = table(cfg)
    t.to_parquet(OUT / "reanalysis.parquet", index=False)
    bias(cfg).to_parquet(OUT / "reanalysis_bias.parquet", index=False)
    summary.extremes_table(cfg, sources=["era5"], leads=[1]).to_parquet(OUT / "reanalysis_extremes.parquet", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
