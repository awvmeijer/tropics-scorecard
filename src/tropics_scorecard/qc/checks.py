"""Quality control checks on tidy observation tables.

Each check takes a DataFrame with columns station_id, time_utc, value (sorted or not)
and returns a flags DataFrame with columns:
    station_id, time_utc, check, detail
A row in the flags table means the reading at that station and time failed that check.
"""
from __future__ import annotations

import pandas as pd

FLAG_COLUMNS = ["station_id", "time_utc", "check", "detail"]


class BlockedByStub(RuntimeError):
    """A metric function this check needs is still a stub."""


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=FLAG_COLUMNS)


def _flags(df: pd.DataFrame, check: str, detail) -> pd.DataFrame:
    if df.empty:
        return _empty()
    out = df[["station_id", "time_utc"]].copy()
    out["check"] = check
    out["detail"] = detail if isinstance(detail, str) else detail.astype(str).values
    return out.reset_index(drop=True)


def duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Same station and time more than once. Flags every copy when the values disagree,
    and the extra copies when they agree."""
    key = ["station_id", "time_utc"]
    dup = df[df.duplicated(key, keep=False)]
    if dup.empty:
        return _empty()
    nvals = dup.groupby(key)["value"].transform("nunique")
    conflicting = dup[nvals > 1]
    repeated = dup[(nvals <= 1) & dup.duplicated(key, keep="first")]
    return pd.concat([
        _flags(conflicting, "duplicate_conflict", "same time, different values"),
        _flags(repeated, "duplicate_repeat", "same time, same value"),
    ], ignore_index=True)


def out_of_range(df: pd.DataFrame, lo: float, hi: float) -> pd.DataFrame:
    bad = df[(df["value"] < lo) | (df["value"] > hi)]
    return _flags(bad, "range", bad["value"].map(lambda v: f"{v} outside [{lo}, {hi}]"))


def spikes(df: pd.DataFrame, jump: float, max_gap_minutes: float) -> pd.DataFrame:
    """A reading that differs from both neighbours by more than `jump`, in the same
    direction, with both neighbours within max_gap_minutes."""
    d = df.dropna(subset=["value"]).sort_values(["station_id", "time_utc"])
    g = d.groupby("station_id")
    prev_v, next_v = g["value"].shift(1), g["value"].shift(-1)
    gap = pd.Timedelta(minutes=max_gap_minutes)
    prev_ok = (d["time_utc"] - g["time_utc"].shift(1)) <= gap
    next_ok = (g["time_utc"].shift(-1) - d["time_utc"]) <= gap
    up = (d["value"] - prev_v > jump) & (d["value"] - next_v > jump)
    down = (prev_v - d["value"] > jump) & (next_v - d["value"] > jump)
    bad = d[(up | down) & prev_ok & next_ok]
    detail = bad["value"].astype(str) + " vs neighbours " + prev_v[bad.index].astype(str) + ", " + next_v[bad.index].astype(str)
    return _flags(bad, "spike", detail)


def flatlines(df: pd.DataFrame, minutes: float, ignore_value: float | None = None,
              max_gap_minutes: float = 15) -> pd.DataFrame:
    """Runs of an identical value lasting at least `minutes`. Every reading in the run is
    flagged. A gap longer than max_gap_minutes breaks a run. `ignore_value` (for example
    zero rain) never counts as a flatline."""
    d = df.dropna(subset=["value"]).sort_values(["station_id", "time_utc"]).copy()
    if d.empty:
        return _empty()
    g = d.groupby("station_id")
    new_run = (d["value"] != g["value"].shift(1)) | ((d["time_utc"] - g["time_utc"].shift(1)) > pd.Timedelta(minutes=max_gap_minutes))
    d["run"] = new_run.cumsum()
    span = d.groupby("run")["time_utc"].agg(["min", "max"])
    length = (span["max"] - span["min"]) / pd.Timedelta(minutes=1)
    long_runs = length[length >= minutes].index
    bad = d[d["run"].isin(long_runs)]
    if ignore_value is not None:
        bad = bad[bad["value"] != ignore_value]
    detail = bad["run"].map(lambda r: f"same value for {length[r]:.0f} min")
    return _flags(bad, "flatline", detail)


def timezone_check(df: pd.DataFrame, local_tz: str, lo_hour: int, hi_hour: int) -> pd.DataFrame:
    """For each station and month, the local hour of the mean daily maximum temperature
    should fall in [lo_hour, hi_hour]. A shifted clock moves it. Flags are per station-month
    and carry the first timestamp of that month."""
    d = df.dropna(subset=["value"]).copy()
    if d.empty:
        return _empty()
    local = d["time_utc"].dt.tz_convert(local_tz)
    d["month"] = local.dt.strftime("%Y-%m")
    d["hour"] = local.dt.hour
    prof = d.groupby(["station_id", "month", "hour"])["value"].mean().reset_index()
    counts = prof.groupby(["station_id", "month"])["hour"].transform("size")
    prof = prof[counts >= 20]
    if prof.empty:
        return _empty()
    peak = prof.loc[prof.groupby(["station_id", "month"])["value"].idxmax()]
    bad = peak[(peak["hour"] < lo_hour) | (peak["hour"] > hi_hour)]
    if bad.empty:
        return _empty()
    first = d.groupby(["station_id", "month"])["time_utc"].min()
    rows = bad.assign(time_utc=[first[(s, m)] for s, m in zip(bad["station_id"], bad["month"])])
    return _flags(rows, "timezone", rows.apply(lambda r: f"{r['month']}: warmest local hour {r['hour']}", axis=1))


def stuck_dry(hourly: pd.DataFrame, stations: pd.DataFrame, radius_km: float,
              min_neighbours: int, neighbour_median_mm: float) -> pd.DataFrame:
    """A gauge with an hourly total of zero while the median of gauges within radius_km
    is at least neighbour_median_mm.

    hourly: station_id, time_utc (hour), value (mm in the hour).
    stations: station_id, latitude, longitude.
    Uses metrics.geo.haversine_km for distances.
    """
    from ..metrics.geo import haversine_km

    pts = stations.drop_duplicates("station_id").set_index("station_id")[["latitude", "longitude"]]
    try:
        neighbours = {}
        for a, pa in pts.iterrows():
            neighbours[a] = [b for b, pb in pts.iterrows()
                             if b != a and haversine_km(pa.latitude, pa.longitude, pb.latitude, pb.longitude) <= radius_km]
    except NotImplementedError as err:
        raise BlockedByStub(str(err)) from err
    wide = hourly.pivot_table(index="time_utc", columns="station_id", values="value")
    rows = []
    for station, near in neighbours.items():
        near = [n for n in near if n in wide.columns]
        if station not in wide.columns or len(near) < min_neighbours:
            continue
        med = wide[near].median(axis=1, skipna=True)
        nvalid = wide[near].notna().sum(axis=1)
        hit = (wide[station] == 0) & (med >= neighbour_median_mm) & (nvalid >= min_neighbours)
        for t in wide.index[hit]:
            rows.append({"station_id": station, "time_utc": t, "check": "stuck_dry",
                         "detail": f"0 mm while median of {int(nvalid[t])} neighbours is {med[t]:.1f} mm"})
    return pd.DataFrame(rows, columns=FLAG_COLUMNS)
