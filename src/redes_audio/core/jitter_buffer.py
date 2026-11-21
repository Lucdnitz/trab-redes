"""Jitter buffer configurável para quadros de áudio sequenciados."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock

from redes_audio.shared.protocol import AudioPacket


@dataclass(slots=True)
class JitterMetrics:
    received: int = 0
    played: int = 0
    lost: int = 0
    late: int = 0
    duplicates: int = 0
    overflow_drops: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


class JitterBuffer:
    """Buffer limitado indexado pelo número de sequência.

    O consumo começa somente após `prefill_frames` quadros. Depois disso, cada chamada a
    `pop_next` avança exatamente uma sequência; uma lacuna é registrada como perda.
    """

    def __init__(self, *, prefill_frames: int = 5, max_frames: int = 50) -> None:
        if prefill_frames < 1:
            raise ValueError("prefill_frames must be positive")
        if max_frames < prefill_frames:
            raise ValueError("max_frames must be greater than or equal to prefill_frames")

        self.prefill_frames = prefill_frames
        self.max_frames = max_frames
        self._packets: dict[int, AudioPacket] = {}
        self._expected_sequence: int | None = None
        self._started = False
        self._metrics = JitterMetrics()
        self._lock = Lock()

    def push(self, packet: AudioPacket) -> bool:
        """Insere um pacote; retorna `False` quando ele não pode mais ser reproduzido."""
        with self._lock:
            self._metrics.received += 1

            if self._expected_sequence is not None and packet.sequence < self._expected_sequence:
                self._metrics.late += 1
                return False
            if packet.sequence in self._packets:
                self._metrics.duplicates += 1
                return False

            if len(self._packets) >= self.max_frames:
                oldest = min(self._packets)
                del self._packets[oldest]
                self._metrics.overflow_drops += 1

            self._packets[packet.sequence] = packet
            return True

    def pop_next(self) -> AudioPacket | None:
        """Entrega o próximo quadro ou `None` em espera/perda."""
        with self._lock:
            if not self._started:
                if len(self._packets) < self.prefill_frames:
                    return None
                self._expected_sequence = min(self._packets)
                self._started = True

            assert self._expected_sequence is not None
            sequence = self._expected_sequence
            self._expected_sequence += 1
            packet = self._packets.pop(sequence, None)

            if packet is None:
                self._metrics.lost += 1
                return None

            self._metrics.played += 1
            return packet

    def reset(self) -> None:
        with self._lock:
            self._packets.clear()
            self._expected_sequence = None
            self._started = False
            self._metrics = JitterMetrics()

    def metrics(self) -> JitterMetrics:
        with self._lock:
            return JitterMetrics(**self._metrics.to_dict())

    def depth(self) -> int:
        with self._lock:
            return len(self._packets)
