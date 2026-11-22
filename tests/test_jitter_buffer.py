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


def test_rearms_after_idle_and_accepts_restarted_stream() -> None:
    buffer = JitterBuffer(prefill_frames=2, max_frames=10, idle_rearm_frames=3)
    buffer.push(packet(0))
    buffer.push(packet(1))

    assert buffer.pop_next().sequence == 0
    assert buffer.pop_next().sequence == 1

    # 3 leituras vazias seguidas sinalizam fim/pausa do fluxo sem contar perdas falsas.
    for _ in range(3):
        assert buffer.pop_next() is None

    assert buffer.metrics().lost == 0

    # Um novo stream reiniciando na sequência 0 deve ser aceito normalmente.
    assert buffer.push(packet(0)) is True
    assert buffer.push(packet(1)) is True
    assert buffer.pop_next().sequence == 0


def test_known_initial_sequence_preserves_a_loss_at_the_start() -> None:
    buffer = JitterBuffer(prefill_frames=2, max_frames=10, initial_sequence=0)
    buffer.push(packet(1))
    buffer.push(packet(2))

    first, missing = buffer.pop_next_with_status()
    assert first is None
    assert missing is True
    assert buffer.metrics().lost == 1
    assert buffer.pop_next().sequence == 1


def test_reset_accepts_immediate_sequence_restart() -> None:
    buffer = JitterBuffer(prefill_frames=2, max_frames=10)
    buffer.push(packet(10))
    buffer.push(packet(11))
    assert buffer.pop_next().sequence == 10

    buffer.reset()
    buffer.push(packet(0))
    buffer.push(packet(1))
    assert buffer.pop_next().sequence == 0
    assert buffer.metrics().late == 0
