import pandas as pd

from tropics_scorecard.store import datagovsg, igra, isd


def test_datagovsg_parse_page():
    body = {"data": {"readingUnit": "mm", "readingType": "TB1 Rainfall 5 Minute Total F",
                     "stations": [{"id": "S1", "name": "X", "location": {"latitude": 1.3, "longitude": 103.8}}],
                     "readings": [{"timestamp": "2024-02-04T00:05:00+08:00", "data": [{"stationId": "S1", "value": 0.2}]}]}}
    rows, stations = datagovsg.parse_page(body, "rainfall")
    assert rows == [{"station_id": "S1", "time": "2024-02-04T00:05:00+08:00", "variable": "rainfall",
                     "value": 0.2, "unit": "mm", "reading_type": "TB1 Rainfall 5 Minute Total F"}]
    assert stations[0]["latitude"] == 1.3


def test_isd_parse_and_preferred(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text(
        '"STATION","DATE","LATITUDE","LONGITUDE","ELEVATION","REPORT_TYPE","WND","TMP","DEW","AA1"\n'
        '"48698099999","2024-01-01T00:00:00","1.35","103.99","6.7","FM-12","340,1,N,0031,1","+0261,1","+0230,1",""\n'
        '"48698099999","2024-01-01T00:00:00","1.35","103.99","6.7","FM-15","340,1,N,0026,1","+0260,1","+0230,1","24,0314,3,1"\n'
        '"48698099999","2024-01-01T00:30:00","1.35","103.99","6.7","FM-15","999,9,C,0000,1","+9999,9","+0230,1",""\n'
    )
    d = isd.parse(csv)
    assert d["temperature_c"].tolist()[:2] == [26.1, 26.0]
    assert pd.isna(d["temperature_c"].iloc[2]) and pd.isna(d["wind_dir_deg"].iloc[2])
    assert d["wind_speed_ms"].iloc[0] == 3.1
    assert d["precip_period_h"].iloc[1] == 24 and d["precip_mm"].iloc[1] == 31.4
    assert d["preferred"].tolist() == [True, False, False]


def test_igra_fixed_width(tmp_path):
    f = tmp_path / "s.txt"
    f.write_text("#SNM00048698 2024 06 01 00 2333    2 ncdc-gts            13679  1039824\n21     0 100784B   33   264B-9999    28   330    29 \n20     2 100751    36B  266B-9999    19     0     2 \n")
    h, lv = igra.parse(f, first_year=2017)
    assert h["release_hhmm"].iloc[0] == "2333" and h["latitude"].iloc[0] == 1.3679
    assert lv["pressure_hpa"].iloc[0] == 1007.84 and lv["temperature_c"].iloc[0] == 26.4
    assert pd.isna(lv["rh_pct"].iloc[0]) and lv["wind_speed_ms"].iloc[0] == 2.9
