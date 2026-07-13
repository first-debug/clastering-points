from typing import Callable
from asyncio import gather, DatagramProtocol
import json
import websockets
from websockets.asyncio.server import ServerConnection


class WebSocketService:
    def __init__(self, ):
        self.connected_clients: set[ServerConnection] = set()

    async def handler(self, websocket: ServerConnection):
        self.connected_clients.add(websocket)
        print(f"WS клиент подключился: {websocket.remote_address}, \
              всего клиентов: {len(self.connected_clients)}")
        try:
            async for _ in websocket:
                pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self.connected_clients.discard(websocket)
            print(f"WS клиент отключился, \
                  всего клиентов: {len(self.connected_clients)}")

    async def broadcast(self, message: dict):
        """Отправить сообщение всем подключённым websocket-клиентам."""
        if not self.connected_clients:
            return
        payload = json.dumps(message, ensure_ascii=False)
        await gather(
            *(client.send(payload) for client in self.connected_clients),
            return_exceptions=True,
        )


class UDPProtocol(DatagramProtocol):
    def __init__(self, loop, broadcast_func: Callable[[dict], None],
                 process_func: Callable[[dict], dict]):
        self.loop = loop
        self.broadcast_func: Callable[[dict]] = broadcast_func
        self.process_func: Callable[[dict], dict] = process_func

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Ошибка парсинга JSON от {addr}: {e}")
            return

        try:
            response = self.process_func(message)
        except Exception as e:
            print(f"Ошибка обработки данных от {addr}: {e}")
            return

        self.loop.create_task(self.broadcast_func(response))
