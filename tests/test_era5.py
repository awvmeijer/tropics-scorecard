"""Plumbing for ERA5 as a source and as a judge, on a small table in memory."""
import pandas as pd

from tropics_scorecard.sources.era5 import Era5


def era5_with(values):
    e = Era5({})
    e.__dict__["cells"] = pd.DataFrame({"station_key": ["a", "b"], "cell_lat": [1.25, 1.25], "cell_lon": [103.75, 104.0]})
    times = pd.to_datetime(["2024-03-01T00:00Z", "2024-03-01T01:00Z"])
    e._tables["temperature_2m"] = pd.DataFrame({
        "cell_lat": [1.25, 1.25, 1.25, 1.25], "cell_lon": [103.75, 103.75, 104.0, 104.0],
        "valid_time": list(times) * 2, "value": values})
    return e, times


def test_predict_reads_the_station_cell_whatever_the_lead():
    e, times = era5_with([27.0, 28.0, 26.0, 25.0])
    cases = pd.DataFrame({"station_key": ["b", "a", "a", "c"], "valid_time": [times[0], times[1], times[1], times[0]],
                          "lead_kind": "day", "lead": [1, 1, 7, 1]}, index=[10, 11, 12, 13])
    out = e.predict("temperature_2m", cases)
    assert list(out.index) == [10, 11, 12, 13]
    assert out.tolist()[:3] == [26.0, 28.0, 28.0]
    assert pd.isna(out.loc[13])  # a station without an ERA5 cell gets no value


def test_history_is_shaped_like_the_observation_table():
    e, times = era5_with([27.0, 28.0, 26.0, 25.0])
    h = e.history("temperature_2m", "2024-03-01", "2024-03-01 00:30")
    assert list(h.columns) == ["station_key", "time_utc", "value"]
    assert sorted(zip(h.station_key, h.value)) == [("a", 27.0), ("b", 26.0)]
