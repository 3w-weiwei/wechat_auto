from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection

from engine.adapters.handlers import Handlers


class WebSocketServer:
    """JSON-RPC over WebSocket server for UI <-> engine communication."""

    def __init__(
        self,
        handlers: Handlers,
        host: str = "localhost",
        port: int = 8765,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self._handlers = handlers
        self._host = host
        self._port = port
        self._on_log = on_log
        self._server: Any = None
        self._clients: set[ServerConnection] = set()

    async def start(self) -> None:
        self._server = await websockets.serve(
            self._handle_client, self._host, self._port
        )
        if self._on_log:
            self._on_log(f"[Server] Listening on ws://{self._host}:{self._port}")

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def broadcast(self, event: str, data: dict[str, object]) -> None:
        message = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        for client in list(self._clients):
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                self._clients.discard(client)

    async def _handle_client(self, websocket: ServerConnection) -> None:
        self._clients.add(websocket)
        try:
            async for raw_message in websocket:
                try:
                    request = json.loads(raw_message)
                    req_id = request.get("id")
                    method = request.get("method", "")
                    params = request.get("params", {})

                    result = self._handlers.dispatch(method, params)
                    response: dict[str, object] = {"id": req_id}
                    if isinstance(result, dict) and "error" in result:
                        response["error"] = result["error"]
                    else:
                        response["result"] = result

                    await websocket.send(json.dumps(response, ensure_ascii=False, default=str))
                except json.JSONDecodeError:
                    await websocket.send(
                        json.dumps({"id": None, "error": {"code": -32700, "message": "Parse error"}})
                    )
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
