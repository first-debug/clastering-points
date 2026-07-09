import asyncio
import json
import numpy as np
from sklearn.cluster import DBSCAN
import websockets
from websockets.asyncio.server import ServerConnection
from shapely.geometry import Point, Polygon
from pyproj import Transformer
from math import atan2


UDP_HOST = '0.0.0.0'
UDP_PORT = 6767
WS_HOST = '0.0.0.0'
WS_PORT = 8765

MAX_DISTANCE_M = 30.0
EARTH_RADIUS_M = 6371000

left_up = (55.980321,
           37.410338)
right_up = (55.981181,
            37.416553)
right_bottum = (55.976810,
            37.418634)
left_bottum = (55.975907,
            37.412519)

connected_clients: set[ServerConnection] = set()
queue: dict = {}
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

valid_area = [
        {
            'lat': left_up[0],
            'lng': left_up[1],
            'name': 'area',
        },
        {
            'lat': right_up[0],
            'lng': right_up[1],
            'name': 'area',
        },
        {
            'lat': right_bottum[0],
            'lng': right_bottum[1],
            'name': 'area',
        },
        {
            'lat': left_bottum[0],
            'lng': left_bottum[1],
            'name': 'area',
        },
    ]

def order_points(points):
     cx = sum(p[0] for p in points) / len(points)
     cy = sum(p[1] for p in points) / len(points)
     res = sorted(points, key=lambda p: atan2(p[1] - cy, p[0] - cx))
     res.append(res[0])
     return res

def check_coords(coords: list) -> list:
    """Принимает (широта, долгота)"""
    result = []

    # Разворачиваем координаты. Было lat = x, lon = y, стало lat = y, lon = x
    # и находим правильный порядок соединения вершин (по  часовой стрелке)
    polygon = Polygon(order_points([x[::-1] for x in [left_up, right_up, right_bottum, left_bottum]]))

    if not polygon.is_valid:
        print("Polygon is invalid!")
        return result


    for lat, lng in coords:
        if polygon.contains(Point(lng, lat)):
            result.append([lat, lng])
            continue
        print("Filtered point:", (lat, lng))

    # fig, ax = plt.subplots()
    # plot_polygon(polygon, ax=ax, add_points=True, facecolor='lightblue', edgecolor='blue')

    # np_coords = np.array(result)
    # plt.scatter(np_coords[:, 0], np_coords[:, 1])
    # plt.savefig("poly.png")
    return result


def check_coords_squer(coords: list) -> list:
    result = []
    for lng, lat in coords:
        if (55.975907 <= lng <= 55.981181) and (37.410338 <= lat <= 37.418634):
            result.append([lat, lng])
            continue
    return result


def cluster_objects(objects: list[dict], max_distance_m: float = 15.0) -> list[dict]:
    if not objects:
        return []
    # отдаём (широта, долгота)
    # FIX: нужно передать и возвращать целые объекты
    filtered_coords: list = check_coords([[o['lat'], o['lng']] for o in objects])
    if len(filtered_coords) == 0:
        return []

    result = []

    coords = np.radians(filtered_coords)
    eps = max_distance_m / EARTH_RADIUS_M


    clustering = DBSCAN(eps=eps, min_samples=1, metric='haversine').fit(coords)
    labels = clustering.labels_

    print(objects)
    print(labels)
    print(filtered_coords)
    clusters = {}
    for label, obj in zip(labels, objects):
        clusters.setdefault(label, []).append(obj)

    for cluster_objs in clusters.values():
        best = max(cluster_objs, key=lambda o: float(o['confidence']))
        result.append(best)

    return result


def process_data(data: dict, addr) -> dict:
    time = str(data.get('timestamp')).split('.')[0]
    prev: dict = queue.pop(time, {})
    if len(prev) == 0:
        queue[time] = data
        return {}
    prev_fut = prev.get('future', [])
    cur_fut = data.get('future', [])
    deduped = cluster_objects(prev_fut + cur_fut, max_distance_m=MAX_DISTANCE_M)
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
    # asyncio.gather с return_exceptions, чтобы отвал одного клиента не рушил остальных
    await asyncio.gather(
        *(client.send(payload) for client in connected_clients),
        return_exceptions=True,
    )


async def ws_handler(websocket: ServerConnection):
    connected_clients.add(websocket)
    print(f"WS клиент подключился: {websocket.remote_address}, всего клиентов: {len(connected_clients)}")
    try:
        async for _ in websocket:
            pass
    except websockets.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"WS клиент отключился, всего клиентов: {len(connected_clients)}")


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
            response = process_data(message, addr)
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
    print(f"UDP сервер запущен на {UDP_HOST}:{UDP_PORT}")

    ws_server = await websockets.serve(ws_handler, WS_HOST, WS_PORT)
    print(f"WebSocket сервер запущен на {WS_HOST}:{WS_PORT}")

    try:
        await asyncio.Future()
    finally:
        udp_transport.close()
        ws_server.close()
        await ws_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())

