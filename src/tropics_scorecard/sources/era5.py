"""ERA5 reanalysis, two ways.

As a forecast source: the reanalysis value for the station's ERA5 cell at the valid time,
whatever the lead time, so ERA5 can be scored against the stations like any model. It is
not a forecast: observations up to that hour went into it.

As a judge: `reference` and `history` give tables shaped like match.observations, with the
ERA5 value of each station's cell in place of the station reading, so the same forecasts can
be scored against ERA5 instead of the instruments.

Built by `store` from the responses cached by ingest.era5. Times are UTC; rain is the total
of the hour ending at valid_time; wind in metres per second.
"""
from __future__ import annotations

import gzip
import json
from functools import cached_property

import pandas as pd

from ..ingest.era5 import FOLDER, GRID
from ..ingest.openmeteo import CELL_DECIMALS, VARIABLES
from ..paths import TABLES
from . import ForecastSource, check_cases

TABLE = TABLES / "openmeteo" / "era5.parquet"
OURS = {v: k for k, v in VARIABLES.items()}


def store() -> pd.DataFrame:
    """Every cached ERA5 response as one table: cell_lat, cell_lon, valid_time, variable, value."""
    frames = []
    for path in sorted((FOLDER / "cells").glob("*/*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            body = json.load(fh)
        hourly = body.get("hourly") or {}
        times = pd.to_datetime(hourly.get("time") or [], utc=True)
        for key, values in hourly.items():
            if key in OURS:
                frames.append(pd.DataFrame({"cell_lat": round(float(body["latitude"]), CELL_DECIMALS),
                                            "cell_lon": round(float(body["longitude"]), CELL_DECIMALS),
                                            "valid_time": times, "variable": OURS[key],
                                            "value": pd.to_numeric(pd.Series(values), errors="coerce")}))
    df = pd.concat(frames, ignore_index=True).dropna(subset=["value"])
    df = df.drop_duplicates(["cell_lat", "cell_lon", "valid_time", "variable"])
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(TABLE, index=False)
    return df


class Era5(ForecastSource):
    name = "era5"
    lead_kinds = ("day", "hour")

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._tables: dict[str, pd.DataFrame] = {}

    @cached_property
    def cells(self) -> pd.DataFrame:
        if not GRID.exists():
            raise LookupError("no ERA5 grid: run ingest.era5 grid")
        return pd.read_parquet(GRID)[["station_key", "cell_lat", "cell_lon"]].drop_duplicates("station_key")

    def table(self, variable: str) -> pd.DataFrame:
        if variable not in self._tables:
            if not TABLE.exists():
                raise LookupError("era5.parquet not built: run sources.era5")
            t = pd.read_parquet(TABLE, filters=[("variable", "==", variable)]).drop(columns="variable")
            self._tables[variable] = t
        return self._tables[variable]

    def at_stations(self, variable: str, frame: pd.DataFrame, time_col: str) -> pd.Series:
        """ERA5 for each row's station cell and time, aligned to frame's index."""
        q = frame[["station_key", time_col]].reset_index().merge(self.cells, on="station_key", how="left")
        q = q.merge(self.table(variable).rename(columns={"valid_time": time_col}),
                    on=["cell_lat", "cell_lon", time_col], how="left")
        return pd.Series(q["value"].to_numpy(), index=q["index"].to_numpy()).reindex(frame.index)

    def predict(self, variable: str, cases: pd.DataFrame) -> pd.Series:
        check_cases(cases)
        return self.at_stations(variable, cases, "valid_time")

    def history(self, variable: str, start, end) -> pd.DataFrame:
        """ERA5 at every station's cell, shaped like match.observations.load: station_key,
        time_utc, value. Used to build an ERA5 climatology for ERA5 as the judge."""
        t = self.table(variable)
        t = t[(t["valid_time"] >= pd.Timestamp(start, tz="UTC")) & (t["valid_time"] <= pd.Timestamp(end, tz="UTC"))]
        h = self.cells.merge(t, on=["cell_lat", "cell_lon"])
        return h.rename(columns={"valid_time": "time_utc"})[["station_key", "time_utc", "value"]].reset_index(drop=True)


if __name__ == "__main__":
    d = store()
    print(f"era5.parquet: {len(d)} rows, {d.groupby(['cell_lat', 'cell_lon']).ngroups} cells, "
          f"{d.valid_time.min()} to {d.valid_time.max()}")
