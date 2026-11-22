"""Codificação e decodificação de quadros de áudio PCM e Opus.

Usa PyAV (`av`) com `libopus` embutido para evitar dependências nativas externas no Windows
e no Linux. Todos os quadros de entrada/saída operam em PCM int16 mono 16 kHz (20 ms).
"""

from __future__ import annotations

import numpy as np

from redes_audio.shared.protocol import AudioCodec

DEFAULT_SAMPLE_RATE = 16_000
DEFAULT_FRAME_MS = 20
DEFAULT_OPUS_BITRATE = 24_000


def _import_av():
    try:
        import av  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - depende dos extras [ai]/[codec]
        raise RuntimeError(
            "PyAV (av) não instalado. Execute: pip install -e '.[ai]'"
        ) from exc
    return av


class OpusEncoder:
    """Codifica quadros PCM int16 mono (16 kHz, 20 ms) em pacotes Opus."""

    def __init__(
        self,
        *,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        frame_ms: int = DEFAULT_FRAME_MS,
        bitrate: int = DEFAULT_OPUS_BITRATE,
    ) -> None:
        av = _import_av()
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.bitrate = bitrate
        self._av = av
        self._samples_per_frame = sample_rate * frame_ms // 1000
        self._ctx = av.CodecContext.create("libopus", "w")
        self._ctx.sample_rate = sample_rate
        self._ctx.layout = "mono"
        self._ctx.format = "s16"
        self._ctx.bit_rate = bitrate
        self._ctx.open()

    def encode(self, pcm_bytes: bytes) -> bytes:
        expected_bytes = self._samples_per_frame * 2
        if len(pcm_bytes) != expected_bytes:
            raise ValueError(f"expected {expected_bytes} PCM bytes, got {len(pcm_bytes)}")

        samples = np.frombuffer(pcm_bytes, dtype=np.int16).reshape(1, self._samples_per_frame)
        frame = self._av.AudioFrame.from_ndarray(samples, format="s16", layout="mono")
        frame.sample_rate = self.sample_rate
        packets = self._ctx.encode(frame)
        if not packets:
            return b""
        return b"".join(bytes(packet) for packet in packets)


class OpusDecoder:
    """Decodifica pacotes Opus para quadros PCM int16 mono de tamanho fixo."""

    def __init__(
        self,
        *,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        frame_ms: int = DEFAULT_FRAME_MS,
    ) -> None:
        av = _import_av()
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self._av = av
        self._samples_per_frame = sample_rate * frame_ms // 1000
        self._frame_bytes = self._samples_per_frame * 2
        self._ctx = av.CodecContext.create("libopus", "r")
        self._ctx.open()
        self._resampler = av.AudioResampler(
            format="s16",
            layout="mono",
            rate=sample_rate,
        )
        self._pcm_buffer = bytearray()

    def decode(self, payload: bytes) -> bytes:
        packet = self._av.Packet(payload)
        for frame in self._ctx.decode(packet):
            for resampled in self._resampler.resample(frame):
                arr = resampled.to_ndarray()
                self._pcm_buffer.extend(arr.astype(np.int16, copy=False).tobytes())

        return self._pop_exact_frame()

    def decode_loss(self) -> bytes:
        """Gera silêncio alinhado ao quadro quando um pacote Opus se perde."""
        return bytes(self._frame_bytes)

    def _pop_exact_frame(self) -> bytes:
        if len(self._pcm_buffer) >= self._frame_bytes:
            chunk = bytes(self._pcm_buffer[: self._frame_bytes])
            del self._pcm_buffer[: self._frame_bytes]
            return chunk
        # O primeiro quadro reamostrado pode ter pequeno atraso de filtro (ex.: 304 amostras).
        missing = self._frame_bytes - len(self._pcm_buffer)
        chunk = bytes(self._pcm_buffer) + bytes(missing)
        self._pcm_buffer.clear()
        return chunk


class FrameEncoder:
    """Abstração única para codificar PCM ou Opus."""

    def __init__(self, codec: AudioCodec, *, sample_rate: int, frame_ms: int) -> None:
        self.codec = codec
        self._opus = (
            OpusEncoder(sample_rate=sample_rate, frame_ms=frame_ms)
            if codec is AudioCodec.OPUS
            else None
        )

    def encode(self, pcm_bytes: bytes) -> bytes:
        if self._opus is None:
            return pcm_bytes
        return self._opus.encode(pcm_bytes)


class FrameDecoder:
    """Abstração única para decodificar PCM ou Opus no cliente/experimento."""

    def __init__(
        self,
        *,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        frame_ms: int = DEFAULT_FRAME_MS,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self._frame_bytes = sample_rate * frame_ms // 1000 * 2
        self._opus: OpusDecoder | None = None

    def decode(self, codec: AudioCodec, payload: bytes) -> bytes:
        if codec is AudioCodec.PCM:
            return payload
        if codec is AudioCodec.OPUS:
            if self._opus is None:
                self._opus = OpusDecoder(sample_rate=self.sample_rate, frame_ms=self.frame_ms)
            return self._opus.decode(payload)
        return bytes(self._frame_bytes)
