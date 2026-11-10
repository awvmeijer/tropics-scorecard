import pandas as pd
import pytest

from tropics_scorecard.qc import checks


def frame(values, station="S1", start="2024-03-01 00:00", step_min=1):
    t = pd.date_range(start, periods=len(values), freq=f"{step_min}min", tz="UTC")
    return pd.DataFrame({"station_id": station, "time_utc": t, "value": values})


def test_range_flags_only_outside():
    f = checks.out_of_range(frame([17.9, 18.0, 40.0, 40.1]), 18, 40)
    assert list(f["check"]) == ["range", "range"]
    assert len(f) == 2


def test_spike_needs_both_neighbours_same_direction():
    f = checks.spikes(frame([27.0, 27.1, 31.0, 27.2, 27.0]), jump=3.0, max_gap_minutes=5)
    assert len(f) == 1 and f["time_utc"].iloc[0].minute == 2
    # a step change is not a spike
    assert checks.spikes(frame([27.0, 27.0, 23.0, 23.0]), jump=3.0, max_gap_minutes=5).empty


def test_spike_ignores_neighbours_beyond_gap():
    d = frame([27.0, 31.0, 27.0], step_min=10)
    assert checks.spikes(d, jump=3.0, max_gap_minutes=5).empty


def test_flatline_flags_whole_run_and_ignores_value():
    d = frame([25.0] * 130 + [25.3])
    f = checks.flatlines(d, minutes=120)
    assert len(f) == 130
    zeros = frame([0.0] * 200, step_min=5)
    assert checks.flatlines(zeros, minutes=60, ignore_value=0).empty


def test_flatline_broken_by_gap():
    a = frame([25.0] * 70)
    b = frame([25.0] * 70, start="2024-03-01 02:00")
    f = checks.flatlines(pd.concat([a, b]), minutes=120, max_gap_minutes=15)
    assert f.empty


def test_duplicates_conflict_and_repeat():
    d = pd.concat([frame([1.0, 2.0]), frame([1.0, 3.0])], ignore_index=True)
    f = checks.duplicates(d)
    assert sorted(f["check"]) == ["duplicate_conflict", "duplicate_conflict", "duplicate_repeat"]


def test_timezone_check_flags_shifted_clock():
    hours = pd.date_range("2024-03-01", "2024-03-31 23:00", freq="h", tz="UTC")
    local_hour = hours.tz_convert("Asia/Singapore").hour
    good = pd.DataFrame({"station_id": "S1", "time_utc": hours, "value": 30 - abs(local_hour - 14)})
    assert checks.timezone_check(good, "Asia/Singapore", 11, 17).empty
    shifted = good.assign(time_utc=good["time_utc"] + pd.Timedelta(hours=8), station_id="S2")
    f = checks.timezone_check(shifted, "Asia/Singapore", 11, 17)
    assert set(f["station_id"]) == {"S2"}


def test_stuck_dry_reports_blocked_stub_cleanly():
    hourly = pd.DataFrame({"station_id": ["A"], "time_utc": [pd.Timestamp("2024-03-01", tz="UTC")], "value": [0.0]})
    stations = pd.DataFrame({"station_id": ["A", "B"], "latitude": [1.3, 1.31], "longitude": [103.8, 103.81]})
    try:
        checks.stuck_dry(hourly, stations, 10, 1, 5.0)
    except checks.BlockedByStub as err:
        assert "haversine_km" in str(err)
    else:
        pytest.skip("metrics.geo.haversine_km is implemented; blocked path no longer reachable")
