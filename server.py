import asyncio
import sys
import json
import numpy as np
from sklearn.cluster import DBSCAN
import websockets
from websockets.asyncio.server import ServerConnection
from shapely.geometry import Point, Polygon
from collections.abc import Callable

from select_funcs import max_confidence
import config

polygon: Polygon
connected_clients: set[ServerConnection] = set()
queue: dict = {}
valid_area = list[dict]
cfg: config.Config

def check_coords(objects: list[dict]) -> list[dict]:
    result = []

    if not polygon.is_valid:
        print("Polygon is invalid!")
        return result

    for i in objects:
        lat = i.get('lat', None)
        lng = i.get('lng', None)
        if lat is None or lng is None:
            print("cannot parse 'lat' and 'lng' from object")
            continue

        if polygon.contains(Point(lng, lat)):
            result.append(i)
            continue
        print("Filtered point:", (lat, lng))

    return result


def cluster_objects(objects: list[dict],
                    select_best_point: Callable[[list[dict]], dict],
                    max_distance_m: float = 15.0) -> list[dict]:
    if not objects:
        return []
    filtered_coords: list = check_coords(objects)
    if len(filtered_coords) == 0:
        return []

    result = []

    coords = np.radians(
            [[c.get('lat'), c.get('lng')] for c in filtered_coords]
            )
    eps = max_distance_m / cfg.earth_radius_m

    clustering = DBSCAN(eps=eps, min_samples=1, metric='haversine').fit(coords)
    labels = clustering.labels_

    clusters = {}
    for label, obj in zip(labels, filtered_coords):
        clusters.setdefault(label, []).append(obj)

    for cluster_objs in clusters.values():
        best = select_best_point(cluster_objs)
        result.append(best)

    return result


def process_data(data: dict) -> dict:
    time = str(data.get('timestamp')).split('.')[0]
    prev: dict = queue.pop(time, {})
    if len(prev) == 0:
        queue[time] = data
        return {}
    prev_fut = prev.get('future', [])
    cur_fut = data.get('future', [])
    deduped = cluster_objects(
            prev_fut + cur_fut,
            max_confidence,
            max_distance_m=cfg.max_distance_m)
    deduped.extend(valid_area)
    return {
        'camera_id': data.get('camera_id'),
        'timestamp': data.get('timestamp'),
        'future': deduped,
    }


async def broadcast(message: dict):
    """Отправить сообщение всем подключённым websocket-клиентам."""
    if not connected_clients:
        return
    payload = json.dumps(message, ensure_ascii=False)
    await asyncio.gather(
        *(client.send(payload) for client in connected_clients),
        return_exceptions=True,
    )


async def ws_handler(websocket: ServerConnection):
    connected_clients.add(websocket)
    print(f"WS клиент подключился: {websocket.remote_address}, \
          всего клиентов: {len(connected_clients)}")
    try:
        async for _ in websocket:
            pass
    except websockets.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"WS клиент отключился, \
              всего клиентов: {len(connected_clients)}")


class UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, loop):
        self.loop = loop

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Ошибка парсинга JSON от {addr}: {e}")
            return

        try:
            response = process_data(message)
        except Exception as e:
            print(f"Ошибка обработки данных от {addr}: {e}")
            return

        self.loop.create_task(broadcast(response))


async def main():
    loop = asyncio.get_running_loop()

    udp_transport, _ = await loop.create_datagram_endpoint(
        lambda: UDPProtocol(loop),
        local_addr=(UDP_HOST, UDP_PORT),
    )
    print(f"UDP is listening {UDP_HOST}:{UDP_PORT}")

    ws_server = await websockets.serve(ws_handler, WS_HOST, WS_PORT)
    print(f"WebSocket is running on {WS_HOST}:{WS_PORT}")

    try:
        await asyncio.Future()
    finally:
        udp_transport.close()
        ws_server.close()
        await ws_server.wait_closed()


if __name__ == "__main__":
    config_file = ""
    if len(sys.argv) == 2:
        config_file = sys.argv[1]
    try_config = config.load_config(config_file)
    if try_config is None:
        print("Cannot load config file.")
        exit(-1)
    asyncio.run(main())
