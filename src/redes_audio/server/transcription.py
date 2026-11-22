"""Transcrição local em CPU com faster-whisper fora do caminho crítico do UDP."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class WordTiming:
    start_s: float
    end_s: float
    word: str


@dataclass(frozen=True, slots=True)
class TranscribedSegment:
    start_s: float
    end_s: float
    text: str
    words: tuple[WordTiming, ...]


@dataclass(frozen=True, slots=True)
class TranscribedChunk:
    sequence: int
    start_ms: int
    end_ms: int
    start_samples: int
    end_samples: int
    text: str
    transcription_ms: float


@dataclass(frozen=True, slots=True)
class StreamingStepResult:
    finalized: list[TranscribedChunk]
    partial_text: str
    partial_start_ms: int


class LocalTranscriber:
    """Encapsula o WhisperModel para transcrição de áudio PCM 16 kHz int16."""

    def __init__(
        self,
        *,
        model_size: str = "base",
        language: str = "pt",
        compute_type: str = "int8",
        cpu_threads: int | None = None,
    ) -> None:
        self.model_size = model_size
        self.language = language
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads or max(1, min(4, (os.cpu_count() or 4) // 2))
        self._model = None

    def ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self.model_size,
            device="cpu",
            compute_type=self.compute_type,
            cpu_threads=self.cpu_threads,
        )

    def transcribe_segments(
        self,
        pcm_bytes: bytes,
        *,
        sample_rate: int = 16_000,
        previous_context: str = "",
        vad_filter: bool = True,
        word_timestamps: bool = True,
    ) -> tuple[list[TranscribedSegment], float]:
        """Transcreve PCM int16 mono e retorna segmentos com tempos por palavra."""
        if len(pcm_bytes) < sample_rate:  # ignora fragmentos menores que 0.5s
            return [], 0.0

        self.ensure_loaded()
        assert self._model is not None

        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if float(np.sqrt(np.mean(audio * audio))) < 0.004:
            return [], 0.0

        t0 = time.perf_counter()
        vad_params = {"min_silence_duration_ms": 300} if vad_filter else None
        segments, _ = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=1,
            vad_filter=vad_filter,
            vad_parameters=vad_params,
            word_timestamps=word_timestamps,
            initial_prompt=previous_context[-160:] if previous_context else None,
            condition_on_previous_text=False,
        )
        items: list[TranscribedSegment] = []
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            words = tuple(
                WordTiming(float(w.start), float(w.end), w.word)
                for w in (seg.words or ())
                if w.word
            )
            items.append(
                TranscribedSegment(
                    start_s=float(seg.start),
                    end_s=float(seg.end),
                    text=text,
                    words=words,
                )
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return items, elapsed_ms

    def transcribe_pcm(
        self,
        pcm_bytes: bytes,
        *,
        sample_rate: int = 16_000,
        previous_context: str = "",
    ) -> tuple[str, float]:
        """Transcreve PCM int16 mono completo e retorna `(texto, tempo_ms)`."""
        items, elapsed_ms = self.transcribe_segments(
            pcm_bytes,
            sample_rate=sample_rate,
            previous_context=previous_context,
            vad_filter=False,
            word_timestamps=False,
        )
        text = " ".join(seg.text for seg in items).strip()
        return text, elapsed_ms


class StreamingTranscriptionBuffer:
    """Buffer deslizante com corte em fronteira exata de palavras/frases."""

    def __init__(
        self,
        transcriber: LocalTranscriber,
        *,
        sample_rate: int = 16_000,
        step_seconds: float = 1.0,
        max_buffer_seconds: float = 4.0,
    ) -> None:
        self.transcriber = transcriber
        self.sample_rate = sample_rate
        self.step_bytes = int(sample_rate * step_seconds) * 2
        self.max_buffer_bytes = int(sample_rate * max_buffer_seconds) * 2
        self._pcm = bytearray()
        self._bytes_since_step = 0
        self._cursor_samples = 0
        self._sequence = 0
        self._last_text = ""

    def reset(self) -> None:
        self._pcm.clear()
        self._bytes_since_step = 0
        self._cursor_samples = 0
        self._sequence = 0
        self._last_text = ""

    def push_pcm(self, pcm_bytes: bytes) -> bool:
        """Acumula PCM e retorna `True` quando houver dados novos suficientes para rodar ASR."""
        self._pcm.extend(pcm_bytes)
        self._bytes_since_step += len(pcm_bytes)
        if self._bytes_since_step < self.step_bytes:
            return False
        self._bytes_since_step = 0
        return True

    async def process_current(self, *, flush: bool = False) -> StreamingStepResult:
        """Lê o estado atual do buffer e finaliza frases ou cláusulas em fronteira de palavra."""
        if not self._pcm:
            return StreamingStepResult(finalized=[], partial_text="", partial_start_ms=0)

        snapshot_cursor = self._cursor_samples
        pcm_bytes = bytes(self._pcm)

        segments, elapsed_ms = await asyncio.to_thread(
            self.transcriber.transcribe_segments,
            pcm_bytes,
            sample_rate=self.sample_rate,
            previous_context=self._last_text,
            vad_filter=True,
            word_timestamps=True,
        )
        if not segments:
            if flush:
                self._pcm.clear()
                self._cursor_samples = snapshot_cursor + len(pcm_bytes) // 2
            return StreamingStepResult(finalized=[], partial_text="", partial_start_ms=0)

        buffer_duration_s = len(pcm_bytes) / (2 * self.sample_rate)
        finalized: list[TranscribedChunk] = []
        consumed_local_samples = 0
        partial_text = ""
        partial_start_ms = 0

        if flush:
            for seg in segments:
                finalized.append(
                    self._make_chunk(snapshot_cursor, seg.start_s, seg.end_s, seg.text, elapsed_ms)
                )
            self._pcm.clear()
            self._cursor_samples = snapshot_cursor + len(pcm_bytes) // 2
            return StreamingStepResult(finalized=finalized, partial_text="", partial_start_ms=0)

        # 1. Se houver >= 2 segmentos ou pausa clara no final, finaliza os concluídos.
        if len(segments) >= 2:
            for seg in segments[:-1]:
                finalized.append(
                    self._make_chunk(snapshot_cursor, seg.start_s, seg.end_s, seg.text, elapsed_ms)
                )
                consumed_local_samples = max(
                    consumed_local_samples,
                    int(seg.end_s * self.sample_rate),
                )
            last_seg = segments[-1]
            if buffer_duration_s - last_seg.end_s >= 0.8:
                finalized.append(
                    self._make_chunk(
                        snapshot_cursor,
                        last_seg.start_s,
                        last_seg.end_s,
                        last_seg.text,
                        elapsed_ms,
                    )
                )
                consumed_local_samples = max(
                    consumed_local_samples,
                    int(last_seg.end_s * self.sample_rate),
                )
            else:
                partial_text = last_seg.text
                partial_start_ms = (
                    (snapshot_cursor + int(last_seg.start_s * self.sample_rate))
                    * 1000
                    // self.sample_rate
                )
        else:
            only = segments[0]
            split_idx = self._find_word_split_index(only, buffer_duration_s)
            if split_idx is not None:
                committed_words = only.words[: split_idx + 1]
                remaining_words = only.words[split_idx + 1 :]
                chunk_text = "".join(w.word for w in committed_words).strip()
                end_s = committed_words[-1].end_s
                if remaining_words:
                    next_start_s = remaining_words[0].start_s
                    cut_s = (end_s + next_start_s) / 2 if next_start_s >= end_s else max(
                        0.0, next_start_s - 0.02
                    )
                else:
                    cut_s = end_s
                if chunk_text:
                    finalized.append(
                        self._make_chunk(
                            snapshot_cursor, only.start_s, end_s, chunk_text, elapsed_ms
                        )
                    )
                    consumed_local_samples = int(cut_s * self.sample_rate)
                if remaining_words:
                    partial_text = "".join(w.word for w in remaining_words).strip()
                    partial_start_ms = (
                        (snapshot_cursor + int(remaining_words[0].start_s * self.sample_rate))
                        * 1000
                        // self.sample_rate
                    )
            else:
                partial_text = only.text
                partial_start_ms = (
                    (snapshot_cursor + int(only.start_s * self.sample_rate))
                    * 1000
                    // self.sample_rate
                )

        if consumed_local_samples > 0:
            cut_bytes = min(len(self._pcm), consumed_local_samples * 2)
            del self._pcm[:cut_bytes]
            self._cursor_samples += cut_bytes // 2

        return StreamingStepResult(
            finalized=finalized,
            partial_text=partial_text,
            partial_start_ms=partial_start_ms,
        )

    def _find_word_split_index(
        self,
        segment: TranscribedSegment,
        buffer_duration_s: float,
    ) -> int | None:
        words = segment.words
        if len(words) < 3:
            return None

        # Se há pausa clara (>= 0.6s) após a última palavra, fecha o segmento inteiro.
        if buffer_duration_s - words[-1].end_s >= 0.6:
            return len(words) - 1

        # Se há vírgula/ponto ou pausa (>= 0.08s) após 1.8s de fala, fecha nessa fronteira.
        safe_end_limit = buffer_duration_s - 0.50
        for idx, word in enumerate(words[:-1]):
            if word.end_s >= 1.8 and word.end_s <= safe_end_limit:
                stripped = word.word.strip()
                gap = words[idx + 1].start_s - word.end_s
                if stripped.endswith((".", "!", "?", ",")) or gap >= 0.08:
                    return idx

        # Se o buffer passou do limite (4.0s), escolhe a maior folga entre palavras.
        if buffer_duration_s >= (self.max_buffer_bytes / (2 * self.sample_rate)):
            candidates = [
                (words[i + 1].start_s - words[i].end_s, i)
                for i in range(1, len(words) - 1)
                if words[i].end_s <= safe_end_limit
            ]
            if candidates:
                return max(candidates)[1]
            return len(words) - 2

        return None

    def _make_chunk(
        self,
        snapshot_cursor: int,
        start_s: float,
        end_s: float,
        text: str,
        elapsed_ms: float,
    ) -> TranscribedChunk:
        start_samples = snapshot_cursor + int(start_s * self.sample_rate)
        end_samples = snapshot_cursor + int(end_s * self.sample_rate)
        chunk = TranscribedChunk(
            sequence=self._sequence,
            start_ms=start_samples * 1000 // self.sample_rate,
            end_ms=end_samples * 1000 // self.sample_rate,
            start_samples=start_samples,
            end_samples=end_samples,
            text=text,
            transcription_ms=round(elapsed_ms, 2),
        )
        self._sequence += 1
        self._last_text = text
        return chunk
