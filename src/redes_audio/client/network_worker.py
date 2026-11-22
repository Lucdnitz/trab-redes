"""Worker Qt que mantém UDP e WebSocket fora do thread da interface."""

from __future__ import annotations

import asyncio
import json
import time
from threading import Event

from PySide6.QtCore import QThread, Signal
from websockets.asyncio.client import connect

from redes_audio.core.jitter_buffer import JitterBuffer
from redes_audio.shared.protocol import AudioPacket, PacketDecodeError


class DatagramReceiver(asyncio.DatagramProtocol):
    def __init__(self, buffer: JitterBuffer, on_packet) -> None:
        self.buffer = buffer
        self.on_packet = on_packet

    def datagram_received(self, data: bytes, _addr) -> None:
        try:
            packet = AudioPacket.decode(data)
        except PacketDecodeError:
            return
        self.buffer.push(packet, wire_bytes=len(data))
        self.on_packet()


class NetworkWorker(QThread):
    connected = Signal(dict)
    event_received = Signal(dict)
    metrics_changed = Signal(dict)
    error = Signal(str)

    def __init__(self, server_host: str, udp_port: int, buffer: JitterBuffer) -> None:
        super().__init__()
        self.server_host = server_host
        self.udp_port = udp_port
        self.buffer = buffer
        self._stop_event = Event()
        self._last_metrics_emit = 0.0

    def run(self) -> None:
        try:
            asyncio.run(self._run_async())
        except Exception as exc:  # Qt precisa converter a falha em sinal para a GUI.
            self.error.emit(str(exc))

    async def _run_async(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: DatagramReceiver(self.buffer, self._publish_metrics),
            local_addr=("0.0.0.0", self.udp_port),
        )

        uri = f"ws://{self.server_host}:8000/ws"
        try:
            async with connect(uri) as websocket:
                await websocket.send(json.dumps({"type": "register", "udp_port": self.udp_port}))
                registration = json.loads(await websocket.recv())
                self.connected.emit(registration)

                while not self._stop_event.is_set():
                    try:
                        raw = await asyncio.wait_for(websocket.recv(), timeout=0.25)
                    except TimeoutError:
                        self._publish_metrics()
                        continue
                    self.event_received.emit(json.loads(raw))
        finally:
            transport.close()

    def _publish_metrics(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_metrics_emit < 0.2:
            return
        self._last_metrics_emit = now
        values = self.buffer.metrics().to_dict()
        values["depth"] = self.buffer.depth()
        self.metrics_changed.emit(values)

    def stop(self) -> None:
        self._stop_event.set()
