import numpy as np
from sklearn.cluster import DBSCAN
from collections.abc import Callable
from shapely.geometry import Polygon

from tools import check_coords, order_points
from tools import make_valid_aera_points


class ProcessServiceConfig:
    def __init__(self,
                 max_distance_m: float,
                 earth_radius_m: int,
                 polygon_coords: list[dict],
                 best_point: Callable[[list[dict]], dict | None]):
        assert max_distance_m != 0.
        assert earth_radius_m != 0
        assert polygon_coords is not None
        assert len(polygon_coords) != 0
        assert best_point is not None

        self.max_distance_m = max_distance_m
        self.earth_radius_m = earth_radius_m
        self.polygon_coords = polygon_coords
        self.best_point_func = best_point


class ProcessService:
    def __init__(self,
                 cfg: ProcessServiceConfig):
        self.queue = {}

        self.earth_radius_m = cfg.earth_radius_m
        self.max_distance_m = cfg.max_distance_m
        self.valid_area = make_valid_aera_points(
                cfg.polygon_coords
                )
        self.polygon = Polygon(
            order_points([(i['lng'], i['lat']) for i in cfg.polygon_coords])
            )
        self.best_point_func = cfg.best_point_func

    def cluster_objects(self, objects: list[dict],
                        max_distance_m: float = 15.0) -> list[dict]:
        if not objects:
            return []
        filtered_coords: list = check_coords(objects, self.polygon)
        if len(filtered_coords) == 0:
            return []

        result = []

        coords = np.radians(
                [[c.get('lat'), c.get('lng')] for c in filtered_coords]
                )
        eps = max_distance_m / self.earth_radius_m

        clustering = DBSCAN(
                eps=eps, min_samples=1, metric='haversine'
                ).fit(coords)
        labels = clustering.labels_

        clusters = {}
        for label, obj in zip(labels, filtered_coords):
            clusters.setdefault(label, []).append(obj)

        for cluster_objs in clusters.values():
            best = self.best_point_func(cluster_objs)
            if best is None:
                continue
            result.append(best)

        return result

    def process(self, data: dict) -> dict:
        time = str(data.get('timestamp')).split('.')[0]
        prev: dict = self.queue.pop(time, {})
        if len(prev) == 0:
            self.queue[time] = data
            return {}
        prev_fut = prev.get('future', [])
        cur_fut = data.get('future', [])
        deduped = self.cluster_objects(
                prev_fut + cur_fut,
                max_distance_m=self.max_distance_m)
        deduped.extend(self.valid_area)
        return {
            'camera_id': 0,
            'timestamp': data.get('timestamp'),
            'future': deduped,
        }
