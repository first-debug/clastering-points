from math import atan2
from shapely import is_valid_reason
from shapely.geometry import Polygon


def order_points(points):
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    res = sorted(points, key=lambda p: atan2(p[1] - cy, p[0] - cx))
    res.append(res[0])
    return res


def fill_polygon(coords: list[set[float]]) -> Polygon | None:
    if len(coords) == 0:
        print("Coords list is empty.")
        return None
    poly = Polygon(order_points(coords))
    if poly.is_valid is not True:
        print("Polygon is incorrect. Reason:", is_valid_reason(poly))
        return None
    return poly


def make_valid_aera_points(points: list[dict]) -> list[dict]:
    return [p | {'name': 'area'} for p in points]
