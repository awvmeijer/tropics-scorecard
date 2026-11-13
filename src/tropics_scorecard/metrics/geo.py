"""Distances on the sphere."""
import math

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres between two points given in degrees.

    Use the haversine formula with EARTH_RADIUS_KM.
    """
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def nearest_station(lat, lon, stations):
    """Return (station_id, distance_km) of the closest station.

    stations maps station_id to (lat, lon). ValueError when it is empty.
    On a tie, return the station_id that sorts first.
    """
    if not stations:
        raise ValueError("no stations")
    distance, station_id = min((haversine_km(lat, lon, la, lo), sid) for sid, (la, lo) in stations.items())
    return station_id, distance
