from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0

Point = tuple[float, float, float]  # (lat, lon, elevation_m)


def parse_gpx(gpx_bytes: bytes) -> list[Point]:
    import gpxpy

    gpx = gpxpy.parse(gpx_bytes.decode("utf-8"))
    points: list[Point] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude, point.elevation or 0.0))

    if len(points) < 2:
        raise ValueError("GPX file has fewer than two track points")

    return points


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def cumulative_distance_km(points: list[Point]) -> list[float]:
    distances = [0.0]
    for (lat1, lon1, _), (lat2, lon2, _) in zip(points, points[1:]):
        distances.append(distances[-1] + haversine_km(lat1, lon1, lat2, lon2))
    return distances
