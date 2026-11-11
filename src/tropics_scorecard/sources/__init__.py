"""One interface for anything that produces forecasts.

A forecast source answers: for these stations, valid times and lead times, what did you say?

    cases = DataFrame(station_key, valid_time, lead_kind, lead)
        lead_kind "day": lead is N in "the run that was current N days earlier"
        lead_kind "hour": lead is hours from the run time to the valid time
    source.predict(variable, cases) -> Series of values aligned to cases (NaN = no forecast)
    source.probability(variable, cases, threshold) -> Series of event probabilities in [0, 1]

Persistence, climatology and each operational model implement it, so a new model plugs in
without touching the scorer. Deterministic sources give a probability of 0 or 1.
"""
from __future__ import annotations

import pandas as pd

CASE_COLUMNS = ["station_key", "valid_time", "lead_kind", "lead"]


class ForecastSource:
    name: str = "source"
    lead_kinds: tuple[str, ...] = ("day", "hour")

    def predict(self, variable: str, cases: pd.DataFrame) -> pd.Series:
        raise NotImplementedError

    def probability(self, variable: str, cases: pd.DataFrame, threshold: float) -> pd.Series:
        """Deterministic default: 1 when the value reaches the threshold, else 0."""
        v = self.predict(variable, cases)
        return (v >= threshold).astype(float).where(v.notna())

    def says_yes(self, variable: str, cases: pd.DataFrame, threshold: float) -> pd.Series:
        """The yes or no forecast used by the contingency table."""
        v = self.predict(variable, cases)
        return (v >= threshold).where(v.notna())


def get_source(name: str, cfg: dict, cell_rule: str | None = None) -> ForecastSource:
    from ..baselines.climatology import Climatology
    from ..baselines.persistence import Persistence
    from .openmeteo import OpenMeteoModel

    if name == "persistence":
        return Persistence(cfg)
    if name == "persistence_issue":
        return Persistence(cfg, mode="issue")
    if name == "climatology":
        return Climatology(cfg)
    return OpenMeteoModel(name, cfg, cell_rule or cfg["matching"]["cell_rule"])


def check_cases(cases: pd.DataFrame) -> None:
    missing = [c for c in CASE_COLUMNS if c not in cases.columns]
    if missing:
        raise ValueError(f"cases lack columns {missing}")
