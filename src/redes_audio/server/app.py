"""Aplicação FastAPI do servidor."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from redes_audio import __version__
from redes_audio.server.broadcaster import AudioBroadcaster
from redes_audio.server.config import settings
from redes_audio.server.registry import ClientEndpoint, ClientRegistry


class HealthResponse(BaseModel):
    status: str
    version: str
    clients: int


registry = ClientRegistry()
broadcaster = AudioBroadcaster(
    registry,
    sample_rate=settings.sample_rate,
    frame_ms=settings.frame_duration_ms,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="Redes Audio Live",
    version=__version__,
    description="Servidor UDP e WebSocket do Projeto 2 de Redes",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, clients=await registry.count())


@app.get("/api/v1/session")
async def session_status() -> dict[str, object]:
    clients = await registry.snapshot()
    return {
        "clients": [
            {"client_id": item.client_id, "host": item.host, "udp_port": item.udp_port}
            for item in clients
        ],
        "sample_rate": settings.sample_rate,
        "frame_duration_ms": settings.frame_duration_ms,
    }


@app.post("/api/v1/demo/start", status_code=status.HTTP_202_ACCEPTED)
async def start_demo() -> dict[str, object]:
    client_count = await registry.count()
    if client_count:
        asyncio.create_task(broadcaster.stream_demo_tone())
    return {"accepted": bool(client_count), "clients": client_count}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    client_id = str(uuid.uuid4())

    try:
        first_message = json.loads(await websocket.receive_text())
        if first_message.get("type") != "register":
            await websocket.close(code=1008, reason="first message must register the client")
            return

        udp_port = int(first_message["udp_port"])
        if not 1 <= udp_port <= 65_535:
            await websocket.close(code=1008, reason="invalid UDP port")
            return

        host = websocket.client.host if websocket.client else "127.0.0.1"
        await registry.register(ClientEndpoint(client_id=client_id, host=host, udp_port=udp_port))
        await websocket.send_json(
            {
                "type": "registered",
                "client_id": client_id,
                "sample_rate": settings.sample_rate,
                "frame_duration_ms": settings.frame_duration_ms,
            }
        )

        while True:
            message = json.loads(await websocket.receive_text())
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass
    finally:
        await registry.unregister(client_id)
