"""Plumbing tests for matching, baselines and the scorer.

The metric kernels have their own tests. Where these tests need the scorer to run past
them, they swap in sentinel functions that count their inputs. A sentinel is not an
implementation of any metric: it only shows which cases reached which call.
"""
import datetime as dt

import pandas as pd
import pytest

from tropics_scorecard import scorer
from tropics_scorecard.baselines.climatology import Climatology
from tropics_scorecard.baselines.persistence import Persistence
from tropics_scorecard.ingest import openmeteo as om_ingest
from tropics_scorecard.match import observations as obs
from tropics_scorecard.scorer import core
from tropics_scorecard.sources import ForecastSource
from tropics_scorecard.store import openmeteo as om_store

UTC = "UTC"


def cfg(**over):
    c = {
        "region": {"local_timezone": "Asia/Singapore"},
        "period": {"day_level_lead_times": {"start": "2024-03-01", "end": "2024-03-20"},
                   "hour_level_lead_times": {"start": "2024-03-01", "end": "2024-03-20"},
                   "climatology_years": {"start": "2017-01-01", "end": "2023-12-31"}},
        "variables": ["rain_hourly", "temperature_2m"],
        "rain_thresholds_mm_per_hour": [0.1, 10.0],
        "lead_times": {"days": [1], "hours": {"max": 2, "table_bin": 6}, "single_run_hours_utc": [0, 12]},
        "matching": {"cell_rule": "land", "cell_rule_sensitivity": "nearest", "gauge_stamp": "end",
                     "rain_readings_per_hour": 12, "instant_window_minutes": 0, "knots_to_ms": 0.514444},
        "baselines": {"persistence_day_offset_hours": 24, "climatology_min_years": 3,
                      "climatology_event_probability_cut": 0.5},
        "regimes": {"northeast_monsoon": {"start": "12-01", "end": "03-15"},
                    "inter_monsoon_1": {"start": "03-16", "end": "05-31"},
                    "southwest_monsoon": {"start": "06-01", "end": "09-30"},
                    "inter_monsoon_2": {"start": "10-01", "end": "11-30"}},
        "bootstrap": {"block_length_days": 2, "resamples": 10, "alpha": 0.05, "seed": 0},
        "forecast_sources": ["persistence", "climatology"],
        "proposals_accepted": True,
    }
    c.update(over)
    return c


# ---------------------------------------------------------------- matching

def test_hour_end_both_conventions():
    t = pd.Series(pd.to_datetime(["2024-03-01T10:00Z", "2024-03-01T10:05Z", "2024-03-01T11:00Z"]))
    assert obs.hour_end(t, "end").dt.hour.tolist() == [10, 11, 11]
    assert obs.hour_end(t, "start").dt.hour.tolist() == [11, 11, 12]
    with pytest.raises(ValueError):
        obs.hour_end(t, "middle")


def test_rain_hours_complete_flagged_and_stuck():
    times = pd.date_range("2024-03-01T10:05Z", "2024-03-01T11:00Z", freq="5min")
    r = pd.DataFrame({"station_id": "S1", "time_utc": times, "value": 0.2})
    r = pd.concat([r, pd.DataFrame({"station_id": "S2", "time_utc": times[:11], "value": 0.0})])
    flags = pd.DataFrame({"station_id": ["S1"], "time_utc": [times[3]], "check": ["range"]})
    h = obs.rain_hours(r, flags, "end", 12).set_index("station_key")
    assert h.loc["dgs:S1", "value"] == pytest.approx(2.4)
    assert bool(h.loc["dgs:S1", "complete"]) and bool(h.loc["dgs:S1", "flagged"])
    assert not bool(h.loc["dgs:S2", "complete"]) and not bool(h.loc["dgs:S2", "flagged"])
    stuck = pd.DataFrame({"station_id": ["S2"], "time_utc": [pd.Timestamp("2024-03-01T11:00Z")], "check": ["stuck_dry"]})
    h2 = obs.rain_hours(r, stuck, "end", 12).set_index("station_key")
    assert bool(h2.loc["dgs:S2", "flagged"]) and not bool(h2.loc["dgs:S1", "flagged"])


