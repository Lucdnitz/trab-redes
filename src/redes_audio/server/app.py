"""Aplicação FastAPI do servidor."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from redes_audio import __version__
from redes_audio.server.broadcaster import AudioBroadcaster
from redes_audio.server.config import settings
from redes_audio.server.registry import ClientEndpoint, ClientRegistry
from redes_audio.server.summary import RollingSummary, SummaryEngine
from redes_audio.server.transcription import LocalTranscriber
from redes_audio.shared.protocol import AudioCodec
from redes_audio.shared.signing import TranscriptSigner

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WAV_PATH = PROJECT_ROOT / "data" / "reference" / "aula_redes.wav"


class HealthResponse(BaseModel):
    status: str
    version: str
    clients: int


class StreamStartRequest(BaseModel):
    codec: str = "pcm"
    wav_path: str | None = None
    loop: bool = False
    enable_transcription: bool = True


registry = ClientRegistry()
rolling_summary = RollingSummary(minimum_pending_characters=settings.summary_min_chars)
summary_engine = SummaryEngine(
    rolling_summary,
    backend=settings.summary_backend,
    ollama_url=settings.ollama_url,
    ollama_model=settings.ollama_model,
)
signer = TranscriptSigner.generate()
transcriber = LocalTranscriber(
    model_size=settings.whisper_model,
    language=settings.whisper_language,
)
broadcaster = AudioBroadcaster(
    registry,
    sample_rate=settings.sample_rate,
    frame_ms=settings.frame_duration_ms,
    signer=signer,
    transcriber=transcriber,
    summary_engine=summary_engine,
    transcription_window_seconds=settings.transcription_window_seconds,
)


def summary_payload() -> dict[str, object]:
    """Serializa o último resumo confirmado para HTTP e WebSocket."""
    return asdict(rolling_summary.snapshot())


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await broadcaster.stop_active_stream()


app = FastAPI(
    title="Redes Audio Live",
    version=__version__,
    description="Servidor UDP e WebSocket do Projeto 2 de Redes",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, clients=await registry.count())


@app.get("/api/v1/session")
async def session_status() -> dict[str, object]:
    clients = await registry.snapshot()
    return {
        "session_id": broadcaster.session_id,
        "streaming": broadcaster.is_streaming(),
        "clients": [
            {"client_id": item.client_id, "host": item.host, "udp_port": item.udp_port}
            for item in clients
        ],
        "sample_rate": settings.sample_rate,
        "frame_duration_ms": settings.frame_duration_ms,
        "public_key": signer.public_key_b64(),
        "summary": summary_payload(),
    }


@app.post("/api/v1/demo/start", status_code=status.HTTP_202_ACCEPTED)
async def start_demo() -> dict[str, object]:
    client_count = await registry.count()
    if client_count:
        await broadcaster.start_demo_background()
    return {"accepted": bool(client_count), "clients": client_count}


@app.post("/api/v1/stream/start", status_code=status.HTTP_202_ACCEPTED)
async def start_stream(request: StreamStartRequest | None = None) -> dict[str, object]:
    req = request or StreamStartRequest()
    codec_name = req.codec.strip().upper()
    try:
        codec = AudioCodec[codec_name]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Codec inválido: {req.codec}") from exc

    wav_path = Path(req.wav_path) if req.wav_path else DEFAULT_WAV_PATH
    if not wav_path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo WAV não encontrado: {wav_path}")

    client_count = await registry.count()
    if client_count:
        await broadcaster.start_wav_background(
            wav_path,
            codec=codec,
            loop_stream=req.loop,
            enable_transcription=req.enable_transcription,
        )
    return {
        "accepted": bool(client_count),
        "clients": client_count,
        "codec": codec.name,
        "wav_path": str(wav_path),
    }


@app.post("/api/v1/stream/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_and_stream(
    request: Request,
    filename: str = "custom.wav",
    codec: str = "opus",
    loop: bool = False,
) -> dict[str, object]:
    """Recebe qualquer arquivo de áudio enviado pelo cliente e inicia a transmissão."""
    codec_name = codec.strip().upper()
    try:
        selected_codec = AudioCodec[codec_name]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Codec inválido: {codec}") from exc

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Arquivo de áudio vazio")

    safe_name = Path(filename).name or "custom.wav"
    upload_dir = PROJECT_ROOT / "data" / "generated"
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / f"upload_{safe_name}"
    saved_path.write_bytes(body)

    client_count = await registry.count()
    if client_count:
        await broadcaster.start_wav_background(
            saved_path,
            codec=selected_codec,
            loop_stream=loop,
            enable_transcription=True,
        )
    return {
        "accepted": bool(client_count),
        "clients": client_count,
        "codec": selected_codec.name,
        "filename": safe_name,
    }


@app.post("/api/v1/stream/stop", status_code=status.HTTP_200_OK)
async def stop_stream() -> dict[str, object]:
    await broadcaster.stop_active_stream()
    return {"stopped": True}


@app.post("/api/v1/demo/tamper", status_code=status.HTTP_202_ACCEPTED)
async def trigger_tampered_transcript() -> dict[str, object]:
    """Envia uma legenda adulterada de propósito para demonstrar a detecção Ed25519."""
    base = broadcaster.last_transcript
    if base is not None:
        tampered = dict(base)
        tampered["text"] = f"{base['text']} [TRECHO ADULTERADO NO CAMINHO]"
    else:
        fake_seq = 999
        valid_sig = signer.sign(
            session_id=broadcaster.session_id,
            sequence=fake_seq,
            start_ms=0,
            end_ms=2_000,
            text="Texto original assinado pelo servidor.",
        )
        tampered = {
            "type": "transcript",
            "session_id": broadcaster.session_id,
            "sequence": fake_seq,
            "start_ms": 0,
            "end_ms": 2_000,
            "start_samples": 0,
            "end_samples": settings.sample_rate * 2,
            "text": "Texto adulterado por atacante na rede!",
            "transcription_ms": 0.0,
            "signature": valid_sig,
        }

    await registry.broadcast_json(tampered)
    return {"sent": True, "clients": await registry.count()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    client_id = str(uuid.uuid4())

    try:
        first_message = json.loads(await websocket.receive_text())
        if first_message.get("type") != "register":
            await websocket.close(code=1008, reason="first message must register the client")
            return

        udp_port = int(first_message["udp_port"])
        if not 1 <= udp_port <= 65_535:
            await websocket.close(code=1008, reason="invalid UDP port")
            return

        host = websocket.client.host if websocket.client else "127.0.0.1"
        await registry.register(
            ClientEndpoint(client_id=client_id, host=host, udp_port=udp_port),
            websocket=websocket,
        )
        await websocket.send_json(
            {
                "type": "registered",
                "client_id": client_id,
                "session_id": broadcaster.session_id,
                "sample_rate": settings.sample_rate,
                "frame_duration_ms": settings.frame_duration_ms,
                "public_key": signer.public_key_b64(),
                "summary": summary_payload(),
            }
        )

        while True:
            message = json.loads(await websocket.receive_text())
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass
    finally:
        await registry.unregister(client_id)
