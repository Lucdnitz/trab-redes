"""Registro em memória dos endpoints UDP observados."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket


@dataclass(frozen=True, slots=True)
class ClientEndpoint:
    client_id: str
    host: str
    udp_port: int


class ClientRegistry:
    def __init__(self) -> None:
        self._clients: dict[str, ClientEndpoint] = {}
        self._websockets: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        endpoint: ClientEndpoint,
        websocket: WebSocket | None = None,
    ) -> None:
        async with self._lock:
            self._clients[endpoint.client_id] = endpoint
            if websocket is not None:
                self._websockets[endpoint.client_id] = websocket

    async def unregister(self, client_id: str) -> None:
        async with self._lock:
            self._clients.pop(client_id, None)
            self._websockets.pop(client_id, None)

    async def snapshot(self) -> tuple[ClientEndpoint, ...]:
        async with self._lock:
            return tuple(self._clients.values())

    async def count(self) -> int:
        async with self._lock:
            return len(self._clients)

    async def broadcast_json(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._websockets.items())

        stale: list[str] = []
        for client_id, ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(client_id)

        if stale:
            async with self._lock:
                for client_id in stale:
                    self._websockets.pop(client_id, None)
