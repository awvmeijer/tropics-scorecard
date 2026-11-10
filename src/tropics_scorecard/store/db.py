"""DuckDB over the Parquet tables. Views only; the Parquet files are the store.

    from tropics_scorecard.store.db import connect
    con = connect()
    con.sql("select station_id, count(*) from isd_obs where preferred group by 1")
"""
from __future__ import annotations

import duckdb

from ..paths import TABLES

VIEWS = {
    "isd_obs": "isd/obs_*.parquet",
    "igra_soundings": "igra/soundings.parquet",
    "igra_levels": "igra/levels.parquet",
    "dgs_readings": "datagovsg/readings_*.parquet",
    "dgs_stations": "datagovsg/stations_*.parquet",
    "qc_flags": "qc/flags_*.parquet",
}


def connect(database: str = ":memory:") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database)
    for name, pattern in VIEWS.items():
        files = list(TABLES.glob(pattern))
        if files:
            con.sql(f"create or replace view {name} as select * from read_parquet('{TABLES / pattern}', union_by_name=true)")
    return con
