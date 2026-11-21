import pytest

from redes_audio.shared.protocol import AudioCodec, AudioPacket, PacketDecodeError


def test_audio_packet_round_trip() -> None:
    original = AudioPacket(
        sequence=42,
        timestamp_samples=13_440,
        codec=AudioCodec.PCM,
        payload=b"\x01\x02" * 320,
    )

    assert AudioPacket.decode(original.encode()) == original


def test_rejects_truncated_payload() -> None:
    encoded = AudioPacket(sequence=1, timestamp_samples=0, payload=b"abc").encode()

    with pytest.raises(PacketDecodeError, match="payload length"):
        AudioPacket.decode(encoded[:-1])


def test_rejects_payload_larger_than_datagram_budget() -> None:
    packet = AudioPacket(sequence=1, timestamp_samples=0, payload=bytes(2_000))

    with pytest.raises(ValueError, match="payload exceeds"):
        packet.encode()
