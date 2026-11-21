"""Transmissor UDP com fonte PCM de demonstração."""

from __future__ import annotations

import asyncio
import math
import socket
from array import array

from redes_audio.server.registry import ClientRegistry
from redes_audio.shared.protocol import AudioCodec, AudioPacket


class AudioBroadcaster:
    def __init__(self, registry: ClientRegistry, *, sample_rate: int, frame_ms: int) -> None:
        self.registry = registry
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.samples_per_frame = sample_rate * frame_ms // 1000

    async def stream_demo_tone(self, *, duration_seconds: float = 3.0, frequency: int = 440) -> int:
        """Envia um tom PCM em tempo real para todos os clientes registrados."""
        total_frames = int(duration_seconds * 1000 / self.frame_ms)
        sequence = 0
        timestamp = 0
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            for _ in range(total_frames):
                samples = array(
                    "h",
                    (
                        int(
                            8_000
                            * math.sin(
                                2 * math.pi * frequency * (timestamp + i) / self.sample_rate
                            )
                        )
                        for i in range(self.samples_per_frame)
                    ),
                )
                packet = AudioPacket(
                    sequence=sequence,
                    timestamp_samples=timestamp,
                    codec=AudioCodec.PCM,
                    payload=samples.tobytes(),
                ).encode()

                clients = await self.registry.snapshot()
                for client in clients:
                    sock.sendto(packet, (client.host, client.udp_port))

                sequence += 1
                timestamp += self.samples_per_frame
                await asyncio.sleep(self.frame_ms / 1000)
        finally:
            sock.close()

        return total_frames