def test_instant_hours_on_the_hour_and_knots():
    times = pd.to_datetime(["2024-03-01T09:59Z", "2024-03-01T10:00Z", "2024-03-01T10:01Z"])
    r = pd.DataFrame({"station_id": "S1", "time_utc": times, "value": [9.0, 10.0, 11.0]})
    h = obs.instant_hours(r, pd.DataFrame(columns=["station_id", "time_utc", "check"]), 0, scale=0.5)
    assert h["value"].tolist() == [5.0] and h["time_utc"].tolist() == [pd.Timestamp("2024-03-01T10:00Z")]
    hw = obs.instant_hours(r, pd.DataFrame(columns=["station_id", "time_utc", "check"]), 1)
    assert hw["value"].tolist() == [10.0]


# ---------------------------------------------------------------- strata and cases

def test_regime_wraps_round_the_new_year():
    local = pd.Series(pd.to_datetime(["2024-12-15", "2024-03-15", "2024-03-16", "2024-07-01", "2024-10-31"]))
    assert core.regime(local, cfg()["regimes"]).tolist() == [
        "northeast_monsoon", "northeast_monsoon", "inter_monsoon_1", "southwest_monsoon", "inter_monsoon_2"]


def reference(days=20, stations=("dgs:S1", "dgs:S2"), start="2024-03-01"):
    t = pd.date_range(f"{start}T00:00Z", periods=24 * days, freq="h")
    rows = [pd.DataFrame({"station_key": s, "network": "dgs", "time_utc": t, "value": (i + 1) * 1.0,
                          "complete": True, "flagged": False}) for i, s in enumerate(stations)]
    return pd.concat(rows, ignore_index=True)


def test_cases_for_hour_leads_follow_the_run_hours():
    c = core.cases_for(cfg(), "temperature_2m", "hour", 3, reference=reference(days=2))
    runs = (c["valid_time"] - pd.Timedelta(hours=3)).dt.hour
    assert set(runs) == {0, 12}
    assert set(c["lead_kind"]) == {"hour"} and set(c["lead"]) == {3}
    assert {"day", "hour_local", "regime"} <= set(c.columns)


# ---------------------------------------------------------------- baselines

def test_persistence_offsets():
    p = Persistence(cfg())
    cases = pd.DataFrame({"station_key": "dgs:S1", "valid_time": pd.Timestamp("2024-03-05T06:00Z"),
                          "lead_kind": ["day", "day", "hour", "hour", "hour"], "lead": [1, 3, 5, 24, 25]})
    assert p.offset_hours(cases).tolist() == [24, 72, 24, 24, 48]
    issue = Persistence(cfg(), mode="issue")
    assert issue.offset_hours(cases).tolist() == [24, 72, 5, 24, 25]


def test_persistence_reads_the_earlier_observation(monkeypatch):
    ref = reference(days=3)
    ref.loc[(ref["station_key"] == "dgs:S1") & (ref["time_utc"] == pd.Timestamp("2024-03-01T06:00Z")), "value"] = 42.0
    monkeypatch.setattr(obs, "load", lambda v, s, e, **kw: ref)
    cases = pd.DataFrame({"station_key": ["dgs:S1", "dgs:S9"], "valid_time": pd.Timestamp("2024-03-02T06:00Z"),
                          "lead_kind": "day", "lead": 1})
    out = Persistence(cfg()).predict("temperature_2m", cases)
    assert out.iloc[0] == 42.0 and pd.isna(out.iloc[1])


def test_climatology_by_station_month_hour_with_network_fallback():
    hist = []
    for year in range(2017, 2021):
        t = pd.date_range(f"{year}-03-01T00:00Z", periods=24 * 3, freq="h")
        hist.append(pd.DataFrame({"station_key": "dgs:S1", "time_utc": t, "value": 1.0}))
    t = pd.date_range("2023-03-01T00:00Z", periods=24 * 3, freq="h")
    hist.append(pd.DataFrame({"station_key": "dgs:NEW", "time_utc": t, "value": 3.0}))
    clim = Climatology(cfg(), reference=pd.concat(hist, ignore_index=True))
    cases = pd.DataFrame({"station_key": ["dgs:S1", "dgs:NEW"], "valid_time": pd.Timestamp("2024-03-10T05:00Z"),
                          "lead_kind": "day", "lead": 2})
    assert clim.predict("rain_hourly", cases).tolist() == [1.0, pytest.approx(1.4)]
    assert clim.fallback_stations["rain_hourly"] == ["dgs:NEW"]
    assert clim.probability("rain_hourly", cases, 2.0).tolist() == [0.0, pytest.approx(0.2)]
    assert clim.says_yes("rain_hourly", cases, 0.5).tolist() == [True, True]


# ---------------------------------------------------------------- scorer

