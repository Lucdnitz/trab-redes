import asyncio
import socket

import pytest

from redes_audio.server.broadcaster import AudioBroadcaster
from redes_audio.server.registry import ClientEndpoint, ClientRegistry
from redes_audio.shared.protocol import AudioCodec, AudioPacket


@pytest.mark.asyncio
async def test_broadcaster_sends_decodable_pcm_packet() -> None:
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", 0))
    receiver.setblocking(False)
    udp_port = receiver.getsockname()[1]

    registry = ClientRegistry()
    await registry.register(ClientEndpoint("test", "127.0.0.1", udp_port))
    broadcaster = AudioBroadcaster(registry, sample_rate=16_000, frame_ms=20)

    stream_task = asyncio.create_task(broadcaster.stream_demo_tone(duration_seconds=0.04))
    try:
        datagram, _ = await asyncio.wait_for(
            asyncio.get_running_loop().sock_recvfrom(receiver, 2_048), timeout=1
        )
        packet = AudioPacket.decode(datagram)
        assert packet.codec is AudioCodec.PCM
        assert packet.sequence == 0
        assert len(packet.payload) == 640
    finally:
        await stream_task
        receiver.close()
