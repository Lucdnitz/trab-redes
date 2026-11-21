"""Reprodução PCM em ritmo fixo a partir do jitter buffer."""

from __future__ import annotations

from threading import Event

from PySide6.QtCore import QThread, Signal

from redes_audio.core.jitter_buffer import JitterBuffer
from redes_audio.shared.protocol import AudioCodec


class PlaybackWorker(QThread):
    error = Signal(str)

    def __init__(
        self,
        buffer: JitterBuffer,
        *,
        sample_rate: int = 16_000,
        frame_ms: int = 20,
    ) -> None:
        super().__init__()
        self.buffer = buffer
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.samples_per_frame = sample_rate * frame_ms // 1000
        self._stop_event = Event()
        self._paused = Event()

    def run(self) -> None:
        try:
            import sounddevice as sd

            silence = bytes(self.samples_per_frame * 2)
            with sd.RawOutputStream(
                samplerate=self.sample_rate,
                blocksize=self.samples_per_frame,
                channels=1,
                dtype="int16",
            ) as stream:
                while not self._stop_event.is_set():
                    if self._paused.is_set():
                        self.msleep(self.frame_ms)
                        continue

                    packet = self.buffer.pop_next()
                    if packet is None:
                        stream.write(silence)
                    elif packet.codec is AudioCodec.PCM:
                        stream.write(packet.payload)
                    else:
                        stream.write(silence)
        except Exception as exc:
            self.error.emit(str(exc))

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()

    def stop(self) -> None:
        self._stop_event.set()
