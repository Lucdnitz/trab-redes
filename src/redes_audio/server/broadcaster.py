"""Transmissor UDP de áudio PCM/Opus com transcrição e resumo assíncronos."""

from __future__ import annotations

import asyncio
import math
import socket
import uuid
from array import array
from pathlib import Path

from redes_audio.server.registry import ClientRegistry
from redes_audio.server.summary import SummaryEngine, TranscriptSegment
from redes_audio.server.transcription import LocalTranscriber, StreamingTranscriptionBuffer
from redes_audio.shared.audio import load_pcm_frames
from redes_audio.shared.codec import FrameEncoder
from redes_audio.shared.protocol import AudioCodec, AudioPacket
from redes_audio.shared.signing import TranscriptSigner


class AudioBroadcaster:
    """Coordena a transmissão UDP em tempo real e o pipeline assíncrono de IA."""

    def __init__(
        self,
        registry: ClientRegistry,
        *,
        sample_rate: int,
        frame_ms: int,
        signer: TranscriptSigner | None = None,
        transcriber: LocalTranscriber | None = None,
        summary_engine: SummaryEngine | None = None,
        transcription_window_seconds: float = 2.0,
    ) -> None:
        self.registry = registry
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.samples_per_frame = sample_rate * frame_ms // 1000
        self.signer = signer or TranscriptSigner.generate()
        self.transcriber = transcriber
        self.summary_engine = summary_engine
        self.transcription_window_seconds = transcription_window_seconds
        self.session_id = str(uuid.uuid4())
        self.last_transcript: dict[str, object] | None = None
        self._active_task: asyncio.Task[int] | None = None
        self._stop_requested = False
        self._control_lock = asyncio.Lock()

    def is_streaming(self) -> bool:
        return self._active_task is not None and not self._active_task.done()

    async def stop_active_stream(self) -> None:
        async with self._control_lock:
            await self._stop_active_locked()

    async def _stop_active_locked(self) -> None:
        self._stop_requested = True
        task = self._active_task
        self._active_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._stop_requested = False

    async def start_wav_background(
        self,
        wav_path: Path,
        *,
        codec: AudioCodec = AudioCodec.PCM,
        loop_stream: bool = False,
        enable_transcription: bool = True,
    ) -> asyncio.Task[int]:
        async with self._control_lock:
            await self._stop_active_locked()
            self._stop_requested = False
            self._active_task = asyncio.create_task(
                self.stream_wav(
                    wav_path,
                    codec=codec,
                    loop_stream=loop_stream,
                    enable_transcription=enable_transcription,
                )
            )
            return self._active_task

    async def start_demo_background(
        self,
        *,
        duration_seconds: float = 3.0,
        frequency: int = 440,
    ) -> asyncio.Task[int]:
        """Inicia o tom pelo mesmo controlador que impede transmissões concorrentes."""
        async with self._control_lock:
            await self._stop_active_locked()
            self._stop_requested = False
            self._active_task = asyncio.create_task(
                self.stream_demo_tone(
                    duration_seconds=duration_seconds,
                    frequency=frequency,
                )
            )
            return self._active_task

    async def stream_demo_tone(self, *, duration_seconds: float = 3.0, frequency: int = 440) -> int:
        """Envia um tom PCM em tempo real para todos os clientes registrados."""
        total_frames = int(duration_seconds * 1000 / self.frame_ms)
        step = 2 * math.pi * frequency / self.sample_rate
        frames = [
            array(
                "h",
                (
                    int(8_000 * math.sin(step * (idx * self.samples_per_frame + i)))
                    for i in range(self.samples_per_frame)
                ),
            ).tobytes()
            for idx in range(total_frames)
        ]
        return await self.stream_pcm_frames(
            frames,
            codec=AudioCodec.PCM,
            enable_transcription=False,
        )

    async def stream_wav(
        self,
        wav_path: Path,
        *,
        codec: AudioCodec = AudioCodec.PCM,
        loop_stream: bool = False,
        enable_transcription: bool = True,
    ) -> int:
        """Lê um arquivo de áudio e transmite quadro a quadro via UDP."""
        frames = await asyncio.to_thread(
            load_pcm_frames,
            wav_path,
            sample_rate=self.sample_rate,
            frame_ms=self.frame_ms,
        )
        if not frames:
            return 0

        total_sent = 0
        while not self._stop_requested:
            sent = await self.stream_pcm_frames(
                frames,
                codec=codec,
                enable_transcription=enable_transcription,
            )
            total_sent += sent
            if not loop_stream or self._stop_requested:
                break
        return total_sent

    async def stream_pcm_frames(
        self,
        pcm_frames: list[bytes],
        *,
        codec: AudioCodec = AudioCodec.PCM,
        enable_transcription: bool = True,
    ) -> int:
        """Transmite quadros PCM (codificando para `codec`) no ritmo de 20 ms."""
        self.session_id = str(uuid.uuid4())
        self.last_transcript = None
        if self.summary_engine is not None:
            self.summary_engine.rolling.reset()

        await self.registry.broadcast_json(
            {
                "type": "stream_started",
                "session_id": self.session_id,
                "codec": codec.name,
                "sample_rate": self.sample_rate,
                "frame_duration_ms": self.frame_ms,
                "public_key": self.signer.public_key_b64(),
            }
        )

        encoder = FrameEncoder(codec, sample_rate=self.sample_rate, frame_ms=self.frame_ms)
        asr_event: asyncio.Event | None = None
        summary_event: asyncio.Event | None = None
        asr_done = False
        summary_done = False
        asr_task: asyncio.Task[None] | None = None
        summary_task: asyncio.Task[None] | None = None
        asr_buffer: StreamingTranscriptionBuffer | None = None

        if enable_transcription and self.transcriber is not None:
            asr_event = asyncio.Event()
            if self.summary_engine is not None:
                summary_event = asyncio.Event()
                summary_task = asyncio.create_task(
                    self._run_summary_worker(summary_event, lambda: summary_done)
                )
            asr_buffer = StreamingTranscriptionBuffer(
                self.transcriber,
                sample_rate=self.sample_rate,
                step_seconds=min(1.0, self.transcription_window_seconds),
            )
            asr_task = asyncio.create_task(
                self._run_transcription_worker(
                    self.session_id,
                    asr_buffer,
                    asr_event,
                    lambda: asr_done,
                    summary_event,
                )
            )

        sequence = 0
        timestamp = 0
        frame_interval = self.frame_ms / 1000
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        loop = asyncio.get_running_loop()
        start_time = loop.time()

        try:
            for frame_index, pcm_frame in enumerate(pcm_frames):
                if self._stop_requested:
                    break

                payload = encoder.encode(pcm_frame)
                if payload:
                    packet = AudioPacket(
                        sequence=sequence,
                        timestamp_samples=timestamp,
                        codec=codec,
                        payload=payload,
                    ).encode()

                    clients = await self.registry.snapshot()
                    for client in clients:
                        try:
                            sock.sendto(packet, (client.host, client.udp_port))
                        except OSError:
                            # Um endpoint inválido não pode interromper os demais ouvintes.
                            continue

                if asr_buffer is not None and asr_event is not None:
                    if asr_buffer.push_pcm(pcm_frame):
                        asr_event.set()

                sequence += 1
                timestamp += self.samples_per_frame
                target_time = start_time + (frame_index + 1) * frame_interval
                remaining = target_time - loop.time()
                if remaining > 0:
                    await asyncio.sleep(remaining)
        finally:
            sock.close()
            asr_done = True
            if asr_event is not None:
                asr_event.set()
            if asr_task is not None:
                try:
                    await asr_task
                except asyncio.CancelledError:
                    pass
            summary_done = True
            if summary_event is not None:
                summary_event.set()
            if summary_task is not None:
                try:
                    await summary_task
                except asyncio.CancelledError:
                    pass
            await self.registry.broadcast_json(
                {"type": "stream_ended", "session_id": self.session_id}
            )
        return sequence

    async def _run_transcription_worker(
        self,
        session_id: str,
        asr_buffer: StreamingTranscriptionBuffer,
        wake_event: asyncio.Event,
        is_done,
        summary_event: asyncio.Event | None,
    ) -> None:
        while True:
            await wake_event.wait()
            wake_event.clear()
            done_now = bool(is_done())
            if self._stop_requested:
                break

            result = await asr_buffer.process_current(flush=done_now)
            await self._emit_transcription_result(session_id, result, summary_event)
            if done_now:
                break

    async def _run_summary_worker(
        self,
        wake_event: asyncio.Event,
        is_done,
    ) -> None:
        """Atualiza o resumo em tarefa independente para nunca atrasar as legendas."""
        assert self.summary_engine is not None
        while True:
            await wake_event.wait()
            wake_event.clear()
            done_now = bool(is_done())
            if self._stop_requested:
                break

            updated = await self.summary_engine.maybe_update(force=done_now)
            if updated is not None:
                snapshot, backend = updated
                await self.registry.broadcast_json(
                    {
                        "type": "summary",
                        "text": snapshot.text,
                        "through_sequence": snapshot.through_sequence,
                        "through_ms": snapshot.through_ms,
                        "backend": backend,
                    }
                )
            if done_now:
                break
            if self.summary_engine.rolling.ready():
                wake_event.set()

    async def _emit_transcription_result(
        self,
        session_id: str,
        result,
        summary_event: asyncio.Event | None,
    ) -> None:
        for chunk in result.finalized:
            signature = self.signer.sign(
                session_id=session_id,
                sequence=chunk.sequence,
                start_ms=chunk.start_ms,
                end_ms=chunk.end_ms,
                text=chunk.text,
            )
            event: dict[str, object] = {
                "type": "transcript",
                "session_id": session_id,
                "sequence": chunk.sequence,
                "start_ms": chunk.start_ms,
                "end_ms": chunk.end_ms,
                "start_samples": chunk.start_samples,
                "end_samples": chunk.end_samples,
                "text": chunk.text,
                "transcription_ms": chunk.transcription_ms,
                "signature": signature,
            }
            self.last_transcript = event
            await self.registry.broadcast_json(event)

            if self.summary_engine is not None:
                self.summary_engine.rolling.add(
                    TranscriptSegment(
                        sequence=chunk.sequence,
                        start_ms=chunk.start_ms,
                        end_ms=chunk.end_ms,
                        text=chunk.text,
                    )
                )
                if summary_event is not None and self.summary_engine.rolling.ready():
                    summary_event.set()

        if result.partial_text:
            await self.registry.broadcast_json(
                {
                    "type": "transcript_partial",
                    "session_id": session_id,
                    "start_ms": result.partial_start_ms,
                    "text": result.partial_text,
                }
            )
