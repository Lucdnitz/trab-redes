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
    bytes_received: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


class JitterBuffer:
    """Buffer limitado indexado pelo número de sequência.

    O consumo começa somente após `prefill_frames` quadros. Depois disso, cada chamada a
    `pop_next` avança exatamente uma sequência; uma lacuna é registrada como perda.
    Se o fluxo parar de enviar por `idle_rearm_frames` quadros consecutivos sem pacotes
    pendentes, o buffer volta a aguardar `prefill_frames` para não contar perdas infinitas.
    """

    def __init__(
        self,
        *,
        prefill_frames: int = 5,
        max_frames: int = 50,
        idle_rearm_frames: int = 25,
        initial_sequence: int | None = None,
    ) -> None:
        if prefill_frames < 1:
            raise ValueError("prefill_frames must be positive")
        if max_frames < prefill_frames:
            raise ValueError("max_frames must be greater than or equal to prefill_frames")
        if idle_rearm_frames < 1:
            raise ValueError("idle_rearm_frames must be positive")
        if initial_sequence is not None and initial_sequence < 0:
            raise ValueError("initial_sequence cannot be negative")

        self.prefill_frames = prefill_frames
        self.max_frames = max_frames
        self.idle_rearm_frames = idle_rearm_frames
        self.initial_sequence = initial_sequence
        self._packets: dict[int, AudioPacket] = {}
        self._expected_sequence: int | None = None
        self._started = False
        self._idle_gaps = 0
        self._pending_empty_losses = 0
        self._metrics = JitterMetrics()
        self._lock = Lock()

    def push(self, packet: AudioPacket, *, wire_bytes: int | None = None) -> bool:
        """Insere um pacote; retorna `False` quando ele não pode mais ser reproduzido."""
        with self._lock:
            self._metrics.received += 1
            self._metrics.bytes_received += (
                wire_bytes if wire_bytes is not None else len(packet.payload)
            )

            # Reinício limpo se um novo stream começar do zero após o anterior ter parado.
            if (
                not self._started
                and not self._packets
                and self._expected_sequence is not None
                and packet.sequence < self._expected_sequence
            ):
                self._expected_sequence = None
                self._pending_empty_losses = 0

            if self._expected_sequence is not None and packet.sequence < self._expected_sequence:
                self._metrics.late += 1
                return False
            if packet.sequence in self._packets:
                self._metrics.duplicates += 1
                return False

            if self._pending_empty_losses > 0:
                self._metrics.lost += self._pending_empty_losses
                self._pending_empty_losses = 0

            if len(self._packets) >= self.max_frames:
                oldest = min(self._packets)
                del self._packets[oldest]
                self._metrics.overflow_drops += 1

            self._packets[packet.sequence] = packet
            return True

    def pop_next(self) -> AudioPacket | None:
        """Entrega o próximo quadro ou `None` em espera/perda."""
        packet, _missing = self.pop_next_with_status()
        return packet

    def pop_next_with_status(self) -> tuple[AudioPacket | None, bool]:
        """Entrega `(pacote, perda_no_instante)` para preservar a linha do tempo.

        O segundo valor diferencia uma lacuna após o início da reprodução da espera pelo
        preenchimento inicial. Isso permite ao reprodutor inserir silêncio no instante exato
        do pacote perdido, sem transformar a perda em aceleração do áudio.
        """
        with self._lock:
            if not self._started:
                if len(self._packets) < self.prefill_frames:
                    return None, False
                self._expected_sequence = (
                    self.initial_sequence
                    if self.initial_sequence is not None
                    else min(self._packets)
                )
                self._started = True
                self._idle_gaps = 0
                self._pending_empty_losses = 0

            assert self._expected_sequence is not None
            sequence = self._expected_sequence
            self._expected_sequence += 1
            packet = self._packets.pop(sequence, None)

            if packet is None:
                if self._packets:
                    self._idle_gaps = 0
                    self._metrics.lost += 1 + self._pending_empty_losses
                    self._pending_empty_losses = 0
                    return None, True

                self._idle_gaps += 1
                if self._idle_gaps >= self.idle_rearm_frames:
                    self._started = False
                    self._idle_gaps = 0
                    self._pending_empty_losses = 0
                    return None, False
                else:
                    self._pending_empty_losses += 1
                return None, True

            self._idle_gaps = 0
            self._metrics.played += 1
            return packet, False

    def rearm(self) -> None:
        """Descarta fila atual para ressincronizar ao vivo sem zerar métricas."""
        with self._lock:
            self._packets.clear()
            self._expected_sequence = None
            self._started = False
            self._idle_gaps = 0
            self._pending_empty_losses = 0

    def reset(self) -> None:
        with self._lock:
            self._packets.clear()
            self._expected_sequence = None
            self._started = False
            self._idle_gaps = 0
            self._pending_empty_losses = 0
            self._metrics = JitterMetrics()

    def metrics(self) -> JitterMetrics:
        with self._lock:
            return JitterMetrics(**self._metrics.to_dict())

    def depth(self) -> int:
        with self._lock:
            return len(self._packets)
