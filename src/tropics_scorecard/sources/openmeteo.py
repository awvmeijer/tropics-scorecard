"""Archived operational forecasts as a forecast source.

Each station is paired with one model grid cell by the cell rule (`land` or `nearest`,
see docs/verification_protocol.md 3.1), looked up in data/tables/openmeteo/grid.parquet.
Lead kind "day" reads the Previous Runs table; lead kind "hour" reads the Single Runs table.
"""
from __future__ import annotations

from functools import cached_property

import pandas as pd

from ..paths import TABLES
from ..sources import ForecastSource, check_cases

TABLE = TABLES / "openmeteo"


class OpenMeteoModel(ForecastSource):
    def __init__(self, model: str, cfg: dict, cell_rule: str):
        self.model, self.cfg, self.cell_rule = model, cfg, cell_rule
        self.name = model if cell_rule == cfg["matching"]["cell_rule"] else f"{model}@{cell_rule}"
        self._tables: dict[tuple[str, str], pd.DataFrame] = {}

    @cached_property
    def cells(self) -> pd.DataFrame:
        g = pd.read_parquet(TABLE / "grid.parquet")
        g = g[(g["model"] == self.model) & (g["cell_rule"] == self.cell_rule)]
        if g.empty:
            raise LookupError(f"no grid cells for {self.model} under rule {self.cell_rule}: run ingest.openmeteo grid")
        # grid.parquet and the forecast tables hold coordinates rounded once to CELL_DECIMALS.
        return g[["station_key", "cell_lat", "cell_lon"]].drop_duplicates("station_key")

    def _table(self, kind: str, variable: str) -> pd.DataFrame:
        if (kind, variable) not in self._tables:
            path = TABLE / f"{'previous' if kind == 'day' else 'single'}_{self.model}.parquet"
            if not path.exists():
                raise LookupError(f"{path.name} not built: run store.openmeteo")
            lead = "lead_day" if kind == "day" else "lead_hours"
            t = pd.read_parquet(path, columns=["cell_lat", "cell_lon", "valid_time", "variable", lead, "value"],
                                filters=[("variable", "==", variable)])
            t = t.rename(columns={lead: "lead"}).drop(columns="variable")
            self._tables[(kind, variable)] = t
        return self._tables[(kind, variable)]

    def predict(self, variable: str, cases: pd.DataFrame) -> pd.Series:
        check_cases(cases)
        out = pd.Series(float("nan"), index=cases.index)
        for kind, part in cases.groupby("lead_kind"):
            t = self._table(kind, variable)
            q = part[["station_key", "valid_time", "lead"]].reset_index().merge(self.cells, on="station_key", how="left")
            q = q.merge(t, on=["cell_lat", "cell_lon", "valid_time", "lead"], how="left")
            out.loc[q["index"].to_numpy()] = q["value"].to_numpy()
        return out
