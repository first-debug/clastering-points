from asyncio import get_running_loop, run, Future
import sys
import websockets

import config
from servers import WebSocketService, UDPProtocol
from process import ProcessService


async def main(cfg: config.Config):
    ws = WebSocketService()
    process_service = ProcessService(cfg)
    loop = get_running_loop()

    udp_transport, _ = await loop.create_datagram_endpoint(
        lambda: UDPProtocol(loop, ws.broadcast, process_service.process),
        local_addr=(cfg.udp_host, cfg.udp_port),
    )
    print(f"UDP is listening {cfg.udp_host}:{cfg.udp_port}")

    ws_server = await websockets.serve(ws.handler, cfg.ws_host, cfg.ws_port)
    print(f"WebSocket is running on {cfg.ws_host}:{cfg.ws_port}")

    try:
        await Future()
    finally:
        udp_transport.close()
        ws_server.close()
        await ws_server.wait_closed()


if __name__ == "__main__":
    config_file = "config.yaml"
    if len(sys.argv) == 2:
        config_file = sys.argv[1]
    cfg = config.load_config(config_file)
    if cfg is None:
        print("Cannot load config file.")
        exit(-1)
    run(main(cfg))
