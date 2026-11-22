"""Leitura e normalização de mídia para PCM mono, 16 bits e quadros fixos."""

from __future__ import annotations

import wave
from pathlib import Path


def load_pcm_frames(
    audio_path: Path,
    *,
    sample_rate: int = 16_000,
    frame_ms: int = 20,
) -> list[bytes]:
    """Lê WAV ou mídia suportada pelo PyAV e devolve quadros PCM uniformes."""
    frame_bytes = sample_rate * frame_ms // 1000 * 2

    if audio_path.suffix.lower() == ".wav":
        with wave.open(str(audio_path), "rb") as wav_file:
            is_native_format = (
                wav_file.getnchannels() == 1
                and wav_file.getsampwidth() == 2
                and wav_file.getframerate() == sample_rate
            )
            raw_pcm = (
                wav_file.readframes(wav_file.getnframes())
                if is_native_format
                else _resample_audio_file(audio_path, sample_rate)
            )
    else:
        raw_pcm = _resample_audio_file(audio_path, sample_rate)

    if not raw_pcm:
        return []

    remainder = len(raw_pcm) % frame_bytes
    if remainder:
        raw_pcm += bytes(frame_bytes - remainder)
    return [raw_pcm[index : index + frame_bytes] for index in range(0, len(raw_pcm), frame_bytes)]


def _resample_audio_file(path: Path, sample_rate: int) -> bytes:
    import av
    import numpy as np

    resampler = av.AudioResampler(format="s16", layout="mono", rate=sample_rate)
    chunks: list[bytes] = []
    with av.open(str(path)) as container:
        for frame in container.decode(audio=0):
            for output_frame in resampler.resample(frame):
                chunks.append(output_frame.to_ndarray().astype(np.int16, copy=False).tobytes())
        for output_frame in resampler.resample(None):
            chunks.append(output_frame.to_ndarray().astype(np.int16, copy=False).tobytes())
    return b"".join(chunks)
