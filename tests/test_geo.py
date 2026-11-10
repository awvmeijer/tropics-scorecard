import math

import pytest

from tropics_scorecard.metrics.geo import haversine_km, nearest_station


def test_same_point_is_zero():
    assert haversine_km(1.35, 103.82, 1.35, 103.82) == pytest.approx(0.0, abs=1e-9)


def test_one_degree_of_longitude_on_the_equator():
    assert haversine_km(0, 0, 0, 1) == pytest.approx(6371.0 * math.pi / 180, abs=1e-6)


def test_one_degree_of_latitude():
    assert haversine_km(10, 50, 11, 50) == pytest.approx(6371.0 * math.pi / 180, abs=1e-6)


def test_half_way_round_the_world():
    assert haversine_km(0, 0, 0, 180) == pytest.approx(6371.0 * math.pi, abs=1e-6)


def test_symmetry():
    assert haversine_km(1.36, 103.99, 3.12, 101.55) == pytest.approx(
        haversine_km(3.12, 101.55, 1.36, 103.99)
    )


def test_nearest_station():
    stations = {"north": (1.45, 103.82), "east": (1.36, 103.99), "west": (1.33, 103.70)}
    station_id, distance = nearest_station(1.35, 103.95, stations)
    assert station_id == "east"
    assert distance == pytest.approx(haversine_km(1.35, 103.95, 1.36, 103.99))


def test_nearest_station_tie_and_empty():
    stations = {"b": (0.0, 1.0), "a": (0.0, -1.0)}
    assert nearest_station(0.0, 0.0, stations)[0] == "a"
    with pytest.raises(ValueError):
        nearest_station(0.0, 0.0, {})
