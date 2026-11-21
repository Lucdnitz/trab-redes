from redes_audio.core.jitter_buffer import JitterBuffer
from redes_audio.shared.protocol import AudioPacket


def packet(sequence: int) -> AudioPacket:
    return AudioPacket(sequence=sequence, timestamp_samples=sequence * 320, payload=b"pcm")


def test_waits_for_prefill_and_reorders_packets() -> None:
    buffer = JitterBuffer(prefill_frames=3, max_frames=10)
    buffer.push(packet(2))
    buffer.push(packet(0))
    assert buffer.pop_next() is None

    buffer.push(packet(1))
    assert buffer.pop_next().sequence == 0
    assert buffer.pop_next().sequence == 1
    assert buffer.pop_next().sequence == 2


def test_counts_missing_and_late_packets() -> None:
    buffer = JitterBuffer(prefill_frames=2, max_frames=10)
    buffer.push(packet(10))
    buffer.push(packet(12))

    assert buffer.pop_next().sequence == 10
    assert buffer.pop_next() is None
    assert buffer.pop_next().sequence == 12
    assert buffer.push(packet(11)) is False

    metrics = buffer.metrics()
    assert metrics.lost == 1
    assert metrics.late == 1
