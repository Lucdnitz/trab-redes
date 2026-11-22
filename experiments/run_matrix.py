"""Runner headless do experimento obrigatório (PCM vs Opus sob perda via tc netem).

Executa no Linux/WSL2 aplicando perdas reais na interface `lo` com `tc netem`,
reutiliza `AudioPacket`, `FrameEncoder`, `FrameDecoder` e `JitterBuffer`,
grava o áudio reconstruído em WAV, transcreve com `faster-whisper` e salva o CSV.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
import wave
from pathlib import Path

import jiwer
import numpy as np

from redes_audio.core.jitter_buffer import JitterBuffer
from redes_audio.server.transcription import LocalTranscriber
from redes_audio.shared.audio import load_pcm_frames
from redes_audio.shared.codec import FrameDecoder, FrameEncoder
from redes_audio.shared.protocol import AudioCodec, AudioPacket, PacketDecodeError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WAV = ROOT / "data" / "reference" / "aula_redes_exp.wav"
DEFAULT_TXT = ROOT / "data" / "reference" / "aula_redes_exp.txt"
RESULTS_DIR = ROOT / "experiments" / "results"
UDP_IP_OVERHEAD_BYTES = 28  # IPv4 (20B) + UDP (8B)


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^\w\sà-úÀ-Ú]", " ", text.lower())
    return " ".join(cleaned.split())


def apply_netem_loss(interface: str, loss_pct: int, *, use_tc: bool) -> None:
    if not use_tc:
        return
    if loss_pct == 0:
        clear_netem(interface, use_tc=True)
        return
    subprocess.run(
        [
            *_privileged_prefix(),
            "tc",
            "qdisc",
            "replace",
            "dev",
            interface,
            "root",
            "netem",
            "loss",
            f"{loss_pct}%",
        ],
        check=True,
    )


def clear_netem(interface: str, *, use_tc: bool) -> None:
    if not use_tc:
        return
    subprocess.run(
        [*_privileged_prefix(), "tc", "qdisc", "del", "dev", interface, "root"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _privileged_prefix() -> list[str]:
    """Usa sudo somente quando o runner não está sendo executado como root."""
    get_euid = getattr(os, "geteuid", None)
    return [] if get_euid is not None and get_euid() == 0 else ["sudo"]


class _HeadlessReceiverProtocol(asyncio.DatagramProtocol):
    def __init__(self, buffer: JitterBuffer) -> None:
        self.buffer = buffer
        self.arrival_times: dict[int, float] = {}

    def datagram_received(self, data: bytes, _addr) -> None:
        recv_t = time.perf_counter()
        try:
            packet = AudioPacket.decode(data)
        except PacketDecodeError:
            return
        self.arrival_times[packet.sequence] = recv_t
        self.buffer.push(packet, wire_bytes=len(data))


async def run_single_trial(
    pcm_frames: list[bytes],
    *,
    codec: AudioCodec,
    sample_rate: int = 16_000,
    frame_ms: int = 20,
    prefill_frames: int = 5,
) -> dict[str, object]:
    """Transmite todos os quadros por UDP real, passa pelo JitterBuffer e reconstrói WAV."""
    buffer = JitterBuffer(
        prefill_frames=prefill_frames,
        max_frames=max(50, prefill_frames * 5),
        idle_rearm_frames=200,
        initial_sequence=0,
    )
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: _HeadlessReceiverProtocol(buffer),
        local_addr=("127.0.0.1", 0),
    )
    udp_port = transport.get_extra_info("sockname")[1]

    encoder = FrameEncoder(codec, sample_rate=sample_rate, frame_ms=frame_ms)
    decoder = FrameDecoder(sample_rate=sample_rate, frame_ms=frame_ms)
    samples_per_frame = sample_rate * frame_ms // 1000
    silence = bytes(samples_per_frame * 2)
    frame_interval = frame_ms / 1000

    send_times: dict[int, float] = {}
    encode_times_ms: list[float] = []
    decode_times_ms: list[float] = []
    wire_bytes_sent = 0
    reconstructed_pcm: list[bytes] = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    start_time = loop.time()

    try:
        for seq, pcm_frame in enumerate(pcm_frames):
            t_enc0 = time.perf_counter()
            payload = encoder.encode(pcm_frame)
            encode_times_ms.append((time.perf_counter() - t_enc0) * 1000.0)

            if payload:
                datagram = AudioPacket(
                    sequence=seq,
                    timestamp_samples=seq * samples_per_frame,
                    codec=codec,
                    payload=payload,
                ).encode()
                send_times[seq] = time.perf_counter()
                sock.sendto(datagram, ("127.0.0.1", udp_port))
                wire_bytes_sent += len(datagram) + UDP_IP_OVERHEAD_BYTES

            # Consome no mesmo ritmo de 20 ms após o prefill para simular reprodução ao vivo.
            popped = buffer.pop_next()
            if popped is not None:
                t_dec0 = time.perf_counter()
                reconstructed_pcm.append(decoder.decode(popped.codec, popped.payload))
                decode_times_ms.append((time.perf_counter() - t_dec0) * 1000.0)
            elif seq >= prefill_frames:
                reconstructed_pcm.append(silence)

            target_time = start_time + (seq + 1) * frame_interval
            remaining = target_time - loop.time()
            if remaining > 0:
                await asyncio.sleep(remaining)

        # Completa exatamente a duração original, inclusive perdas iniciais e finais.
        while len(reconstructed_pcm) < len(pcm_frames):
            popped = buffer.pop_next()
            if popped is None:
                reconstructed_pcm.append(silence)
            else:
                t_dec0 = time.perf_counter()
                reconstructed_pcm.append(decoder.decode(popped.codec, popped.payload))
                decode_times_ms.append((time.perf_counter() - t_dec0) * 1000.0)
    finally:
        sock.close()
        transport.close()

    metrics = buffer.metrics()
    net_latencies_ms = [
        max(0.0, (protocol.arrival_times[seq] - send_times[seq]) * 1000.0)
        for seq in protocol.arrival_times
        if seq in send_times
    ]

    return {
        "pcm_bytes": b"".join(reconstructed_pcm),
        "packets_sent": len(pcm_frames),
        "packets_received": metrics.received,
        "packets_played": metrics.played,
        "packets_lost": max(0, len(pcm_frames) - metrics.received),
        "packets_late": metrics.late,
        "bytes_received_wire": metrics.bytes_received + metrics.received * UDP_IP_OVERHEAD_BYTES,
        "bytes_sent_wire": wire_bytes_sent,
        "avg_encode_ms": float(np.mean(encode_times_ms)) if encode_times_ms else 0.0,
        "avg_decode_ms": float(np.mean(decode_times_ms)) if decode_times_ms else 0.0,
        "avg_network_ms": float(np.mean(net_latencies_ms)) if net_latencies_ms else 0.0,
    }


def write_wav(path: Path, pcm_bytes: bytes, *, sample_rate: int = 16_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa a matriz experimental do Projeto 2.")
    parser.add_argument("--wav", type=Path, default=DEFAULT_WAV, help="WAV de referência")
    parser.add_argument("--txt", type=Path, default=DEFAULT_TXT, help="Texto gabarito")
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "results.csv")
    parser.add_argument("--interface", default="lo", help="Interface Linux para tc netem")
    parser.add_argument("--repetitions", type=int, default=3, help="Repetições por combinação")
    parser.add_argument(
        "--losses",
        default="0,1,5,10,20",
        help="Percentuais de perda separados por vírgula",
    )
    parser.add_argument("--whisper-model", default="base", help="Modelo faster-whisper")
    parser.add_argument(
        "--no-tc",
        action="store_true",
        help="Executa sem chamar tc netem (apenas smoke test local no Windows)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    use_tc = not args.no_tc
    if use_tc and sys.platform.startswith("win"):
        raise SystemExit(
            "tc netem requer Linux/WSL2. Rode este script no WSL2 ou use --no-tc para smoke test."
        )

    losses = [int(x.strip()) for x in args.losses.split(",") if x.strip()]
    pcm_frames = load_pcm_frames(args.wav, sample_rate=16_000, frame_ms=20)
    duration_s = len(pcm_frames) * 0.02

    transcriber = LocalTranscriber(
        model_size=args.whisper_model,
        language="pt",
        compute_type="int8",
    )
    transcriber.ensure_loaded()

    clean_pcm = b"".join(pcm_frames)
    clean_transcript, clean_asr_ms = transcriber.transcribe_pcm(clean_pcm)
    norm_clean = normalize_text(clean_transcript)
    ground_truth = args.txt.read_text(encoding="utf-8").strip() if args.txt.exists() else ""
    norm_gt = normalize_text(ground_truth)

    print(f"Áudio: {args.wav.name} ({duration_s:.2f}s, {len(pcm_frames)} quadros)")
    print(f"Transcrição limpa ({clean_asr_ms:.0f} ms): {clean_transcript}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run",
        "codec",
        "loss_pct",
        "repetition",
        "duration_s",
        "packets_sent",
        "packets_received",
        "packets_lost",
        "packets_late",
        "observed_loss_pct",
        "bytes_received_wire",
        "bandwidth_kbps",
        "jitter_buffer_ms",
        "wer",
        "wer_vs_gt",
        "capture_to_send_ms",
        "network_ms",
        "buffer_ms",
        "asr_window_ms",
        "transcription_ms",
        "decode_ms",
        "text_delivery_ms",
        "display_budget_ms",
        "total_ms",
        "transcript",
    ]

    rows: list[dict[str, object]] = []
    run_id = 0
    jitter_buffer_ms = 100.0
    capture_frame_ms = 20.0
    asr_window_ms = 1_000.0
    display_budget_ms = round(1000.0 / 60.0, 2)

    try:
        for codec in (AudioCodec.PCM, AudioCodec.OPUS):
            for loss_pct in losses:
                apply_netem_loss(args.interface, loss_pct, use_tc=use_tc)
                for rep in range(1, args.repetitions + 1):
                    run_id += 1
                    trial = asyncio.run(
                        run_single_trial(pcm_frames, codec=codec, prefill_frames=5)
                    )
                    wav_out = (
                        args.output.parent
                        / "wav"
                        / f"run_{run_id:02d}_{codec.name}_{loss_pct}.wav"
                    )
                    write_wav(wav_out, trial["pcm_bytes"])

                    hyp_text, asr_ms = transcriber.transcribe_pcm(trial["pcm_bytes"])
                    norm_hyp = normalize_text(hyp_text)
                    wer_clean = jiwer.wer(norm_clean, norm_hyp) if norm_clean else 0.0
                    wer_gt = jiwer.wer(norm_gt, norm_hyp) if norm_gt else 0.0

                    # Escala tempo total de ASR para o orçamento por janela de 4s.
                    window_scale = min(1.0, 4.0 / max(1.0, duration_s))
                    asr_window_compute_ms = round(asr_ms * window_scale, 2)
                    capture_to_send_ms = round(capture_frame_ms + float(trial["avg_encode_ms"]), 2)
                    network_ms = round(float(trial["avg_network_ms"]), 2)
                    decode_ms = round(float(trial["avg_decode_ms"]), 2)
                    # Proxy conservadora: o texto retorna pelo mesmo enlace local medido.
                    text_delivery_ms = network_ms
                    total_ms = round(
                        capture_to_send_ms
                        + network_ms
                        + jitter_buffer_ms
                        + decode_ms
                        + asr_window_ms
                        + asr_window_compute_ms
                        + text_delivery_ms
                        + display_budget_ms,
                        2,
                    )

                    sent = int(trial["packets_sent"])
                    lost = int(trial["packets_lost"])
                    obs_loss = round((lost / sent) * 100.0, 2) if sent else 0.0
                    wire_bytes = int(trial["bytes_received_wire"])
                    bandwidth_kbps = round((wire_bytes * 8) / duration_s / 1000.0, 2)

                    row = {
                        "run": run_id,
                        "codec": codec.name,
                        "loss_pct": loss_pct,
                        "repetition": rep,
                        "duration_s": round(duration_s, 2),
                        "packets_sent": sent,
                        "packets_received": trial["packets_received"],
                        "packets_lost": lost,
                        "packets_late": trial["packets_late"],
                        "observed_loss_pct": obs_loss,
                        "bytes_received_wire": wire_bytes,
                        "bandwidth_kbps": bandwidth_kbps,
                        "jitter_buffer_ms": jitter_buffer_ms,
                        "wer": round(wer_clean, 4),
                        "wer_vs_gt": round(wer_gt, 4),
                        "capture_to_send_ms": capture_to_send_ms,
                        "network_ms": network_ms,
                        "buffer_ms": jitter_buffer_ms,
                        "asr_window_ms": asr_window_ms,
                        "transcription_ms": asr_window_compute_ms,
                        "decode_ms": decode_ms,
                        "text_delivery_ms": text_delivery_ms,
                        "display_budget_ms": display_budget_ms,
                        "total_ms": total_ms,
                        "transcript": hyp_text,
                    }
                    rows.append(row)
                    with args.output.open("w", newline="", encoding="utf-8") as fp:
                        writer = csv.DictWriter(fp, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                    print(
                        f"Run {run_id:02d} | {codec.name:4s} | loss={loss_pct:2d}% "
                        f"(obs={obs_loss:5.2f}%) | bw={bandwidth_kbps:6.1f} kbps "
                        f"| WER={wer_clean:.3f} | total={total_ms:.1f}ms"
                    )
    finally:
        clear_netem(args.interface, use_tc=use_tc)

    with args.output.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "hypothesis": (
            "A perda de pacotes aumenta o WER; Opus reduz banda, mas pode reagir de forma "
            "diferente do PCM sob a mesma perda."
        ),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "interface": args.interface,
        "tc_netem": use_tc,
        "losses_pct": losses,
        "repetitions": args.repetitions,
        "whisper_model": args.whisper_model,
        "reference_audio": str(args.wav),
        "reference_text": str(args.txt),
        "rows": len(rows),
    }
    (args.output.parent / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"CSV salvo em: {args.output}")


if __name__ == "__main__":
    main()
