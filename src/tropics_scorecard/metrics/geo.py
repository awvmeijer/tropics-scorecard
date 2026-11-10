"""Distances on the sphere."""

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres between two points given in degrees.

    Use the haversine formula with EARTH_RADIUS_KM.
    """
    raise NotImplementedError("write me by hand: metrics.geo.haversine_km")


def nearest_station(lat, lon, stations):
    """Return (station_id, distance_km) of the closest station.

    stations maps station_id to (lat, lon). ValueError when it is empty.
    On a tie, return the station_id that sorts first.
    """
    raise NotImplementedError("write me by hand: metrics.geo.nearest_station")