class Constant(ForecastSource):
    def __init__(self, name, value):
        self.name, self.value = name, value

    def predict(self, variable, cases):
        return pd.Series(self.value, index=cases.index, dtype=float)


@pytest.fixture
def sentinels(monkeypatch):
    """Count-only stand-ins for the metric kernels."""
    from tropics_scorecard.metrics import bootstrap, categorical, errors, probabilistic

    def count(f, o):
        return float(len(f))

    for name in ("bias", "mae", "rmse"):
        monkeypatch.setattr(errors, name, count)
    monkeypatch.setattr(probabilistic, "brier_score", count)
    monkeypatch.setattr(bootstrap, "block_bootstrap_ci_mean_diff",
                        lambda a, b, block, **kw: (float(len(a)), -1.0, float(block)))
    monkeypatch.setattr(categorical, "contingency", lambda f, o: (sum(f), 0, 0, len(f) - sum(f)))
    for name in ("pod", "far", "csi", "ets"):
        monkeypatch.setattr(categorical, name, lambda h, m, fa, cn: 0.5)


def pairs_for(source, variable="rain_hourly", days=20):
    c = core.cases_for(cfg(), variable, "day", 1, reference=reference(days=days))
    return core.make_pairs(source, variable, c, (0.1, 10.0))


def test_scorer_groups_and_counts(sentinels):
    p = pairs_for(Constant("x", 1.0), days=20)
    rows = pd.DataFrame(scorer.score_pairs(p, {"source": "x", "variable": "rain_hourly"}, cfg(),
                                           groups=("all", "hour_local", "regime"), thresholds=(0.1, 10.0)))
    mae = rows[(rows.metric == "mae") & (rows.hour_local == "all") & (rows.regime == "all")].iloc[0]
    assert mae.n_pairs == 2 * 24 * 20 and mae.n_days == 21  # 20 UTC days span 21 local days
    assert mae.high == 2.0  # the block length from config reached the bootstrap
    assert set(rows[rows.hour_local != "all"].hour_local) == {str(h) for h in range(24)}
    assert set(rows[rows.regime != "all"].regime) == {"northeast_monsoon", "inter_monsoon_1"}
    rmse = rows[(rows.metric == "rmse") & (rows.hour_local == "all") & (rows.regime == "all")].iloc[0]
    assert rmse.value == pytest.approx(21 ** 0.5)
    ets = rows[(rows.metric == "ets") & (rows.threshold == 0.1) & (rows.hour_local == "all") & (rows.regime == "all")]
    assert len(ets) == 1 and pd.isna(ets.iloc[0].low)
    ev = rows[(rows.metric == "observed_events") & (rows.threshold == 10.0) & (rows.hour_local == "all") & (rows.regime == "all")]
    assert ev.iloc[0].value == 0  # the sentinel table has no misses, and constant 1 mm never reaches 10 mm


def test_scorer_drops_groups_too_short_for_the_block(sentinels):
    p = pairs_for(Constant("x", 1.0), "temperature_2m", days=1)
    assert scorer.score_pairs(p, {"source": "x"}, cfg(bootstrap={"block_length_days": 5, "resamples": 10,
                                                                  "alpha": 0.05, "seed": 0})) == []


def test_comparison_uses_common_cases_only(sentinels):
    a = pairs_for(Constant("a", 1.0), "temperature_2m")
    b = pairs_for(Constant("b", 2.0), "temperature_2m")
    b = b[b["station_key"] == "dgs:S1"]
    rows = scorer.core.compare_pairs(a, b, {"source": "a"}, "b", cfg())
    assert len(rows) == 1 and rows[0]["against"] == "b" and rows[0]["n_pairs"] == 24 * 20


def test_nothing_is_scored_before_sign_off():
    with pytest.raises(core.NotReady, match="not signed off"):
        core.check_ready(cfg(proposals_accepted=False))
    with pytest.raises(core.NotReady, match="block_length_days"):
        core.check_ready(cfg(bootstrap={"block_length_days": "TODO"}))


# ---------------------------------------------------------------- Open-Meteo

def test_weight_is_pro_rata():
    assert om_ingest.weight(1, 3, 7) == 1
    assert om_ingest.weight(1, 15, 91) == pytest.approx(1.5 * 6.5)
    assert om_ingest.weight(4, 1, 1) == 4


def test_ledger_waits_when_full(tmp_path, monkeypatch):
    led = om_ingest.Ledger(tmp_path / "l.jsonl")
    led.record(0.8 * 600)
    slept = []
    monkeypatch.setattr(om_ingest.time, "sleep", lambda s: (slept.append(s), led.entries.clear()))
    led.wait_for(1)
    assert slept and slept[0] > 50


