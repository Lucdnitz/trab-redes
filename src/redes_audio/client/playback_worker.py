"""Reprodução contínua PCM/Opus a partir do jitter buffer via buffer em anel."""

from __future__ import annotations

import time
from threading import Event, Lock

from PySide6.QtCore import QThread, Signal

from redes_audio.core.jitter_buffer import JitterBuffer
from redes_audio.shared.codec import FrameDecoder


class PlaybackWorker(QThread):
    error = Signal(str)
    position_changed = Signal(int)

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
        self._frame_bytes = self.samples_per_frame * 2
        self._max_ring_bytes = self._frame_bytes * 15
        self._decoder = FrameDecoder(sample_rate=sample_rate, frame_ms=frame_ms)
        self._ring = bytearray()
        self._ring_lock = Lock()
        self._primed = False
        self._stop_event = Event()
        self._paused = Event()

    def reset_stream(self) -> None:
        """Limpa o estado do decodificador e do anel ao iniciar nova transmissão."""
        self._decoder = FrameDecoder(sample_rate=self.sample_rate, frame_ms=self.frame_ms)
        with self._ring_lock:
            self._ring.clear()
            self._primed = False

    def _audio_callback(self, outdata, frames: int, _time_info, _status) -> None:
        needed = frames * 2
        with self._ring_lock:
            if not self._primed:
                if len(self._ring) < self._frame_bytes * 3:
                    outdata[:] = b"\x00" * needed
                    return
                self._primed = True

            available = len(self._ring)
            if available >= needed:
                outdata[:] = self._ring[:needed]
                del self._ring[:needed]
            elif available > 0:
                outdata[:available] = self._ring
                outdata[available:] = b"\x00" * (needed - available)
                self._ring.clear()
                self._primed = False
            else:
                outdata[:] = b"\x00" * needed
                self._primed = False

    def run(self) -> None:
        try:
            import sounddevice as sd

            frame_interval = self.frame_ms / 1000
            emitted_counter = 0

            with sd.RawOutputStream(
                samplerate=self.sample_rate,
                blocksize=0,
                latency="high",
                channels=1,
                dtype="int16",
                callback=self._audio_callback,
            ):
                next_tick = time.perf_counter()
                while not self._stop_event.is_set():
                    if self._paused.is_set():
                        with self._ring_lock:
                            self._ring.clear()
                            self._primed = False
                        self.msleep(self.frame_ms)
                        next_tick = time.perf_counter()
                        continue

                    with self._ring_lock:
                        ring_bytes = len(self._ring)

                    # Só consome do jitter buffer se o anel de saída ainda tiver folga.
                    if ring_bytes < self._max_ring_bytes:
                        packet = self.buffer.pop_next()
                        if packet is not None:
                            pcm = self._decoder.decode(packet.codec, packet.payload)
                            with self._ring_lock:
                                self._ring.extend(pcm)
                            emitted_counter += 1
                            if emitted_counter % 10 == 0:
                                self.position_changed.emit(packet.timestamp_samples)

                    next_tick += frame_interval
                    sleep_s = next_tick - time.perf_counter()
                    if sleep_s > 0.001:
                        time.sleep(sleep_s)
                    elif sleep_s < -0.2:
                        next_tick = time.perf_counter()
        except Exception as exc:
            self.error.emit(str(exc))

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()

    def stop(self) -> None:
        self._stop_event.set()
