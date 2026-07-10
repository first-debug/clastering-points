from yaml import safe_load


class Config:
    udp_host: str
    udp_port: int
    ws_host: str
    ws_port: int
    max_distance_m: float
    earth_radius_m: int

    polygon_coords: list[dict]

    def __init__(self, udp_host: str = "0.0.0.0", udp_port: int = 6767,
                 ws_host: str = "0.0.0.0", ws_port: int = 8675,
                 max_distance_m: float = 30., earth_radius_m: int = 6371000,
                 polygon_coords: list[dict] = []
                 ) -> None:
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
                cfg["udp-host"],
                cfg["udp-port"],
                cfg["ws-host"],
                cfg["ws-port"],
                cfg["max-distance-m"],
                cfg["earth-radius-m"],
                cfg["polygon-coords"],
                )
