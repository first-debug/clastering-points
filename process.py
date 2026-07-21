import numpy as np
from sklearn.cluster import DBSCAN
from collections.abc import Callable
from shapely.geometry import Polygon

from select_funcs import max_confidence
from tools import check_coords, order_points
from config import Config
from tools import make_valid_aera_points


class ProcessService:
    def __init__(self, cfg: Config):
        self.queue = {}
        self.earth_radius_m = cfg.earth_radius_m
        self.max_distance_m = cfg.max_distance_m
        self.valid_area: list[dict] = make_valid_aera_points(
                cfg.polygon_coords
                )
        self.polygon: Polygon = Polygon(
            order_points([(i['lng'], i['lat']) for i in cfg.polygon_coords])
            )

    def cluster_objects(self, objects: list[dict],
                        select_best_point: Callable[[list[dict]], dict],
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
            best = select_best_point(cluster_objs)
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
                max_confidence,
                max_distance_m=self.max_distance_m)
        deduped.extend(self.valid_area)
        return {
            'camera_id': 0,
            'timestamp': data.get('timestamp'),
            'future': deduped,
        }
