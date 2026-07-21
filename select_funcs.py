import math


def max_confidence(objs: list[dict]) -> dict:
    return max(objs, key=lambda o: float(o['confidence']))


def get_centered_coordinates(
        coords: list[dict]
        ) -> dict | None:
    if not coords:
        return None

    x = 0.0
    y = 0.0
    z = 0.0
    confidence = 0
    object_id = 10 ** 4

    num_coords = len(coords)

    for obj in coords:
        lat_rad = math.radians(float(obj['lat']))
        lon_rad = math.radians(float(obj['lng']))

        x += math.cos(lat_rad) * math.cos(lon_rad)
        y += math.cos(lat_rad) * math.sin(lon_rad)
        z += math.sin(lat_rad)

        confidence += float(obj['confidence'])
        object_id = min(object_id, int(obj['object_id']))

    x /= num_coords
    y /= num_coords
    z /= num_coords
    confidence /= num_coords

    hypotenuse = math.sqrt(x * x + y * y)
    center_lat = math.atan2(z, hypotenuse)
    center_lon = math.atan2(y, x)

    return {
            "name": "самалёт",
            "object_id": object_id,
            "lat": math.degrees(center_lat),
            "lng": math.degrees(center_lon),
            "confidence": confidence,
            }
