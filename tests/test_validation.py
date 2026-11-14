"""Plumbing for the validation tables and the small trained model, on tables in memory."""
import numpy as np
import pandas as pd
import pytest

from tropics_scorecard.baselines.always_dry import AlwaysDry
from tropics_scorecard.scorer import postprocess, summary
from tropics_scorecard.scorer.validation import PerfectCell

CFG = {"bootstrap": {"block_length_days": 2, "resamples": 50, "alpha": 0.05, "seed": 0},
       "summary_scores": {"cell_mean_min_gauges": 3}}


def pairs(forecast, observed, days=10):
    n = len(forecast)
    return pd.DataFrame({"station_key": "a", "valid_time": pd.date_range("2024-03-01", periods=n, freq="h", tz="UTC"),
                         "forecast": forecast, "observed": observed, "day": [f"d{i % days}" for i in range(n)]})


def test_always_dry_is_zero_for_rain_only():
    cases = pd.DataFrame({"station_key": ["a"], "valid_time": [pd.Timestamp("2024-03-01", tz="UTC")], "lead_kind": "day", "lead": 1})
    assert AlwaysDry().predict("rain_hourly", cases).tolist() == [0.0]
    assert AlwaysDry().predict("temperature_2m", cases).isna().all()


def test_paired_change_in_rmse_and_mae():
    obs = [0.0] * 40
    model, ref = pairs([1.0] * 40, obs), pairs([2.0] * 40, obs)
    assert summary.paired_change(model, ref, CFG, "mae")["percent"][0] == pytest.approx(-50.0)
    # mean squared errors 1 and 4: root mean square error halves too
    assert summary.paired_change(model, ref, CFG, "rmse")["percent"][0] == pytest.approx(-50.0)
    assert summary.paired_change(pairs([1.0] * 2, [0.0] * 2, days=2), pairs([2.0] * 2, [0.0] * 2, days=2), CFG) is None


def test_perfect_cell_leaves_the_gauge_itself_out():
    t = pd.Timestamp("2024-03-01 06:00", tz="UTC")
    p = pd.DataFrame({"station_key": ["a", "b", "c", "d"], "valid_time": t, "observed": [0.0, 3.0, 6.0, 100.0]})
    pc = PerfectCell.__new__(PerfectCell)
    pc.cfg = CFG
    pc.cells = pd.DataFrame({"station_key": ["a", "b", "c", "d"], "cell_lat": [1.25, 1.25, 1.25, 1.5], "cell_lon": 103.75})
    out = pc.six_hour(p).set_index("station_key")["forecast"]
    assert out.to_dict() == {"a": 4.5, "b": 3.0, "c": 1.5}  # d is alone in its cell: fewer than 3 gauges


def test_linear_fit_recovers_a_known_rule():
    rng = np.random.default_rng(0)
    d = pd.DataFrame({c: rng.normal(size=400) for c in postprocess.INPUTS})
    d["observed"] = 2.0 + 0.5 * d["ecmwf_ifs025"] - 1.5 * d["climatology"]
    predict, coef = postprocess.fit_linear(d)
    assert coef[0] == pytest.approx(2.0)
    assert dict(zip(postprocess.INPUTS, coef[1:]))["ecmwf_ifs025"] == pytest.approx(0.5)
    assert np.allclose(predict(d), d["observed"])
