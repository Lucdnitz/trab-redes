"""Registro em memória dos endpoints UDP observados."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClientEndpoint:
    client_id: str
    host: str
    udp_port: int


class ClientRegistry:
    def __init__(self) -> None:
        self._clients: dict[str, ClientEndpoint] = {}
        self._lock = asyncio.Lock()

    async def register(self, endpoint: ClientEndpoint) -> None:
        async with self._lock:
            self._clients[endpoint.client_id] = endpoint

    async def unregister(self, client_id: str) -> None:
        async with self._lock:
            self._clients.pop(client_id, None)

    async def snapshot(self) -> tuple[ClientEndpoint, ...]:
        async with self._lock:
            return tuple(self._clients.values())

    async def count(self) -> int:
        async with self._lock:
            return len(self._clients)
