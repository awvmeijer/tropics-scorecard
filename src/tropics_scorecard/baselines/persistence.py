"""Persistence: tomorrow will be like the latest comparable observation.

mode "daily" (default):
    lead day N: the observation at the same station 24N hours before the valid time.
    lead hour h: the observation at the same hour of day on the latest day before the run,
    24 * ceil(h / 24) hours before the valid time.
mode "issue":
    lead hour h: the observation at the run time, h hours before the valid time.
    lead day N: the observation 24N hours before the valid time (same as daily).

Only observations that pass the same quality control as the reference are used, so a
missing or flagged predictor hour gives no forecast. See docs/verification_protocol.md 5.1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..match import observations
from ..sources import ForecastSource, check_cases


class Persistence(ForecastSource):
    def __init__(self, cfg: dict, mode: str = "daily", drop_flagged: bool = True):
        if mode not in ("daily", "issue"):
            raise ValueError(mode)
        self.cfg, self.mode, self.drop_flagged = cfg, mode, drop_flagged
        self.name = "persistence" if mode == "daily" else "persistence_issue"
        self.day_hours = int(cfg["baselines"]["persistence_day_offset_hours"])
        self._obs: dict[str, pd.Series] = {}

    def offset_hours(self, cases: pd.DataFrame) -> pd.Series:
        lead = cases["lead"].astype(int)
        day = cases["lead_kind"] == "day"
        if self.mode == "issue":
            hours = np.where(day, lead * self.day_hours, lead)
        else:
            hours = np.where(day, lead * self.day_hours, 24 * np.ceil(lead / 24).astype(int))
        return pd.Series(hours, index=cases.index)

    def _series(self, variable: str, start, end) -> pd.Series:
        key = f"{variable}|{start}|{end}"
        if key not in self._obs:
            obs = observations.load(variable, start, end, drop_flagged=self.drop_flagged)
            self._obs[key] = obs.set_index(["station_key", "time_utc"])["value"]
        return self._obs[key]

    def predict(self, variable: str, cases: pd.DataFrame) -> pd.Series:
        check_cases(cases)
        if cases.empty:
            return pd.Series(dtype=float, index=cases.index)
        when = cases["valid_time"] - pd.to_timedelta(self.offset_hours(cases), unit="h")
        obs = self._series(variable, when.min(), when.max())
        idx = pd.MultiIndex.from_arrays([cases["station_key"], when])
        return pd.Series(obs.reindex(idx).to_numpy(), index=cases.index, dtype=float)
