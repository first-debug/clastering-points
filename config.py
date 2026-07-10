from yaml import safe_load


class Config:
    udp_host: str
    udp_port: int
    ws_host: str
    ws_port: int
    max_distance_m: float
    earth_radius_m: int
    polygon_coords: list[dict]

    def __init__(self, udp_host: str, udp_port: int,
                 ws_host: str, ws_port: int,
                 max_distance_m: float, earth_radius_m: int,
                 polygon_coords: list[dict]
                 ) -> None:
        assert udp_host != ""
        assert udp_port != 0
        assert ws_host != ""
        assert ws_port != 0
        assert max_distance_m != 0.
        assert earth_radius_m != 0
        assert polygon_coords is not None
        assert len(polygon_coords) != 0

        self.udp_host = udp_host
        self.udp_port = udp_port
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.max_distance_m = max_distance_m
        self.earth_radius_m = earth_radius_m
        self.polygon_coords = polygon_coords


def load_config(file_name: str = "config.yaml") -> Config | None:
    with open(file_name, "r", encoding="utf-8") as file:
        cfg = safe_load(file)

        return Config(
                cfg.get("udp-host", "0.0.0.0"),
                cfg.get("udp-port", 6767),
                cfg.get("ws-host", "0.0.0.0"),
                cfg.get("ws-port", 8675),
                cfg.get("max-distance-m", 30.),
                cfg.get("earth-radius-m", 6371000),
                cfg.get("polygon-coords", [])
                )