def test_parse_previous_and_single():
    body = {"latitude": 1.25, "longitude": 104.0, "elevation": 0.0,
            "hourly": {"time": ["2024-03-01T00:00", "2024-03-01T01:00"],
                       "precipitation_previous_day1": [0.0, 1.5], "temperature_2m_previous_day3": [27.0, None]}}
    df = om_store.parse_previous(body, "m")
    assert set(df["variable"]) == {"rain_hourly", "temperature_2m"}
    assert df[df.variable == "rain_hourly"]["lead_day"].tolist() == [1, 1]
    assert pd.isna(df[df.variable == "temperature_2m"]["value"].iloc[1])
    single = [{"latitude": 1.25, "longitude": 104.0, "elevation": 0.0,
               "hourly": {"time": ["2024-03-01T00:00", "2024-03-01T03:00"], "wind_speed_10m": [2.0, 3.0]}}]
    s = om_store.parse_single(single, "m", dt.datetime(2024, 3, 1, 0))
    assert s["lead_hours"].tolist() == [0, 3] and set(s["variable"]) == {"wind_speed_10m"}


def test_v2_day_kept_when_v1_lacks_the_day_file(tmp_path, monkeypatch):
    from tropics_scorecard.store import datagovsg as store

    monkeypatch.setattr(store, "CACHE", tmp_path)
    for day in ("2025-03-14", "2025-03-15"):
        d = tmp_path / "rainfall" / "2025" / day
        d.mkdir(parents=True)
        (d / "p001.json.gz").write_bytes(b"")
        (d / "DONE").write_text("1\n")
    only_midnight = tmp_path / "rainfall-v1" / "2025" / "2025-03-14"
    only_midnight.mkdir(parents=True)
    (only_midnight / "midnight.json.gz").write_bytes(b"")
    (only_midnight / "DONE").write_text("1\n")
    full = tmp_path / "rainfall-v1" / "2025" / "2025-03-15"
    full.mkdir(parents=True)
    (full / "day.json.gz").write_bytes(b"")
    (full / "DONE").write_text("2\n")
    assert [p.parent.name for p in store._pages("rainfall", 2025)] == ["2025-03-14"]


def test_single_runs_cached_twice_are_kept_once(tmp_path, monkeypatch):
    import gzip
    import json

    monkeypatch.setattr(om_store, "CACHE", tmp_path)
    monkeypatch.setattr(om_store, "OUT", tmp_path / "out")
    loc = {"latitude": 1.25, "longitude": 104.0, "elevation": 0.0,
           "hourly": {"time": ["2026-04-02T01:00"], "temperature_2m": [27.0]}}
    folder = tmp_path / "single" / "m" / "2026" / "2026-04-02T00"
    folder.mkdir(parents=True)
    for name in ("aaa.json.gz", "bbb.json.gz"):
        with gzip.open(folder / name, "wt") as fh:
            json.dump([loc], fh)
    df = pd.read_parquet(om_store.build_single("m"))
    assert len(df) == 1 and df["lead_hours"].tolist() == [1]


def test_exclusions_match_source_variable_and_lead():
    c = cfg(exclusions=[{"source": "m", "variable": "rain_hourly", "lead_kind": "day", "leads": [5, 7], "reason": "x"}])
    assert core.excluded(c, "m", "rain_hourly", "day", 7)
    assert not core.excluded(c, "m", "rain_hourly", "day", 3)
    assert not core.excluded(c, "m", "temperature_2m", "day", 7)
    assert not core.excluded(cfg(), "m", "rain_hourly", "day", 7)


def test_six_hour_totals_need_all_six_hours():
    c = core.cases_for(cfg(), "rain_hourly", "day", 1, reference=reference(days=2, stations=("dgs:S1",)))
    p = core.make_pairs(Constant("x", 0.5), "rain_hourly", c, ())
    p = p[p["valid_time"] != pd.Timestamp("2024-03-01T08:00Z")]  # break the window ending 12:00
    out = core.six_hour_totals(p, cfg())
    ends = set(out["valid_time"])
    assert pd.Timestamp("2024-03-01T12:00Z") not in ends and pd.Timestamp("2024-03-01T18:00Z") in ends
    assert set(out["forecast"]) == {3.0} and set(out["observed"]) == {6.0}
    assert set(out["valid_time"].dt.hour) <= {0, 6, 12, 18}
