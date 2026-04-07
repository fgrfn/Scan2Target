"""WebSocket connection manager — broadcasts JSON events to all clients."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._clients: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        client_id = str(uuid.uuid4())[:8]
        async with self._lock:
            self._clients[client_id] = ws
        await ws.send_json({"type": "connected", "client_id": client_id})
        logger.debug("WS client %s connected (%d total)", client_id, len(self._clients))
        return client_id

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            self._clients.pop(client_id, None)
        logger.debug("WS client %s disconnected (%d remaining)", client_id, len(self._clients))

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self._clients:
            return
        data = json.dumps(payload)
        dead: list[str] = []
        for cid, ws in list(self._clients.items()):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(cid)
        async with self._lock:
            for cid in dead:
                self._clients.pop(cid, None)

    async def broadcast_job(self, job: dict[str, Any]) -> None:
        await self.broadcast({"type": "job_update", "data": job})

    async def broadcast_scanner(self, uri: str, online: bool, name: str) -> None:
        await self.broadcast({"type": "scanner_update",
                              "data": {"uri": uri, "online": online, "name": name}})


_manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    return _manager
