"""Climatology: what usually happens at this station, in this month, at this local hour.

Built from config period.climatology_years, which ends before the test period starts.
- Continuous variables: the mean.
- Events (rain above a threshold): the observed frequency, used as the probability, and
  "yes" when the frequency reaches baselines.climatology_event_probability_cut.
- A station with fewer than baselines.climatology_min_years distinct years of history uses
  the network value for that month and hour instead, and is listed in `fallback_stations`.

Lead time does not matter to climatology. See docs/verification_protocol.md 5.2.
"""
from __future__ import annotations

import pandas as pd

from ..match import observations
from ..sources import ForecastSource, check_cases


class Climatology(ForecastSource):
    name = "climatology"
    deterministic = False

    def __init__(self, cfg: dict, reference: pd.DataFrame | None = None):
        self.cfg = cfg
        self.min_years = int(cfg["baselines"]["climatology_min_years"])
        self.cut = float(cfg["baselines"]["climatology_event_probability_cut"])
        self.tz = cfg["region"]["local_timezone"]
        self._reference = reference  # tests can pass a table instead of reading the store
        self._tables: dict[str, tuple] = {}
        self._histories: dict[str, pd.DataFrame] = {}
        self.fallback_stations: dict[str, list[str]] = {}

    def _history(self, variable: str) -> pd.DataFrame:
        if self._reference is not None:
            return self._reference
        years = self.cfg["period"]["climatology_years"]
        return observations.load(variable, years["start"], f"{years['end']} 23:59")

    def _keys(self, times: pd.Series) -> tuple[pd.Series, pd.Series]:
        local = times.dt.tz_convert(self.tz)
        return local.dt.month, local.dt.hour

    def table(self, variable: str, thresholds: tuple[float, ...] = ()) -> tuple[pd.DataFrame, pd.DataFrame]:
        """(per station, network) tables keyed by month and local hour, with mean, n, years
        and p_<threshold> for every rain threshold in config plus any asked for here.
        The history is read once per variable; a new threshold rebuilds from that copy."""
        wanted = set(thresholds)
        if variable == "rain_hourly":
            wanted |= {float(t) for t in self.cfg.get("rain_thresholds_mm_per_hour") or []}
        cached = self._tables.get(variable)
        if cached is not None and wanted <= cached[2]:
            return cached[0], cached[1]
        if variable not in self._histories:
            h = self._history(variable).copy()
            h["month"], h["hour"] = self._keys(h["time_utc"])
            h["year"] = h["time_utc"].dt.tz_convert(self.tz).dt.year
            self._histories[variable] = h
        h = self._histories[variable]
        cols = {}
        for t in sorted(wanted):
            h[f"p_{t}"] = (h["value"] >= t).astype(float)
            cols[f"p_{t}"] = (f"p_{t}", "mean")
        agg = dict(mean=("value", "mean"), n=("value", "size"), **cols)
        st = h.groupby(["station_key", "month", "hour"]).agg(**agg).reset_index()
        years = h.groupby("station_key")["year"].nunique()
        net = h.groupby(["month", "hour"]).agg(**agg).reset_index()
        st["years"] = st["station_key"].map(years)
        self.fallback_stations[variable] = sorted(years[years < self.min_years].index)
        self._tables[variable] = (st, net, wanted)
        return st, net

    def _lookup(self, variable: str, cases: pd.DataFrame, column: str, thresholds=()) -> pd.Series:
        check_cases(cases)
        st, net = self.table(variable, tuple(thresholds))
        month, hour = self._keys(cases["valid_time"])
        q = pd.DataFrame({"station_key": cases["station_key"].to_numpy(), "month": month.to_numpy(),
                          "hour": hour.to_numpy()}, index=cases.index)
        a = q.merge(st[["station_key", "month", "hour", "years", column]], on=["station_key", "month", "hour"], how="left")
        b = q.merge(net[["month", "hour", column]], on=["month", "hour"], how="left")
        use_net = a["years"].isna() | (a["years"] < self.min_years)
        out = a[column].where(~use_net, b[column])
        return pd.Series(out.to_numpy(), index=cases.index, dtype=float)

    def predict(self, variable: str, cases: pd.DataFrame) -> pd.Series:
        return self._lookup(variable, cases, "mean")

    def probability(self, variable: str, cases: pd.DataFrame, threshold: float) -> pd.Series:
        return self._lookup(variable, cases, f"p_{float(threshold)}", (float(threshold),))

    def says_yes(self, variable: str, cases: pd.DataFrame, threshold: float) -> pd.Series:
        p = self.probability(variable, cases, threshold)
        return (p >= self.cut).where(p.notna())
